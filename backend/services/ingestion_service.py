from datetime import datetime, timezone

from sqlalchemy.orm import Session

from config import get_settings
from models.incident import Incident
from models.submission import Submission
from services.clustering_service import cluster_submission
from services.gemini_service import extract_incident_type
from services.scoring_service import score_incident
from services.verification_service import verify_submission
from utils.location import coarsen_location
from utils.privacy import sanitize_text


settings = get_settings()


def process_submission(db: Session, submission_id: str) -> tuple[Submission, Incident | None]:
    submission = db.get(Submission, submission_id)
    if not submission:
        raise ValueError(f"Submission {submission_id} not found.")

    submission = verify_submission(db, submission)
    incident = cluster_submission(db, submission)
    score_incident(db, incident)
    db.refresh(submission)
    db.refresh(incident)
    return submission, incident


def create_official_alert(db: Session, alert_data: dict) -> Incident:
    lat, lng, grid_cell = coarsen_location(
        float(alert_data["latitude"]),
        float(alert_data["longitude"]),
        settings.grid_size_meters,
    )
    submitted_at = alert_data.get("submitted_at") or datetime.now(timezone.utc)
    text_note = sanitize_text(alert_data.get("text_note"))
    incident_type = extract_incident_type(text_note or alert_data.get("title", ""))

    submission = Submission(
        source_type="official",
        media_type=None,
        media_path=None,
        text_note=text_note,
        latitude=lat,
        longitude=lng,
        grid_cell=grid_cell,
        submitted_at=submitted_at,
        device_trust_score=1.0,
        integrity_token="official-source",
        verification_status="verified",
        anonymous_token=None,
        processed_at=submitted_at,
    )
    db.add(submission)
    db.flush()

    incident = Incident(
        type=incident_type,
        title=alert_data.get("title") or f"Official {incident_type} alert",
        summary=alert_data.get("summary"),
        source_type="official",
        confidence_tier="official",
        confidence_score=0.98,
        latitude=lat,
        longitude=lng,
        grid_cell=grid_cell,
        timestamp_first_seen=submitted_at,
        timestamp_last_updated=submitted_at,
        number_of_reports=1,
        official_overlap=True,
        media_count=0,
        tags=f'["{incident_type}", "official", "{grid_cell}"]',
        verification_notes="Created from official alert ingestion.",
        is_active=True,
    )
    db.add(incident)
    db.flush()

    submission.incident_id = incident.id
    db.add(submission)
    db.commit()
    db.refresh(incident)
    return incident
