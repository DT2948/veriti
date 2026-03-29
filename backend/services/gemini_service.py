from __future__ import annotations

from typing import Iterable

from google import genai

from config import get_settings
from utils.dubai_locations import get_neighborhood_name


settings = get_settings()
_client: genai.Client | None = None


def _get_client() -> genai.Client | None:
    global _client
    if not settings.gemini_api_key:
        return None
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _build_submission_notes(submissions: Iterable) -> str:
    notes = [
        (submission.text_note or "").strip()
        for submission in submissions
        if (submission.text_note or "").strip()
    ]
    return "\n".join(f"- {note}" for note in notes) if notes else "- No reporter notes provided."


def _generate_text(prompt: str) -> str:
    client = _get_client()
    if client is None:
        raise RuntimeError("Gemini API key is not configured.")

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    text = getattr(response, "text", "") or ""
    if not text.strip():
        raise RuntimeError("Gemini returned an empty response.")
    return text.strip()


def _fallback_incident_type(text_note: str) -> str:
    text = (text_note or "").lower()
    if any(keyword in text for keyword in {"blast", "explosion", "boom", "detonation"}):
        return "explosion"
    if any(keyword in text for keyword in {"debris", "wreckage", "rubble"}):
        return "debris"
    if any(keyword in text for keyword in {"siren", "alarm", "warning siren"}):
        return "siren"
    if any(keyword in text for keyword in {"missile", "rocket", "projectile"}):
        return "missile"
    if any(keyword in text for keyword in {"structural", "collapsed", "collapse", "damage"}):
        return "structural_damage"
    if any(keyword in text for keyword in {"warning", "alert", "evacuate", "shelter"}):
        return "warning"
    return "unknown"


def _fallback_summary(incident, submissions) -> str:
    neighborhood_name = get_neighborhood_name(
        incident.grid_cell,
        incident.latitude,
        incident.longitude,
    )
    qualifier = (
        "Official reporting and public submissions both reference this incident."
        if incident.official_overlap
        else "The information remains unconfirmed and is based on incoming reports."
    )
    return (
        f"{incident.number_of_reports} independent report(s) indicate a {incident.type.replace('_', ' ')} "
        f"reported near {neighborhood_name}. {qualifier} The current confidence tier is "
        f"{incident.confidence_tier}."
    )


def _fallback_confidence_explanation(incident) -> str:
    if incident.official_overlap:
        return (
            "This incident is rated official because it overlaps with an official source. "
            "Confidence would decrease only if the official report is withdrawn or corrected."
        )
    if incident.number_of_reports >= 3:
        return (
            "This incident is rated corroborated because multiple independent reports from the same area "
            "arrived close together in time. Confidence would increase further with official confirmation "
            "or clearer supporting media."
        )
    if incident.number_of_reports >= 2:
        return (
            "This incident is rated plausible because at least two reports point to the same area and timeframe. "
            "Confidence would increase with more independent reports or an official alert."
        )
    return (
        "This incident is rated unverified because it currently relies on a single report or limited supporting evidence. "
        "Confidence would increase with corroborating reports, media, or official confirmation."
    )


def generate_incident_summary(incident, submissions) -> str:
    neighborhood_name = get_neighborhood_name(
        incident.grid_cell,
        incident.latitude,
        incident.longitude,
    )
    prompt = f"""
You are a crisis information analyst for a civilian safety platform in Dubai. Generate a brief, factual 2-3 sentence summary of this incident. Do NOT present uncertain information as fact. Use phrases like "reportedly", "according to public reports", "unconfirmed" where appropriate.

Incident type: {incident.type}
Location: {neighborhood_name}
Number of independent reports: {incident.number_of_reports}
Time range: {incident.timestamp_first_seen.isoformat()} to {incident.timestamp_last_updated.isoformat()}
Confidence tier: {incident.confidence_tier}
Report notes:
{_build_submission_notes(submissions)}

Write a calm, factual summary suitable for concerned residents.
""".strip()
    try:
        return _generate_text(prompt)
    except Exception:
        return _fallback_summary(incident, submissions)


def generate_confidence_explanation(incident, submissions) -> str:
    prompt = f"""
Explain in 1-2 sentences why this incident is rated as {incident.confidence_tier}.
Consider: {incident.number_of_reports} reports, {incident.media_count} media attachments,
official overlap: {"yes" if incident.official_overlap else "no"}. Be specific about what would increase
or decrease confidence.
""".strip()
    try:
        return _generate_text(prompt)
    except Exception:
        return _fallback_confidence_explanation(incident)


def extract_incident_type(text_note: str, media_description: str | None = None) -> str:
    allowed_types = [
        "explosion",
        "debris",
        "siren",
        "missile",
        "structural_damage",
        "warning",
        "unknown",
    ]
    prompt = f"""
Classify the incident into exactly one of these labels: {", ".join(allowed_types)}.
Return only the label.

Text note: {text_note or "none"}
Media description: {media_description or "none"}
""".strip()
    try:
        result = _generate_text(prompt).strip().lower()
        return result if result in allowed_types else "unknown"
    except Exception:
        return _fallback_incident_type(text_note)
