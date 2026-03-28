from typing import Iterable

import google.generativeai as genai

from config import get_settings


settings = get_settings()


def _configure_client() -> bool:
    if not settings.gemini_api_key:
        return False
    genai.configure(api_key=settings.gemini_api_key)
    return True


def _build_submission_context(submissions: Iterable) -> str:
    lines: list[str] = []
    for index, submission in enumerate(submissions, start=1):
        lines.append(
            f"{index}. source={submission.source_type}, submitted_at={submission.submitted_at.isoformat()}, "
            f"text_note={submission.text_note or 'none'}, media_type={submission.media_type or 'none'}, "
            f"device_trust_score={submission.device_trust_score}"
        )
    return "\n".join(lines) if lines else "No submissions linked."


def _generate_text(prompt: str) -> str:
    if not _configure_client():
        raise RuntimeError("Gemini API key is not configured.")
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    text = getattr(response, "text", "") or ""
    return text.strip()


def generate_incident_summary(incident, submissions) -> str:
    prompt = f"""
You are assisting a crisis signal verification platform.
Produce a factual 2-3 sentence summary. Do not present uncertain information as confirmed fact.

Incident type: {incident.type}
Number of reports: {incident.number_of_reports}
Time range: {incident.timestamp_first_seen.isoformat()} to {incident.timestamp_last_updated.isoformat()}
Location area: {incident.grid_cell} near lat={incident.latitude}, lng={incident.longitude}
Confidence tier: {incident.confidence_tier}
Submission notes:
{_build_submission_context(submissions)}
"""
    try:
        return _generate_text(prompt)
    except Exception:
        return (
            f"{incident.number_of_reports} report(s) were grouped into a {incident.type} incident in {incident.grid_cell}. "
            f"The current confidence tier is {incident.confidence_tier}, and details remain provisional pending more corroboration."
        )


def generate_confidence_explanation(incident, submissions) -> str:
    prompt = f"""
Explain in 1-2 concise sentences why this incident has its current confidence tier.

Incident type: {incident.type}
Confidence tier: {incident.confidence_tier}
Confidence score: {incident.confidence_score}
Official overlap: {incident.official_overlap}
Submission context:
{_build_submission_context(submissions)}
"""
    try:
        return _generate_text(prompt)
    except Exception:
        return incident.verification_notes or (
            f"The incident is rated {incident.confidence_tier} based on corroboration level, trust signals, and available media."
        )


def extract_incident_type(text_note: str, media_description: str | None = None) -> str:
    allowed_types = ["explosion", "debris", "siren", "missile", "warning", "unknown"]
    prompt = f"""
Classify the incident into exactly one of these labels: {", ".join(allowed_types)}.
Return only the label.

Text note: {text_note or 'none'}
Media description: {media_description or 'none'}
"""
    try:
        result = _generate_text(prompt).lower().strip()
        return result if result in allowed_types else "unknown"
    except Exception:
        text = (text_note or "").lower()
        if any(keyword in text for keyword in {"blast", "explosion", "boom"}):
            return "explosion"
        if any(keyword in text for keyword in {"siren", "alarm"}):
            return "siren"
        if any(keyword in text for keyword in {"missile", "rocket"}):
            return "missile"
        if any(keyword in text for keyword in {"debris", "wreckage"}):
            return "debris"
        if any(keyword in text for keyword in {"warning", "alert"}):
            return "warning"
        return "unknown"
