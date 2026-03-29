from datetime import datetime, timezone

from sqlalchemy import select
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


def _adjacent_grid_cells(grid_cell: str) -> set[str]:
    try:
        _, lat_idx, lng_idx = grid_cell.split("_")
        lat_index = int(lat_idx)
        lng_index = int(lng_idx)
    except (ValueError, AttributeError):
        return {grid_cell}

    cells = set()
    for lat_offset in (-1, 0, 1):
        for lng_offset in (-1, 0, 1):
            cells.add(f"grid_{lat_index + lat_offset}_{lng_index + lng_offset}")
    return cells


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


def create_official_alert(
    db: Session,
    alert_data: dict,
    incident_type_override: str | None = None,
) -> Incident:
    lat, lng, grid_cell = coarsen_location(
        float(alert_data["latitude"]),
        float(alert_data["longitude"]),
        settings.grid_size_meters,
    )
    submitted_at = alert_data.get("submitted_at") or datetime.now(timezone.utc)
    text_note = sanitize_text(alert_data.get("text_note"))
    incident_type = (
        incident_type_override
        if incident_type_override and incident_type_override != "unknown"
        else extract_incident_type(text_note or alert_data.get("title", ""))
    )

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

    nearby_public_incidents = db.scalars(
        select(Incident).where(
            Incident.is_active.is_(True),
            Incident.grid_cell.in_(_adjacent_grid_cells(grid_cell)),
        )
    ).all()

    merge_target = next(
        (
            nearby_incident
            for nearby_incident in nearby_public_incidents
            if nearby_incident.source_type != "official"
        ),
        None,
    )

    if merge_target is not None:
        merge_target.official_overlap = True
        merge_target.source_type = "mixed"
        merge_target.type = incident_type
        merge_target.title = alert_data.get("title") or merge_target.title
        merge_target.summary = alert_data.get("summary") or merge_target.summary
        merge_target.timestamp_last_updated = submitted_at
        merge_target.tags = f'["{incident_type}", "official"]'
        merge_target.verification_notes = "Merged with official alert ingestion."
        submission.incident_id = merge_target.id
        db.add_all([submission, merge_target])
        db.flush()
        score_incident(db, merge_target)
        incident = merge_target
    else:
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
            tags=f'["{incident_type}", "official"]',
            verification_notes="Created from official alert ingestion.",
            is_active=True,
        )
        db.add(incident)
        db.flush()

        submission.incident_id = incident.id
        db.add(submission)
        db.flush()

        for nearby_incident in nearby_public_incidents:
            if nearby_incident.source_type == "official":
                continue
            nearby_incident.official_overlap = True
            db.add(nearby_incident)
            db.flush()
            score_incident(db, nearby_incident)

    db.commit()
    db.refresh(incident)
    return incident
