from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models.incident import Incident
from services.elevenlabs_service import generate_audio
from services.gemini_service import generate_audio_briefing_script


router = APIRouter(prefix="/audio-briefing", tags=["audio-briefing"])
settings = get_settings()


@router.get("")
def get_audio_briefing(db: Session = Depends(get_db)) -> Response:
    if not settings.elevenlabs_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audio briefing not configured",
        )

    try:
        incidents = db.scalars(
            select(Incident)
            .where(Incident.is_active.is_(True))
            .order_by(Incident.timestamp_last_updated.desc())
        ).all()
        script = generate_audio_briefing_script(incidents)
        audio_bytes = generate_audio(script)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=briefing.mp3",
                "Cache-Control": "no-cache",
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audio briefing temporarily unavailable",
        ) from exc
