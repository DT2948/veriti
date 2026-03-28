from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models.submission import Submission
from schemas.submission import SubmissionResponse, SubmissionStatus
from utils.location import coarsen_location
from utils.media import get_media_type, save_upload
from utils.privacy import sanitize_text, strip_exif
from workers.pipeline import run_verification_pipeline


settings = get_settings()
router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("/upload", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def upload_submission(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(default=None),
    text_note: str | None = Form(default=None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    device_trust_score: float | None = Form(default=None),
    integrity_token: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> SubmissionResponse:
    try:
        media_path = None
        media_type = None
        if file is not None:
            media_type = get_media_type(file.filename)
            if media_type is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported media type. Please upload an image or video.",
                )
            media_path = await save_upload(file, settings.upload_dir)
            if media_type == "image":
                strip_exif(media_path)

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

        background_tasks.add_task(run_verification_pipeline, None, submission.id)
        return SubmissionResponse(
            id=submission.id,
            verification_status=submission.verification_status,
            submitted_at=submission.submitted_at,
            message="Submission received and queued for verification.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload submission: {exc}",
        ) from exc


@router.get("/{submission_id}/status", response_model=SubmissionStatus)
def get_submission_status(submission_id: str, db: Session = Depends(get_db)) -> SubmissionStatus:
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return SubmissionStatus(
        id=submission.id,
        verification_status=submission.verification_status,
        incident_id=submission.incident_id,
    )
