import asyncio
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from benchmarking.metrics import MetricRegistry, registry
from main import app, settings
from workers.pipeline import run_verification_pipeline


class MetricRegistryTests(unittest.TestCase):
    def test_buffer_is_bounded_and_active_returns_to_zero(self):
        metrics = MetricRegistry(max_events=2)
        for _ in range(3):
            started = metrics.begin()
            metrics.finish("test.operation", started)
        self.assertEqual(len(metrics.snapshot()), 2)
        self.assertEqual(metrics.active, 0)
        self.assertGreaterEqual(metrics.peak_active, 1)

    def test_http_middleware_uses_route_template(self):
        async def exercise():
            previous = settings.performance_metrics_enabled
            settings.performance_metrics_enabled = True
            registry.clear()
            try:
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    ok = await client.get("/")
                    missing = await client.get("/private-value-123")
                self.assertEqual(ok.status_code, 200)
                self.assertEqual(missing.status_code, 404)
                events = [event for event in registry.snapshot() if event.operation == "http.request"]
                self.assertEqual(events[0].labels["route"], "/")
                self.assertEqual(events[1].labels["route"], "unmatched")
                self.assertNotIn("private-value-123", str(events))
                self.assertEqual(registry.active, 0)
            finally:
                settings.performance_metrics_enabled = previous
        asyncio.run(exercise())


class PipelineLoggingTests(unittest.TestCase):
    def test_pipeline_logs_failure_without_exception_message(self):
        submission = SimpleNamespace(
            id="safe-correlation-id",
            media_path=None,
            media_type=None,
            verification_status="pending",
            processed_at=None,
        )

        class FakeSession:
            def get(self, model, identifier):
                return submission
            def add(self, value):
                pass
            def commit(self):
                pass
            def refresh(self, value):
                pass

        secret = "synthetic-private-caption"
        with patch("workers.pipeline.process_submission", side_effect=ValueError(secret)):
            with self.assertLogs("workers.pipeline", level=logging.ERROR) as captured:
                run_verification_pipeline(FakeSession(), submission.id)
        output = "\n".join(captured.output)
        self.assertIn("exception_class=ValueError", output)
        self.assertNotIn(secret, output)
        self.assertEqual(submission.verification_status, "rejected")


if __name__ == "__main__":
    unittest.main()
