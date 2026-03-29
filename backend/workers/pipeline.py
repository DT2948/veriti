from datetime import datetime, timezone
import logging
from pathlib import Path

from sqlalchemy import select

from database import SessionLocal
from config import get_settings
from models.submission import Submission
from services.clustering_service import build_incident_title
from services.gemini_service import (
    analyze_and_cross_validate,
    analyze_video_and_cross_validate,
    extract_incident_type,
    generate_confidence_explanation,
    generate_incident_summary,
    is_fallback_media_analysis,
)
from services.ingestion_service import process_submission
from services.scoring_service import compute_confidence_tier
from utils.dubai_locations import (
    get_neighborhood_name,
    is_implausible_report_location,
    resolve_known_location,
)
from utils.location import coarsen_location
from utils.media import delete_raw_media


logger = logging.getLogger(__name__)
settings = get_settings()


def _location_distance(
    lat_a: float | None,
    lng_a: float | None,
    lat_b: float | None,
    lng_b: float | None,
) -> float:
    if None in {lat_a, lng_a, lat_b, lng_b}:
        return 0.0
    return ((lat_a - lat_b) ** 2 + (lng_a - lng_b) ** 2) ** 0.5


def _resolve_media_location_override(
    submission: Submission,
    media_analysis: dict | None,
) -> tuple[float, float, str] | None:
    if not media_analysis or is_fallback_media_analysis(media_analysis):
        return None

    cross_validation = media_analysis.get("cross_validation") or {}
    overall_consistency = (cross_validation.get("overall_consistency") or "").lower()
    location_media_match = (cross_validation.get("location_media_match") or "").lower()

    candidate_texts = [
        media_analysis.get("inferred_location"),
        media_analysis.get("media_description"),
        (cross_validation.get("explanation") or ""),
        submission.text_note,
        *list(media_analysis.get("visible_landmarks") or []),
    ]

    resolved_location = next(
        (
            location
            for text in candidate_texts
            if (location := resolve_known_location(text)) is not None
        ),
        None,
    )
    if resolved_location is None:
        return None

    _, resolved_lat, resolved_lng = resolved_location
    resolved_distance = _location_distance(
        submission.latitude,
        submission.longitude,
        resolved_lat,
        resolved_lng,
    )
    claimed_location_is_implausible = is_implausible_report_location(
        submission.latitude,
        submission.longitude,
    )
    gemini_detected_mismatch = (
        location_media_match == "disagree"
        or overall_consistency in {"inconsistent", "partial"}
    )
    resolved_location_is_far = (
        resolved_distance >= 0.06 and location_media_match != "agree"
    )

    if (
        not claimed_location_is_implausible
        and not gemini_detected_mismatch
        and not resolved_location_is_far
    ):
        return None

    corrected_lat, corrected_lng, corrected_grid_cell = coarsen_location(
        resolved_lat,
        resolved_lng,
        settings.grid_size_meters,
    )
    return corrected_lat, corrected_lng, corrected_grid_cell


def run_verification_pipeline(db, submission_id: str) -> None:
    own_session = db is None
    session = db or SessionLocal()
    media_path_to_delete: str | None = None
    corrected_location: tuple[float, float, str] | None = None
    try:
        submission = session.get(Submission, submission_id)
        if not submission:
            return

        media_path_to_delete = submission.media_path

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
            logger.info(
                "Submission %s media analysis source=%s detected_type=%s trust_modifier=%s",
                submission.id,
                "fallback" if is_fallback_media_analysis(media_analysis) else "gemini",
                preferred_type,
                media_analysis.get("trust_modifier", 0.0),
            )
        elif submission.media_type == "video":
            neighborhood = get_neighborhood_name(
                submission.grid_cell,
                submission.latitude,
                submission.longitude,
            )
            media_analysis = analyze_video_and_cross_validate(
                file_path=submission.media_path,
                text_note=submission.text_note,
                claimed_lat=submission.latitude,
                claimed_lng=submission.longitude,
                neighborhood_name=neighborhood,
            )
            preferred_type = media_analysis.get("detected_incident_type", "unknown")
            logger.info(
                "Submission %s video analysis source=%s detected_type=%s trust_modifier=%s",
                submission.id,
                "fallback" if is_fallback_media_analysis(media_analysis) else "gemini",
                preferred_type,
                media_analysis.get("trust_modifier", 0.0),
            )

        corrected_location = _resolve_media_location_override(submission, media_analysis)
        if corrected_location is not None:
            corrected_lat, corrected_lng, corrected_grid_cell = corrected_location
            logger.info(
                "Submission %s location corrected from (%s, %s, %s) to (%s, %s, %s) based on media-caption inference.",
                submission.id,
                submission.latitude,
                submission.longitude,
                submission.grid_cell,
                corrected_lat,
                corrected_lng,
                corrected_grid_cell,
            )
            submission.latitude = corrected_lat
            submission.longitude = corrected_lng
            submission.grid_cell = corrected_grid_cell
            session.add(submission)
            session.commit()
            session.refresh(submission)

        submission, incident = process_submission(session, submission_id)
        if incident is not None:
            if corrected_location is not None:
                corrected_lat, corrected_lng, corrected_grid_cell = corrected_location
                if incident.grid_cell != corrected_grid_cell or incident.number_of_reports == 1:
                    incident.latitude = corrected_lat
                    incident.longitude = corrected_lng
                    incident.grid_cell = corrected_grid_cell
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
            summary_source = getattr(incident, "_summary_generation_source", "unknown")
            confidence_source = getattr(incident, "_confidence_explanation_source", "unknown")
            logger.info(
                "Incident %s summary_source=%s confidence_explanation_source=%s final_type=%s final_tier=%s final_score=%.3f",
                incident.id,
                summary_source,
                confidence_source,
                incident.type,
                incident.confidence_tier,
                incident.confidence_score,
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
            media_path_to_delete = submission.media_path
            submission.verification_status = "rejected"
            submission.processed_at = datetime.now(timezone.utc)
            session.add(submission)
            session.commit()
    finally:
        if media_path_to_delete:
            try:
                if Path(media_path_to_delete).exists():
                    delete_raw_media(media_path_to_delete, settings.upload_dir)
            except Exception:
                logger.warning(
                    "Failed to delete raw media for submission %s: %s",
                    submission_id,
                    media_path_to_delete,
                    exc_info=True,
                )
        if own_session:
            session.close()
