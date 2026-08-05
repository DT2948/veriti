import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from scripts.generate_privacy_benchmark_fixtures import generate_fixtures


class FixtureGeneratorTests(unittest.TestCase):
    def test_generation_is_deterministic_and_manifest_matches(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            manifest_a = generate_fixtures(Path(first), profile="small")
            manifest_b = generate_fixtures(Path(second), profile="small")
            self.assertEqual(
                [(row["filename"], row["sha256"]) for row in manifest_a["fixtures"]],
                [(row["filename"], row["sha256"]) for row in manifest_b["fixtures"]],
            )
            stored = json.loads((Path(first) / "manifest.json").read_text())
            self.assertEqual(stored["fixture_count"], len(stored["fixtures"]))
            for row in stored["fixtures"]:
                path = Path(first) / row["filename"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row["sha256"])

    def test_metadata_dimensions_and_invalid_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = generate_fixtures(Path(directory), profile="small")
            gps = next(row for row in manifest["fixtures"] if row["gps"])
            with Image.open(Path(directory) / gps["filename"]) as image:
                self.assertEqual(image.size, (gps["width"], gps["height"]))
                exif = image.getexif()
                self.assertEqual(exif.get(271), "Example Camera Co.")
                self.assertIn(34853, exif)
            invalid = [row for row in manifest["fixtures"] if row["intentionally_invalid"]]
            self.assertTrue(invalid)
            for row in invalid:
                with self.assertRaises((UnidentifiedImageError, OSError)):
                    Image.open(Path(directory) / row["filename"]).verify()


if __name__ == "__main__":
    unittest.main()
