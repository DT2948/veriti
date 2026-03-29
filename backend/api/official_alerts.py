from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.incidents import _to_incident_response
from database import get_db
from schemas.incident import IncidentResponse, OfficialSourceRequest
from services.gemini_service import parse_official_source
from services.ingestion_service import create_official_alert


router = APIRouter(prefix="/official-alerts", tags=["official-alerts"])


@router.post("", response_model=IncidentResponse)
def create_official_source_alert(
    request: OfficialSourceRequest,
    db: Session = Depends(get_db),
) -> IncidentResponse:
    try:
        parsed = parse_official_source(request.text)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to parse official source text",
        ) from exc

    alert_data = {
        "latitude": parsed["latitude"],
        "longitude": parsed["longitude"],
        "text_note": f"[Official Source] {parsed['summary']}",
        "title": parsed["title"],
        "summary": parsed["summary"],
        "source_url": request.source_url,
    }

    try:
        incident = create_official_alert(
            db,
            alert_data,
            incident_type_override=parsed["incident_type"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create official alert: {exc}",
        ) from exc

    return _to_incident_response(incident)
