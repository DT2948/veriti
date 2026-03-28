from sqlalchemy import select
from sqlalchemy.orm import Session

from models.incident import Incident
from models.submission import Submission


def compute_confidence_tier(score: float) -> str:
    if score >= 0.9:
        return "official"
    if score >= 0.6:
        return "corroborated"
    if score >= 0.3:
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
    independent_report_count = len(independent_groups)
    device_scores = [s.device_trust_score for s in submissions if s.device_trust_score is not None]
    avg_device_score = sum(device_scores) / len(device_scores) if device_scores else 0.5
    media_bonus = 0.08 if any(s.media_type for s in submissions) else 0.0
    detail_bonus = min(0.1, sum(0.03 for s in submissions if s.text_note and len(s.text_note.split()) >= 8))

    if incident.official_overlap or any(s.source_type == "official" for s in submissions):
        base_score = 0.9
        rationale = "Official source overlap detected."
    elif independent_report_count >= 3:
        base_score = 0.6
        rationale = f"{independent_report_count} independent reports corroborate the event."
    elif independent_report_count == 2:
        base_score = 0.35
        rationale = "Two independent reports suggest a plausible incident."
    else:
        base_score = 0.15
        rationale = "Only a single report is available so confidence remains low."

    trust_adjustment = (avg_device_score - 0.5) * 0.2
    raw_score = base_score + trust_adjustment + media_bonus + detail_bonus
    score = max(0.1, min(1.0, round(raw_score, 3)))
    tier = "official" if incident.official_overlap else compute_confidence_tier(score)

    incident.confidence_score = score if tier != "official" else max(score, 0.9)
    incident.confidence_tier = tier
    incident.verification_notes = (
        f"{rationale} Avg device trust {avg_device_score:.2f}; "
        f"media bonus {media_bonus:.2f}; detail bonus {detail_bonus:.2f}."
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident.confidence_tier, incident.confidence_score, incident.verification_notes
