import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


async def save_upload(file: UploadFile, upload_dir: str = "uploads") -> str:
    directory = Path(upload_dir)
    directory.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "").suffix.lower()
    filename = f"{uuid.uuid4()}{suffix}"
    destination = directory / filename

    try:
        async with aiofiles.open(destination, "wb") as out_file:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                await out_file.write(chunk)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {exc}",
        ) from exc
    finally:
        await file.close()

    return str(destination)


def delete_raw_media(file_path: str) -> None:
    if file_path and os.path.exists(file_path):
        os.remove(file_path)


def get_media_type(filename: str | None) -> str | None:
    if not filename:
        return None

    extension = Path(filename).suffix.lower()
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in VIDEO_EXTENSIONS:
        return "video"
    return None
