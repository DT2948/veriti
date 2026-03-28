import re
from pathlib import Path

from PIL import Image


EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"(?:(?:\+|00)\d{1,3}[\s-]?)?(?:\d[\s-]?){8,14}\d")


def strip_exif(file_path: str) -> None:
    suffix = Path(file_path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        return

    with Image.open(file_path) as image:
        data = list(image.getdata())
        sanitized = Image.new(image.mode, image.size)
        sanitized.putdata(data)
        sanitized.save(file_path)


def sanitize_text(text: str | None) -> str | None:
    if text is None:
        return None

    redacted = EMAIL_RE.sub("[redacted-email]", text)
    redacted = PHONE_RE.sub("[redacted-phone]", redacted)
    return redacted.strip()
