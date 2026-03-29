from datetime import datetime, timedelta, timezone

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from config import get_settings
from models.incident import Incident
from models.submission import Submission
from services.gemini_service import extract_incident_type
from utils.dubai_locations import get_neighborhood_name
from utils.hashing import hamming_distance


settings = get_settings()


def build_incident_title(incident_type: str, grid_cell: str, latitude: float, longitude: float) -> str:
    neighborhood_name = get_neighborhood_name(grid_cell, latitude, longitude)
    readable_type = incident_type.replace("_", " ").title()
    return f"{readable_type} reported near {neighborhood_name}"


def find_nearby_incidents(
    db: Session,
    grid_cell: str,
    time_window_minutes: int = 30,
    reference_time: datetime | None = None,
) -> list[Incident]:
    reference_time = reference_time or datetime.now(timezone.utc)
    cutoff = reference_time - timedelta(minutes=time_window_minutes)
    stmt: Select[tuple[Incident]] = (
        select(Incident)
        .options(joinedload(Incident.submissions))
        .where(
            Incident.grid_cell == grid_cell,
            Incident.timestamp_last_updated >= cutoff,
            Incident.is_active.is_(True),
        )
        .order_by(Incident.timestamp_last_updated.desc())
    )
    return db.scalars(stmt).unique().all()


def _find_duplicate_submission(db: Session, submission: Submission) -> Submission | None:
    if not submission.perceptual_hash:
        return None

    existing_submissions = db.scalars(
        select(Submission).where(
            Submission.perceptual_hash.is_not(None),
            Submission.incident_id.is_not(None),
            Submission.id != submission.id,
        )
    ).all()

    best_match: Submission | None = None
    best_distance: int | None = None
    for existing_submission in existing_submissions:
        if not existing_submission.perceptual_hash:
            continue

        distance = hamming_distance(submission.perceptual_hash, existing_submission.perceptual_hash)
        if distance > settings.duplicate_hash_threshold:
            continue

        if best_distance is None or distance < best_distance:
            best_match = existing_submission
            best_distance = distance

    return best_match


def _assign_submission_to_incident(
    db: Session,
    submission: Submission,
    incident: Incident,
    duplicate_source: Submission | None = None,
) -> Incident:
    submission.incident_id = incident.id
    if duplicate_source is not None:
        submission.duplicate_group_id = (
            duplicate_source.duplicate_group_id or duplicate_source.id
        )

    incident.number_of_reports += 1
    incident.timestamp_last_updated = datetime.now(timezone.utc)
    if submission.media_type:
        incident.media_count += 1

    if submission.source_type == "official":
        incident.official_overlap = True
        incident.source_type = "official" if incident.number_of_reports == 1 else "mixed"
    elif incident.source_type == "official":
        incident.source_type = "mixed"

    db.add_all([submission, incident])
    db.commit()
    db.refresh(incident)
    return incident


def _create_incident_for_submission(db: Session, submission: Submission) -> Incident:
    incident_type = extract_incident_type(submission.text_note or "")
    incident = Incident(
        type=incident_type,
        title=build_incident_title(
            incident_type,
            submission.grid_cell,
            submission.latitude,
            submission.longitude,
        ),
        summary=None,
        source_type=submission.source_type,
        confidence_tier="official" if submission.source_type == "official" else "unverified",
        confidence_score=0.95 if submission.source_type == "official" else 0.15,
        latitude=submission.latitude,
        longitude=submission.longitude,
        grid_cell=submission.grid_cell,
        timestamp_first_seen=submission.submitted_at,
        timestamp_last_updated=submission.submitted_at,
        number_of_reports=1,
        official_overlap=submission.source_type == "official",
        media_count=1 if submission.media_type else 0,
        tags=f'["{incident_type}"]',
        verification_notes="Created from first clustered submission.",
        is_active=True,
    )
    db.add(incident)
    db.flush()

    submission.incident_id = incident.id
    db.add(submission)
    db.commit()
    db.refresh(incident)
    return incident


def cluster_submission(db: Session, submission: Submission) -> Incident:
    duplicate_submission = _find_duplicate_submission(db, submission)
    if duplicate_submission and duplicate_submission.incident_id:
        incident = db.get(Incident, duplicate_submission.incident_id)
        if incident is not None:
            return _assign_submission_to_incident(
                db,
                submission,
                incident,
                duplicate_source=duplicate_submission,
            )

    nearby_incidents = find_nearby_incidents(
        db,
        submission.grid_cell,
        time_window_minutes=settings.clustering_time_window_minutes,
        reference_time=submission.submitted_at,
    )

    if nearby_incidents:
        return _assign_submission_to_incident(db, submission, nearby_incidents[0])

    return _create_incident_for_submission(db, submission)
