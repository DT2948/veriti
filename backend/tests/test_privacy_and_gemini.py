import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from scripts.generate_privacy_benchmark_fixtures import generate_fixtures
from services import gemini_service
from utils.privacy import sanitize_text, strip_exif


class PrivacyCorrectnessTests(unittest.TestCase):
    def test_real_backend_strip_exif_and_text_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = generate_fixtures(Path(directory), profile="small")
            row = next(item for item in manifest["fixtures"] if item["gps"])
            path = Path(directory) / row["filename"]
            before = path.read_bytes()
            strip_exif(str(path))
            with Image.open(path) as image:
                self.assertFalse(image.getexif())
                image.verify()
            self.assertNotEqual(before, path.read_bytes())

        sanitized = sanitize_text(
            "My name is Jordan Example, jordan@example.test, +1 555-010-1234, @example_user"
        )
        self.assertNotIn("Jordan Example", sanitized)
        self.assertNotIn("jordan@example.test", sanitized)
        self.assertNotIn("555-010-1234", sanitized)
        self.assertNotIn("@example_user", sanitized)


class GeminiModeTests(unittest.TestCase):
    def test_stubbed_mode_never_builds_live_client(self):
        previous_benchmark = gemini_service.settings.benchmark_mode
        previous_requested = gemini_service.settings.requested_gemini_mode
        gemini_service.settings.benchmark_mode = True
        gemini_service.settings.requested_gemini_mode = "stubbed"
        try:
            with patch("services.gemini_service._get_client") as get_client:
                result = gemini_service._generate_text("not logged", "gemini.incident_type")
            self.assertEqual(result, "unknown")
            get_client.assert_not_called()
        finally:
            gemini_service.settings.benchmark_mode = previous_benchmark
            gemini_service.settings.requested_gemini_mode = previous_requested

    def test_disabled_mode_never_builds_live_client(self):
        previous_benchmark = gemini_service.settings.benchmark_mode
        previous_requested = gemini_service.settings.requested_gemini_mode
        gemini_service.settings.benchmark_mode = True
        gemini_service.settings.requested_gemini_mode = "disabled"
        try:
            with patch("services.gemini_service._get_client") as get_client:
                with self.assertRaises(RuntimeError):
                    gemini_service._generate_text("not logged", "gemini.summary")
            get_client.assert_not_called()
        finally:
            gemini_service.settings.benchmark_mode = previous_benchmark
            gemini_service.settings.requested_gemini_mode = previous_requested


if __name__ == "__main__":
    unittest.main()
