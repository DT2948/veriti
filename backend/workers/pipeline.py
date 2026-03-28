from datetime import datetime, timezone

from sqlalchemy import select

from database import SessionLocal
from models.submission import Submission
from services.gemini_service import (
    generate_confidence_explanation,
    generate_incident_summary,
)
from services.ingestion_service import process_submission


def run_verification_pipeline(db, submission_id: str) -> None:
    own_session = db is None
    session = db or SessionLocal()
    try:
        submission = session.get(Submission, submission_id)
        if not submission:
            return

        submission.verification_status = "processing"
        session.add(submission)
        session.commit()
        session.refresh(submission)

        submission, incident = process_submission(session, submission_id)
        if incident is not None:
            linked_submissions = session.scalars(
                select(Submission).where(Submission.incident_id == incident.id)
            ).all()
            incident.summary = generate_incident_summary(incident, linked_submissions)
            incident.verification_notes = generate_confidence_explanation(incident, linked_submissions)
            incident.timestamp_last_updated = datetime.now(timezone.utc)
            session.add(incident)

        submission.processed_at = datetime.now(timezone.utc)
        submission.verification_status = "verified" if incident else "rejected"
        session.add(submission)
        session.commit()
    except Exception:
        submission = session.get(Submission, submission_id)
        if submission:
            submission.verification_status = "rejected"
            submission.processed_at = datetime.now(timezone.utc)
            session.add(submission)
            session.commit()
    finally:
        if own_session:
            session.close()
