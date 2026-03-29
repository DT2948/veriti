import re
from pathlib import Path

from PIL import Image


EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"(?:(?:\+|00)\d{1,3}[\s-]?)?(?:\d[\s().-]?){8,16}\d")
HANDLE_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_]{2,32}\b")
SELF_ID_RE = re.compile(
    r"\b(?:[Mm]y name is|[Tt]his is|[Ii] am|[Ii]'m)\s+[A-Za-z]+(?:\s+[A-Za-z]+){0,2}\b"
)


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

    # Best-effort PII scrubbing favors over-redaction so free-text notes
    # cannot easily self-identify a reporter.
    redacted = EMAIL_RE.sub("[redacted]", text)
    redacted = PHONE_RE.sub("[redacted]", redacted)
    redacted = SELF_ID_RE.sub("[redacted]", redacted)
    redacted = HANDLE_RE.sub("[redacted]", redacted)
    return redacted.strip()
