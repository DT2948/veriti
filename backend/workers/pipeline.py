from datetime import datetime, timezone

from sqlalchemy import select

from database import SessionLocal
from models.submission import Submission
from services.clustering_service import build_incident_title
from services.gemini_service import (
    analyze_and_cross_validate,
    extract_incident_type,
    generate_confidence_explanation,
    generate_incident_summary,
)
from services.ingestion_service import process_submission
from services.scoring_service import compute_confidence_tier
from utils.dubai_locations import get_neighborhood_name


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

        media_analysis = None
        preferred_type = "unknown"
        if submission.media_path and submission.media_type == "image":
            neighborhood = get_neighborhood_name(
                submission.grid_cell,
                submission.latitude,
                submission.longitude,
            )
            media_analysis = analyze_and_cross_validate(
                file_path=submission.media_path,
                text_note=submission.text_note,
                claimed_lat=submission.latitude,
                claimed_lng=submission.longitude,
                neighborhood_name=neighborhood,
            )
            preferred_type = media_analysis.get("detected_incident_type", "unknown")
        elif submission.media_type == "video":
            # TODO: Add Gemini video analysis support once the MVP pipeline handles video frames.
            media_analysis = None

        submission, incident = process_submission(session, submission_id)
        if incident is not None:
            linked_submissions = session.scalars(
                select(Submission).where(Submission.incident_id == incident.id)
            ).all()
            if preferred_type != "unknown":
                incident.type = preferred_type
                incident.tags = f'["{preferred_type}"]'
            elif incident.type == "unknown":
                candidate_text = " ".join(
                    filter(None, [linked_submission.text_note for linked_submission in linked_submissions])
                )
                media_description = None
                if media_analysis:
                    media_description = media_analysis.get("media_description")
                extracted_type = extract_incident_type(candidate_text, media_description)
                if extracted_type != "unknown":
                    incident.type = extracted_type
                    incident.tags = f'["{extracted_type}"]'

            if media_analysis:
                trust_modifier = float(media_analysis.get("trust_modifier", 0.0) or 0.0)
                if trust_modifier != 0.0:
                    incident.confidence_score = max(
                        0.0,
                        min(1.0, incident.confidence_score + trust_modifier),
                    )
                    incident.confidence_tier = compute_confidence_tier(
                        incident.confidence_score,
                        incident.number_of_reports,
                        incident.official_overlap,
                    )

            incident.title = build_incident_title(
                incident.type,
                incident.grid_cell,
                incident.latitude,
                incident.longitude,
            )
            incident.summary = generate_incident_summary(
                incident,
                linked_submissions,
                media_analysis=media_analysis,
            )
            incident.verification_notes = generate_confidence_explanation(
                incident,
                linked_submissions,
            )
            if media_analysis:
                cross_validation = media_analysis.get("cross_validation", {})
                consistency = cross_validation.get("overall_consistency", "unknown")
                explanation = cross_validation.get("explanation", "")
                incident.verification_notes = (
                    f"{incident.verification_notes} Signal cross-validation: "
                    f"{consistency}. {explanation}".strip()
                )
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
