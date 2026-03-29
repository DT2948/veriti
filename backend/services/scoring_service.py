from sqlalchemy import select
from sqlalchemy.orm import Session

from models.incident import Incident
from models.submission import Submission


def compute_confidence_tier(
    score: float,
    number_of_reports: int,
    official_overlap: bool = False,
) -> str:
    if official_overlap:
        return "official"
    if number_of_reports >= 3 or score >= 0.6:
        return "corroborated"
    if number_of_reports >= 2 or score >= 0.3:
        return "plausible"
    return "unverified"


def score_incident(db: Session, incident: Incident) -> tuple[str, float, str]:
    submissions = db.scalars(select(Submission).where(Submission.incident_id == incident.id)).all()
    if not submissions:
        incident.confidence_tier = "unverified"
        incident.confidence_score = 0.1
        incident.verification_notes = "No linked submissions were found."
        db.add(incident)
        db.commit()
        return incident.confidence_tier, incident.confidence_score, incident.verification_notes

    independent_groups = {submission.duplicate_group_id or submission.id for submission in submissions}
    distinct_group_count = len(independent_groups)
    report_count = len(submissions)
    device_scores = [s.device_trust_score for s in submissions if s.device_trust_score is not None]
    avg_device_score = sum(device_scores) / len(device_scores) if device_scores else 0.5
    media_bonus = 0.08 if any(s.media_type for s in submissions) else 0.0
    detail_bonus = min(0.1, sum(0.03 for s in submissions if s.text_note and len(s.text_note.split()) >= 8))
    duplicate_penalty = min(0.08, max(0, report_count - distinct_group_count) * 0.01)

    if incident.official_overlap or any(s.source_type == "official" for s in submissions):
        base_score = 0.9
        rationale = "Official source overlap detected."
    elif report_count >= 5:
        base_score = 0.65
        rationale = (
            f"{report_count} reports reference the event across "
            f"{distinct_group_count} distinct evidence group(s)."
        )
    elif report_count >= 3:
        base_score = 0.5
        rationale = (
            f"{report_count} reports reference the event, though only "
            f"{distinct_group_count} distinct evidence group(s) were detected."
        )
    elif report_count == 2:
        base_score = 0.35
        rationale = "Two reports suggest a plausible incident."
    else:
        base_score = 0.15
        rationale = "Only a single report is available so confidence remains low."

    trust_adjustment = (avg_device_score - 0.5) * 0.2
    raw_score = base_score + trust_adjustment + media_bonus + detail_bonus - duplicate_penalty
    score = max(0.1, min(1.0, round(raw_score, 3)))
    tier = compute_confidence_tier(
        score=score,
        number_of_reports=report_count,
        official_overlap=incident.official_overlap or any(s.source_type == "official" for s in submissions),
    )

    incident.confidence_score = score if tier != "official" else max(score, 0.9)
    incident.confidence_tier = tier
    incident.verification_notes = (
        f"{rationale} Avg device trust {avg_device_score:.2f}; "
        f"media bonus {media_bonus:.2f}; detail bonus {detail_bonus:.2f}; "
        f"duplicate penalty {duplicate_penalty:.2f}."
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident.confidence_tier, incident.confidence_score, incident.verification_notes
