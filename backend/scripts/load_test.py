from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarking.io import environment_metadata, load_fixtures, write_result_bundle
from benchmarking.statistics import summarize_samples


def classify_error(exc: BaseException) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.TransportError):
        return "transport"
    return "error"


async def validate_server(client: httpx.AsyncClient, base_url: str, gemini_mode: str) -> dict:
    response = await client.get(f"{base_url.rstrip('/')}/api/v1/health")
    response.raise_for_status()
    health = response.json()
    if health.get("gemini_mode") != gemini_mode:
        raise RuntimeError(
            f"Server Gemini mode is {health.get('gemini_mode')!r}, expected {gemini_mode!r}. "
            "Restart the backend with the documented benchmark environment."
        )
    if gemini_mode != "live" and not health.get("benchmark_mode"):
        raise RuntimeError("Non-live Gemini modes require VERITI_BENCHMARK_MODE=true.")
    return health


async def run_load(
    *,
    base_url: str,
    endpoint: str,
    fixtures: list[dict],
    concurrency: int,
    total_requests: int | None,
    warmup: int,
    timeout: float,
    seed: int,
    duration: float | None = None,
    rate_limit: float | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[list[dict], dict]:
    rng = random.Random(seed)
    ordered = fixtures.copy()
    rng.shuffle(ordered)
    semaphore = asyncio.Semaphore(concurrency)
    active = 0
    peak_active = 0
    active_lock = asyncio.Lock()
    launch_started = time.perf_counter()

    async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
        async def submit(index: int, measured: bool) -> dict | None:
            nonlocal active, peak_active
            if rate_limit:
                scheduled_at = launch_started + (index / rate_limit)
                await asyncio.sleep(max(0.0, scheduled_at - time.perf_counter()))
            fixture = ordered[index % len(ordered)]
            async with semaphore:
                async with active_lock:
                    active += 1
                    peak_active = max(peak_active, active)
                started = time.perf_counter()
                started_at_utc = datetime.now(timezone.utc).isoformat()
                status_code = None
                outcome = "success"
                try:
                    with fixture["path"].open("rb") as stream:
                        response = await client.post(
                            f"{base_url.rstrip('/')}{endpoint}",
                            data={
                                "text_note": f"Synthetic benchmark report {uuid.uuid4()}",
                                "latitude": "25.2048",
                                "longitude": "55.2708",
                                "device_trust_score": "0.85",
                                "integrity_token": "benchmark-local-v1",
                            },
                            files={"file": (fixture["filename"], stream, _mime(fixture["format"]))},
                        )
                    status_code = response.status_code
                    if status_code < 200 or status_code >= 300:
                        outcome = f"http_{status_code // 100}xx"
                except Exception as exc:
                    outcome = classify_error(exc)
                finally:
                    duration_ms = (time.perf_counter() - started) * 1000
                    ended_at_utc = datetime.now(timezone.utc).isoformat()
                    async with active_lock:
                        active -= 1
                if not measured:
                    return None
                return {
                    "request_id": str(uuid.uuid4()),
                    "fixture_id": fixture["fixture_id"],
                    "format": fixture["format"],
                    "size_category": fixture["size_category"],
                    "input_bytes": fixture["file_size"],
                    "started_at_utc": started_at_utc,
                    "ended_at_utc": ended_at_utc,
                    "duration_ms": round(duration_ms, 3),
                    "status_code": status_code,
                    "outcome": outcome,
                }

        if warmup:
            await asyncio.gather(*(submit(i, False) for i in range(warmup)))
            launch_started = time.perf_counter()
        if duration is not None:
            deadline = launch_started + duration
            rows = []
            next_index = 0
            index_lock = asyncio.Lock()

            async def worker() -> None:
                nonlocal next_index
                while time.perf_counter() < deadline:
                    async with index_lock:
                        index = next_index
                        next_index += 1
                    if rate_limit and launch_started + (index / rate_limit) >= deadline:
                        return
                    row = await submit(index, True)
                    if row is not None:
                        rows.append(row)

            await asyncio.gather(*(worker() for _ in range(concurrency)))
        else:
            rows = await asyncio.gather(
                *(submit(i, True) for i in range(total_requests or 0))
            )

    samples = [row for row in rows if row is not None]
    elapsed = time.perf_counter() - launch_started
    summary = summarize_samples(
        [{**row, "success": row["outcome"] == "success"} for row in samples]
    )
    summary.update(
        total_requests_attempted=len(samples),
        completed_requests=len(samples),
        status_code_counts=dict(Counter(str(row["status_code"]) for row in samples)),
        error_counts=dict(Counter(row["outcome"] for row in samples if row["outcome"] != "success")),
        requests_per_second=round(len(samples) / elapsed, 3) if elapsed else 0.0,
        timeout_rate=(
            sum(row["outcome"] == "timeout" for row in samples) / len(samples)
            if samples else 0.0
        ),
        peak_client_concurrency=peak_active,
        test_duration_seconds=round(elapsed, 3),
    )
    return samples, summary


def _mime(format_name: str) -> str:
    return "image/png" if format_name == "PNG" else "image/jpeg"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a repeatable Veriti submission load test.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--endpoint", default="/api/v1/submissions/upload")
    parser.add_argument("--concurrency", type=int, default=10)
    count = parser.add_mutually_exclusive_group()
    count.add_argument("--total-requests", type=int, default=100)
    count.add_argument("--duration", type=float)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--fixtures", type=Path, default=Path("benchmark_fixtures/privacy"))
    parser.add_argument("--output", type=Path, default=Path("benchmark_results/load-test.json"))
    parser.add_argument("--seed", type=int, default=20260418)
    parser.add_argument("--gemini-mode", choices=("stubbed", "disabled", "live"), default="stubbed")
    parser.add_argument("--rate-limit", type=float)
    parser.add_argument("--notes", default="")
    return parser


async def async_main(args: argparse.Namespace) -> int:
    fixtures, manifest = load_fixtures(args.fixtures)
    async with httpx.AsyncClient(timeout=args.timeout) as client:
        await validate_server(client, args.base_url, args.gemini_mode)
    rows, summary = await run_load(
        base_url=args.base_url,
        endpoint=args.endpoint,
        fixtures=fixtures,
        concurrency=args.concurrency,
        total_requests=args.total_requests if args.duration is None else None,
        duration=args.duration,
        warmup=args.warmup,
        timeout=args.timeout,
        seed=args.seed,
        rate_limit=args.rate_limit,
    )
    async with httpx.AsyncClient(timeout=args.timeout) as client:
        metrics_response = await client.get(
            f"{args.base_url.rstrip('/')}/api/v1/health/performance"
        )
        metrics_response.raise_for_status()
        summary["server_metrics"] = metrics_response.json()
    summary.update(
        gemini_mode=args.gemini_mode,
        concurrency=args.concurrency,
        warmup_requests=args.warmup,
        fixture_manifest_version=manifest["manifest_version"],
    )
    environment = environment_metadata(args.notes, " ".join(sys.argv))
    write_result_bundle(args.output, rows, summary, environment, manifest)
    print(json.dumps(summary, indent=2))
    print(f"Machine-readable results: {args.output}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.concurrency < 1 or args.warmup < 0:
        raise SystemExit("Concurrency must be positive and warm-up cannot be negative.")
    if args.gemini_mode == "live" and args.concurrency > 2:
        raise SystemExit("Live Gemini benchmarks are capped at concurrency 2; use stubbed mode for load.")
    try:
        return asyncio.run(async_main(args))
    except Exception as exc:
        print(f"Benchmark failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
