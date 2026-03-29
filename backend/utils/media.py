import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


logger = logging.getLogger(__name__)


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


def delete_raw_media(file_path: str, upload_dir: str = "uploads") -> None:
    if not file_path:
        return

    target_path = Path(file_path)
    if not target_path.exists():
        logger.info("Raw media already absent, skipping delete: %s", file_path)
        return

    resolved_upload_dir = Path(upload_dir).resolve()
    resolved_target = target_path.resolve()

    try:
        resolved_target.relative_to(resolved_upload_dir)
    except ValueError as exc:
        raise ValueError(
            f"Refusing to delete media outside upload dir: {resolved_target}"
        ) from exc

    os.remove(resolved_target)
    logger.info("Deleted raw media: %s", resolved_target)


def scrub_video_metadata(file_path: str) -> None:
    if not file_path:
        return

    source_path = Path(file_path)
    if not source_path.exists():
        return

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        logger.warning("Video metadata scrubbing skipped because ffmpeg is not installed.")
        return

    temp_output_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=source_path.parent,
            prefix=f"{source_path.stem}_scrubbed_",
            suffix=source_path.suffix,
            delete=False,
        ) as temp_output:
            temp_output_path = temp_output.name

        # Best-effort privacy scrub: container metadata is removed without
        # re-encoding the underlying streams. This requires ffmpeg server-side.
        subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-i",
                str(source_path),
                "-map_metadata",
                "-1",
                "-c",
                "copy",
                temp_output_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        os.replace(temp_output_path, source_path)
        logger.info("Scrubbed video metadata: %s", source_path)
    except Exception:
        logger.warning("Failed to scrub video metadata for %s", source_path, exc_info=True)
        if temp_output_path:
            try:
                Path(temp_output_path).unlink(missing_ok=True)
            except OSError:
                logger.warning(
                    "Failed to clean temporary scrubbed video file for %s",
                    source_path,
                    exc_info=True,
                )


def get_media_type(filename: str | None) -> str | None:
    if not filename:
        return None

    extension = Path(filename).suffix.lower()
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in VIDEO_EXTENSIONS:
        return "video"
    return None
