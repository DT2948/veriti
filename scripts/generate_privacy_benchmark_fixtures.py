from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


DEFAULT_SEED = 20260418
SYNTHETIC_PII = [
    "Jordan Example",
    "555-010-1234",
    "jordan@example.test",
    "100 Example Street",
]


@dataclass(frozen=True)
class FixtureSpec:
    filename: str
    format: str
    width: int
    height: int
    size_category: str
    fixture_category: str
    exif: bool = False
    gps: bool = False
    rendered_text: bool = False
    intentionally_invalid: bool = False
    expected_processing_outcome: str = "success"


FIXTURE_SPECS = (
    FixtureSpec("small_gradient_exif_gps.jpg", "JPEG", 640, 480, "small", "gradient", True, True),
    FixtureSpec("small_pattern.png", "PNG", 640, 480, "small", "geometric_pattern"),
    FixtureSpec("small_texture.jpg", "JPEG", 640, 480, "small", "photo_like_texture"),
    FixtureSpec("small_synthetic_text.png", "PNG", 640, 480, "small", "synthetic_text", rendered_text=True),
    FixtureSpec("medium_gradient.jpg", "JPEG", 1920, 1080, "medium", "gradient"),
    FixtureSpec("medium_pattern.png", "PNG", 1920, 1080, "medium", "geometric_pattern"),
    FixtureSpec("medium_texture_exif.jpg", "JPEG", 1920, 1080, "medium", "photo_like_texture", True),
    FixtureSpec("medium_synthetic_text.jpg", "JPEG", 1920, 1080, "medium", "synthetic_text", rendered_text=True),
    FixtureSpec("large_gradient_exif_gps.jpg", "JPEG", 4032, 3024, "large", "gradient", True, True),
    FixtureSpec("large_pattern.png", "PNG", 4032, 3024, "large", "geometric_pattern"),
    FixtureSpec("large_texture.jpg", "JPEG", 4032, 3024, "large", "photo_like_texture"),
    FixtureSpec("large_synthetic_text.jpg", "JPEG", 4032, 3024, "large", "synthetic_text", rendered_text=True),
    FixtureSpec("corrupted.jpg", "JPEG", 0, 0, "invalid", "corrupted_jpeg", intentionally_invalid=True, expected_processing_outcome="failure"),
    FixtureSpec("unsupported.bin", "BINARY", 0, 0, "invalid", "unsupported_input", intentionally_invalid=True, expected_processing_outcome="failure"),
)


