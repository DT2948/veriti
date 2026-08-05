from datetime import datetime, timezone
import time

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from config import get_settings
from benchmarking.metrics import correlations, registry
from database import get_db
from models.submission import Submission
from schemas.submission import SubmissionResponse, SubmissionStatus
from utils.location import coarsen_location
from utils.media import get_media_type, save_upload, scrub_video_metadata
from utils.privacy import sanitize_text, strip_exif
from utils.rate_limiter import upload_rate_limiter
from workers.pipeline import run_verification_pipeline


settings = get_settings()
router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("/upload", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def upload_submission(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(default=None),
    text_note: str | None = Form(default=None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    device_trust_score: float | None = Form(default=None),
    integrity_token: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> SubmissionResponse:
    started = time.perf_counter()
    metric_outcome = "success"
    try:
        # Client IP is used only for short-lived in-memory rate limiting.
        # It is never stored with submissions and never written to persistent storage.
        client_ip = request.client.host if request.client else "unknown"
        if not settings.benchmark_mode and not upload_rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many submissions. Please wait before submitting again.",
            )

        media_path = None
        media_type = None
        if file is not None:
            media_started = time.perf_counter()
            media_type = get_media_type(file.filename)
            if media_type is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported media type. Please upload an image or video.",
                )
            media_path = await save_upload(file, settings.upload_dir)
            if media_type == "image":
                strip_exif(media_path)
            else:
                scrub_video_metadata(media_path)
            if settings.performance_metrics_enabled or settings.benchmark_mode:
                registry.record(
                    "verification.media_prepare",
                    (time.perf_counter() - media_started) * 1000,
                    labels={"media_type": media_type},
                )

        sanitized_note = sanitize_text(text_note)
        coarse_lat, coarse_lng, grid_cell = coarsen_location(
            latitude,
            longitude,
            settings.grid_size_meters,
        )

        submission = Submission(
            source_type="public",
            media_type=media_type,
            media_path=media_path,
            text_note=sanitized_note,
            latitude=coarse_lat,
            longitude=coarse_lng,
            grid_cell=grid_cell,
            submitted_at=datetime.now(timezone.utc),
            device_trust_score=device_trust_score,
            integrity_token=integrity_token,
            verification_status="pending",
            anonymous_token=None,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

        correlations.accepted(submission.id, settings.gemini_mode)
        background_tasks.add_task(run_verification_pipeline, None, submission.id)
        return SubmissionResponse(
            id=submission.id,
            correlation_id=submission.id,
            verification_status=submission.verification_status,
            submitted_at=submission.submitted_at,
            message="Submission received and queued for verification.",
        )
    except HTTPException:
        metric_outcome = "client_error"
        raise
    except Exception as exc:
        metric_outcome = "error"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload submission.",
        ) from exc
    finally:
        if settings.performance_metrics_enabled or settings.benchmark_mode:
            registry.record(
                "submission.accept",
                (time.perf_counter() - started) * 1000,
                metric_outcome,
            )


@router.get("/{submission_id}/status", response_model=SubmissionStatus)
def get_submission_status(submission_id: str, db: Session = Depends(get_db)) -> SubmissionStatus:
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    timing = correlations.get(submission.id)
    verification_duration_ms = None
    if submission.processed_at is not None:
        submitted_at = submission.submitted_at
        processed_at = submission.processed_at
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=timezone.utc)
        if processed_at.tzinfo is None:
            processed_at = processed_at.replace(tzinfo=timezone.utc)
        verification_duration_ms = round(
            (processed_at - submitted_at).total_seconds() * 1000,
            3,
        )
    return SubmissionStatus(
        id=submission.id,
        correlation_id=submission.id,
        verification_status=submission.verification_status,
        incident_id=submission.incident_id,
        submitted_at=submission.submitted_at,
        processed_at=submission.processed_at,
        verification_duration_ms=verification_duration_ms,
        gemini_mode=timing.gemini_mode if timing else settings.gemini_mode,
        fallback_used=timing.fallback_used if timing else False,
    )
