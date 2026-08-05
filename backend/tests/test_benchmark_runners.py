import asyncio
import tempfile
import unittest
from pathlib import Path

import httpx

from scripts.generate_privacy_benchmark_fixtures import generate_fixtures
from backend.scripts.e2e_benchmark import run_e2e
from backend.scripts.load_test import run_load


class LoadRunnerTests(unittest.TestCase):
    def test_load_summary_rotation_and_errors(self):
        async def exercise(fixtures):
            active = 0
            peak = 0

            async def handler(request):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                await asyncio.sleep(0.005)
                active -= 1
                return httpx.Response(201, json={"id": "safe-id"})

            rows, summary = await run_load(
                base_url="http://test",
                endpoint="/api/v1/submissions/upload",
                fixtures=fixtures,
                concurrency=3,
                total_requests=8,
                warmup=1,
                timeout=1,
                seed=7,
                transport=httpx.MockTransport(handler),
            )
            self.assertEqual(len(rows), 8)
            self.assertEqual(summary["success_count"], 8)
            self.assertLessEqual(peak, 3)
            self.assertGreater(len({row["fixture_id"] for row in rows}), 1)

        with tempfile.TemporaryDirectory() as directory:
            manifest = generate_fixtures(Path(directory), profile="small")
            fixtures = [
                {**row, "path": Path(directory) / row["filename"]}
                for row in manifest["fixtures"]
                if not row["intentionally_invalid"]
            ]
            asyncio.run(exercise(fixtures))

    def test_timeout_is_classified(self):
        async def handler(request):
            raise httpx.ReadTimeout("synthetic timeout", request=request)

        with tempfile.TemporaryDirectory() as directory:
            manifest = generate_fixtures(Path(directory), profile="small")
            fixture = next(row for row in manifest["fixtures"] if not row["intentionally_invalid"])
            fixture = {**fixture, "path": Path(directory) / fixture["filename"]}
            rows, summary = asyncio.run(run_load(
                base_url="http://test",
                endpoint="/upload",
                fixtures=[fixture],
                concurrency=1,
                total_requests=1,
                warmup=0,
                timeout=1,
                seed=1,
                transport=httpx.MockTransport(handler),
            ))
            self.assertEqual(rows[0]["outcome"], "timeout")
            self.assertEqual(summary["failure_count"], 1)


class EndToEndRunnerTests(unittest.TestCase):
    def test_completion_rejection_and_timeout_are_recorded(self):
        async def exercise(fixtures):
            submitted = 0

            async def handler(request):
                nonlocal submitted
                if request.method == "POST":
                    submitted += 1
                    return httpx.Response(201, json={"id": "id-" + str(submitted)})
                identifier = request.url.path.split("/")[-2]
                if identifier == "id-1":
                    return httpx.Response(200, json={
                        "verification_status": "verified",
                        "fallback_used": True,
                        "verification_duration_ms": 12.5,
                    })
                if identifier == "id-2":
                    return httpx.Response(200, json={
                        "verification_status": "rejected",
                        "fallback_used": False,
                        "verification_duration_ms": 9.0,
                    })
                return httpx.Response(200, json={
                    "verification_status": "processing",
                    "fallback_used": False,
                    "verification_duration_ms": None,
                })

            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                rows, summary = await run_e2e(
                    client=client,
                    base_url="http://test",
                    endpoint="/api/v1/submissions/upload",
                    fixtures=fixtures,
                    submissions=3,
                    concurrency=1,
                    poll_interval=0.001,
                    timeout=0.01,
                    seed=2,
                )
            self.assertEqual(summary["successful_completions"], 1)
            self.assertEqual(summary["rejections"], 1)
            self.assertEqual(summary["timeouts"], 1)
            self.assertEqual(summary["fallback_count"], 1)
            self.assertIsNotNone(rows[0]["end_to_end_duration_ms"])

        with tempfile.TemporaryDirectory() as directory:
            manifest = generate_fixtures(Path(directory), profile="small")
            fixtures = [
                {**row, "path": Path(directory) / row["filename"]}
                for row in manifest["fixtures"]
                if not row["intentionally_invalid"]
            ]
            asyncio.run(exercise(fixtures))


if __name__ == "__main__":
    unittest.main()