def _gradient(width: int, height: int, seed: int) -> Image.Image:
    rng = random.Random(seed)
    start = tuple(rng.randrange(20, 130) for _ in range(3))
    end = tuple(rng.randrange(140, 240) for _ in range(3))
    row = Image.new("RGB", (width, 1))
    pixels = []
    for x in range(width):
        ratio = x / max(1, width - 1)
        pixels.append(tuple(round(start[c] + (end[c] - start[c]) * ratio) for c in range(3)))
    row.putdata(pixels)
    image = row.resize((width, height))
    draw = ImageDraw.Draw(image)
    for index in range(12):
        x = (index * width) // 12
        y = int(height * (0.25 + 0.18 * math.sin(index)))
        draw.ellipse((x, y, x + max(12, width // 30), y + max(12, height // 25)), fill=(220, 120, 70))
    return image


def _pattern(width: int, height: int, seed: int) -> Image.Image:
    rng = random.Random(seed)
    image = Image.new("RGB", (width, height), (35, 45, 58))
    draw = ImageDraw.Draw(image)
    step = max(24, min(width, height) // 18)
    for y in range(0, height, step):
        for x in range(0, width, step):
            color = (rng.randrange(50, 220), rng.randrange(50, 220), rng.randrange(50, 220))
            if ((x // step) + (y // step)) % 2:
                draw.rectangle((x, y, min(width, x + step), min(height, y + step)), fill=color)
            else:
                draw.ellipse((x, y, min(width, x + step), min(height, y + step)), fill=color)
    return image


def _texture(width: int, height: int, seed: int) -> Image.Image:
    rng = random.Random(seed)
    raw = rng.randbytes(width * height * 3)
    noise = Image.frombytes("RGB", (width, height), raw)
    base = _gradient(width, height, seed + 1)
    return Image.blend(base, noise, 0.28)


def _synthetic_text(width: int, height: int, seed: int) -> Image.Image:
    image = _pattern(width, height, seed)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    padding = max(16, width // 30)
    box_height = max(110, height // 3)
    draw.rounded_rectangle(
        (padding, padding, width - padding, min(height - padding, padding + box_height)),
        radius=max(8, padding // 2),
        fill=(242, 239, 232),
    )
    line_height = max(18, box_height // 6)
    for index, value in enumerate(SYNTHETIC_PII):
        draw.text((padding * 2, padding * 2 + index * line_height), value, fill=(25, 31, 42), font=font)
    return image


def _fake_exif(include_gps: bool) -> Image.Exif:
    exif = Image.Exif()
    exif[270] = "Synthetic benchmark fixture"
    exif[271] = "Example Camera Co."
    exif[272] = "Deterministic Model 1"
    exif[305] = "Veriti Fixture Generator"
    exif[306] = "2026:04:18 12:00:00"
    exif[36867] = "2026:04:18 12:00:00"
    if include_gps:
        exif[34853] = {
            1: "N",
            2: (25.0, 12.0, 0.0),
            3: "E",
            4: (55.0, 16.0, 0.0),
        }
    return exif


def _build_image(spec: FixtureSpec, seed: int) -> Image.Image:
    if spec.fixture_category == "gradient":
        return _gradient(spec.width, spec.height, seed)
    if spec.fixture_category == "geometric_pattern":
        return _pattern(spec.width, spec.height, seed)
    if spec.fixture_category == "photo_like_texture":
        return _texture(spec.width, spec.height, seed)
    if spec.fixture_category == "synthetic_text":
        return _synthetic_text(spec.width, spec.height, seed)
    raise ValueError(f"Unsupported fixture category: {spec.fixture_category}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_fixtures(output_dir: Path, seed: int = DEFAULT_SEED, profile: str = "full") -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    specs = FIXTURE_SPECS
    if profile == "small":
        specs = tuple(spec for spec in FIXTURE_SPECS if spec.size_category in {"small", "invalid"})
    elif profile != "full":
        raise ValueError("profile must be 'full' or 'small'")

    rows: list[dict] = []
    for index, spec in enumerate(specs):
        path = output_dir / spec.filename
        fixture_seed = seed + index * 997
        if spec.fixture_category == "corrupted_jpeg":
            data = b"\xff\xd8\xff\xe0" + random.Random(fixture_seed).randbytes(96)
            path.write_bytes(data)
        elif spec.fixture_category == "unsupported_input":
            path.write_bytes(b"VERITI_BENCHMARK_UNSUPPORTED\x00\x01\x02")
        else:
            image = _build_image(spec, fixture_seed)
            save_options: dict = {}
            if spec.format == "JPEG":
                save_options.update(quality=88, optimize=False, progressive=False)
                if spec.exif:
                    save_options["exif"] = _fake_exif(spec.gps)
            else:
                save_options.update(compress_level=6)
            image.save(path, format=spec.format, **save_options)
            image.close()

        row = asdict(spec)
        row.update(
            fixture_id=path.stem,
            file_size=path.stat().st_size,
            sha256=_sha256(path),
            random_seed=fixture_seed,
            synthetic_pii=SYNTHETIC_PII if spec.rendered_text else [],
            image_text_redaction_expected=False,
        )
        rows.append(row)

    manifest = {
        "manifest_version": 1,
        "generator_seed": seed,
        "profile": profile,
        "fixture_count": len(rows),
        "fixtures": rows,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic Veriti privacy benchmark fixtures.")
    parser.add_argument("--output", type=Path, default=Path("benchmark_fixtures/privacy"))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--profile", choices=("full", "small"), default="full")
    args = parser.parse_args()
    manifest = generate_fixtures(args.output, args.seed, args.profile)
    print(f"Generated {manifest['fixture_count']} deterministic fixtures in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
