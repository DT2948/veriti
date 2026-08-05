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
try:
    from .load_test import _mime, classify_error, validate_server
except ImportError:
    from load_test import _mime, classify_error, validate_server


async def run_e2e(
    *,
    client: httpx.AsyncClient,
    base_url: str,
    endpoint: str,
    fixtures: list[dict],
    submissions: int,
    concurrency: int,
    poll_interval: float,
    timeout: float,
    seed: int,
) -> tuple[list[dict], dict]:
    rng = random.Random(seed)
    ordered = fixtures.copy()
    rng.shuffle(ordered)
    semaphore = asyncio.Semaphore(concurrency)

    async def one(index: int) -> dict:
        fixture = ordered[index % len(ordered)]
        started = time.perf_counter()
        row = {
            "sample_id": str(uuid.uuid4()),
            "fixture_id": fixture["fixture_id"],
            "format": fixture["format"],
            "size_category": fixture["size_category"],
            "outcome": "error",
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "ended_at_utc": None,
            "fallback_used": False,
            "end_to_end_duration_ms": None,
            "verification_duration_ms": None,
        }
        async with semaphore:
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
                if response.status_code < 200 or response.status_code >= 300:
                    row["outcome"] = f"http_{response.status_code // 100}xx"
                    row["end_to_end_duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
                    row["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
                    return row
                correlation_id = response.json().get("correlation_id") or response.json()["id"]
                deadline = time.perf_counter() + timeout
                while time.perf_counter() < deadline:
                    status_response = await client.get(
                        f"{base_url.rstrip('/')}/api/v1/submissions/{correlation_id}/status"
                    )
                    if status_response.status_code != 200:
                        row["outcome"] = f"http_{status_response.status_code // 100}xx"
                        row["end_to_end_duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
                        row["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
                        return row
                    payload = status_response.json()
                    state = payload["verification_status"]
                    if state in {"verified", "rejected"}:
                        row["outcome"] = "success" if state == "verified" else "rejected"
                        row["fallback_used"] = bool(payload.get("fallback_used"))
                        row["verification_duration_ms"] = payload.get("verification_duration_ms")
                        row["end_to_end_duration_ms"] = round(
                            (time.perf_counter() - started) * 1000, 3
                        )
                        row["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
                        return row
                    await asyncio.sleep(poll_interval)
                row["outcome"] = "timeout"
                row["end_to_end_duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
                row["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
                return row
            except Exception as exc:
                row["outcome"] = classify_error(exc)
                row["end_to_end_duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
                row["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
                return row

    rows = await asyncio.gather(*(one(index) for index in range(submissions)))
    completed = [row for row in rows if row["end_to_end_duration_ms"] is not None]
    successful = [row for row in rows if row["outcome"] == "success"]
    summary = summarize_samples(
        [
            {
                "duration_ms": row["end_to_end_duration_ms"],
                "success": row["outcome"] == "success",
            }
            for row in completed
        ]
    )
    verification = summarize_samples(
        [
            {"duration_ms": row["verification_duration_ms"], "success": True}
            for row in successful
            if row["verification_duration_ms"] is not None
        ]
    )
    summary.update(
        submission_count=submissions,
        successful_completions=len(successful),
        rejections=sum(row["outcome"] == "rejected" for row in rows),
        timeouts=sum(row["outcome"] == "timeout" for row in rows),
        fallback_count=sum(bool(row["fallback_used"]) for row in rows),
        outcome_counts=dict(Counter(row["outcome"] for row in rows)),
        median_verification_ms=verification["median_ms"],
        p95_verification_ms=verification["p95_ms"],
    )
    return rows, summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark Veriti submission-to-verification latency.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--endpoint", default="/api/v1/submissions/upload")
    parser.add_argument("--submissions", type=int)
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--poll-interval", type=float, default=0.25)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--fixtures", type=Path, default=Path("benchmark_fixtures/privacy"))
    parser.add_argument("--output", type=Path, default=Path("benchmark_results/e2e.json"))
    parser.add_argument("--seed", type=int, default=20260418)
    parser.add_argument("--gemini-mode", choices=("stubbed", "live"), default="stubbed")
    parser.add_argument("--notes", default="")
    return parser


async def async_main(args: argparse.Namespace) -> int:
    fixtures, manifest = load_fixtures(args.fixtures)
    submissions = args.submissions if args.submissions is not None else (10 if args.gemini_mode == "live" else 25)
    concurrency = args.concurrency if args.concurrency is not None else (1 if args.gemini_mode == "live" else 5)
    if args.gemini_mode == "live" and (submissions > 20 or concurrency > 2):
        raise RuntimeError("Live runs are capped at 20 submissions and concurrency 2.")
    async with httpx.AsyncClient(timeout=args.timeout) as client:
        await validate_server(client, args.base_url, args.gemini_mode)
        rows, summary = await run_e2e(
            client=client,
            base_url=args.base_url,
            endpoint=args.endpoint,
            fixtures=fixtures,
            submissions=submissions,
            concurrency=concurrency,
            poll_interval=args.poll_interval,
            timeout=args.timeout,
            seed=args.seed,
        )
        metrics_response = await client.get(
            f"{args.base_url.rstrip('/')}/api/v1/health/performance"
        )
        metrics_response.raise_for_status()
        summary["server_metrics"] = metrics_response.json()
    summary.update(
        gemini_mode=args.gemini_mode,
        concurrency=concurrency,
        fixture_manifest_version=manifest["manifest_version"],
    )
    environment = environment_metadata(args.notes, " ".join(sys.argv))
    write_result_bundle(args.output, rows, summary, environment, manifest)
    print(json.dumps(summary, indent=2))
    print(f"Machine-readable results: {args.output}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.poll_interval <= 0 or args.timeout <= 0:
        raise SystemExit("Poll interval and timeout must be positive.")
    try:
        return asyncio.run(async_main(args))
    except Exception as exc:
        print(f"Benchmark failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
