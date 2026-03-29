from __future__ import annotations

import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Iterable

from google import genai
from google.genai import types
from PIL import Image

from config import get_settings
from utils.dubai_locations import get_neighborhood_name
from utils.incident_types import ALLOWED_TYPES, DEFAULT_TYPE


settings = get_settings()
_client: genai.Client | None = None
logger = logging.getLogger(__name__)


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


def _normalize_incident_type(value: str | None) -> str:
    normalized = (value or "").strip().lower().replace(" ", "_")
    return normalized if normalized in ALLOWED_TYPES else DEFAULT_TYPE


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


def _clean_json_text(text: str) -> str:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    return candidate


def _extract_json_object(text: str) -> str:
    candidate = _clean_json_text(text)
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        return candidate[start : end + 1]
    return candidate


def _fallback_analysis() -> dict:
    return {
        "media_description": "Media analysis unavailable.",
        "detected_incident_type": DEFAULT_TYPE,
        "severity_estimate": "unclear",
        "visible_landmarks": [],
        "inferred_location": "unknown",
        "plausibility": "unclear",
        "cross_validation": {
            "caption_media_match": "neutral",
            "location_media_match": "neutral",
            "caption_location_match": "neutral",
            "overall_consistency": "partial",
            "explanation": "Cross-validation could not be performed.",
        },
        "trust_modifier": 0.0,
        "inferred_data": {
            "suggested_type": DEFAULT_TYPE,
            "suggested_location": DEFAULT_TYPE,
        },
    }


def _normalize_analysis_payload(payload: dict) -> dict:
    fallback = _fallback_analysis()
    cross_validation = payload.get("cross_validation") or {}
    inferred_data = payload.get("inferred_data") or {}
    trust_modifier = payload.get("trust_modifier", 0.0)
    try:
        trust_modifier = float(trust_modifier)
    except (TypeError, ValueError):
        trust_modifier = 0.0

    return {
        "media_description": str(
            payload.get("media_description") or fallback["media_description"]
        ),
        "detected_incident_type": _normalize_incident_type(
            payload.get("detected_incident_type")
        ),
        "severity_estimate": str(
            payload.get("severity_estimate") or fallback["severity_estimate"]
        ).lower(),
        "visible_landmarks": [
            str(item) for item in (payload.get("visible_landmarks") or [])
        ],
        "inferred_location": str(
            payload.get("inferred_location") or fallback["inferred_location"]
        ),
        "plausibility": str(
            payload.get("plausibility") or fallback["plausibility"]
        ).lower(),
        "cross_validation": {
            "caption_media_match": str(
                cross_validation.get("caption_media_match")
                or fallback["cross_validation"]["caption_media_match"]
            ).lower(),
            "location_media_match": str(
                cross_validation.get("location_media_match")
                or fallback["cross_validation"]["location_media_match"]
            ).lower(),
            "caption_location_match": str(
                cross_validation.get("caption_location_match")
                or fallback["cross_validation"]["caption_location_match"]
            ).lower(),
            "overall_consistency": str(
                cross_validation.get("overall_consistency")
                or fallback["cross_validation"]["overall_consistency"]
            ).lower(),
            "explanation": str(
                cross_validation.get("explanation")
                or fallback["cross_validation"]["explanation"]
            ),
        },
        "trust_modifier": max(-0.3, min(0.3, trust_modifier)),
        "inferred_data": {
            "suggested_type": _normalize_incident_type(
                inferred_data.get("suggested_type")
            ),
            "suggested_location": str(
                inferred_data.get("suggested_location")
                or fallback["inferred_data"]["suggested_location"]
            ),
        },
    }


def _load_image_bytes(file_path: str) -> tuple[bytes, str]:
    path = Path(file_path)
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(path.suffix.lower(), "image/jpeg")

    with Image.open(path) as image:
        image = image.convert("RGB")
        max_side = max(image.size)
        if max_side > 1024:
            scale = 1024 / max_side
            resized = (
                max(1, int(image.width * scale)),
                max(1, int(image.height * scale)),
            )
            image = image.resize(resized)

        output = BytesIO()
        output_format = "PNG" if mime_type == "image/png" else "JPEG"
        save_mime_type = "image/png" if output_format == "PNG" else "image/jpeg"
        image.save(output, format=output_format, quality=88)
        return output.getvalue(), save_mime_type


def _fallback_incident_type(text_note: str) -> str:
    text = (text_note or "").lower()
    if any(keyword in text for keyword in {"blast", "explosion", "boom", "detonation"}):
        return "explosion"
    if any(keyword in text for keyword in {"missile", "rocket", "projectile"}):
        return "missile"
    if any(keyword in text for keyword in {"strike", "hit", "impacted", "impact"}):
        return "missile"
    if any(keyword in text for keyword in {"debris", "wreckage", "rubble"}):
        return "debris"
    if any(keyword in text for keyword in {"siren", "alarm", "warning siren"}):
        return "siren"
    if any(keyword in text for keyword in {"warning", "alert", "evacuate", "shelter"}):
        return "warning"
    return DEFAULT_TYPE


def _fallback_summary(incident, submissions) -> str:
    neighborhood_name = get_neighborhood_name(
        incident.grid_cell,
        incident.latitude,
        incident.longitude,
    )
    media_context = ""
    if getattr(incident, "_media_analysis_context", None):
        cross_validation = incident._media_analysis_context.get("cross_validation", {})
        media_context = (
            f" Cross-validation assessed the submission signals as "
            f"{cross_validation.get('overall_consistency', 'partial')}."
        )
    qualifier = (
        "Official reporting and public submissions both reference this incident."
        if incident.official_overlap
        else "The information remains unconfirmed and is based on incoming reports."
    )
    return (
        f"{incident.number_of_reports} independent report(s) indicate a {incident.type.replace('_', ' ')} "
        f"reported near {neighborhood_name}. {qualifier} The current confidence tier is "
        f"{incident.confidence_tier}.{media_context}"
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


def analyze_and_cross_validate(
    file_path: str,
    text_note: str = None,
    claimed_lat: float = None,
    claimed_lng: float = None,
    neighborhood_name: str = None,
) -> dict:
    client = _get_client()
    if client is None:
        return _fallback_analysis()

    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return _fallback_analysis()

    try:
        image_bytes, mime_type = _load_image_bytes(file_path)
    except Exception:
        return _fallback_analysis()

    prompt = f"""
You are a crisis verification analyst for a civilian safety platform in Dubai. You have received a submission with three signals. Analyze the image and cross-validate all signals against each other.

SIGNAL 1 - CLAIMED LOCATION: {neighborhood_name or "Not provided"} (coordinates: {claimed_lat}, {claimed_lng})

SIGNAL 2 - USER CAPTION: "{text_note or "No caption provided"}"

SIGNAL 3 - UPLOADED IMAGE: [attached]

Perform the following analysis:

1. MEDIA ANALYSIS: Describe what the image shows in 2-3 sentences. Identify the incident type, severity, and any visible Dubai landmarks or identifiable locations.
Use only the provided incident labels. If the scene suggests something was "hit", "struck", or impacted, prefer
"missile" when a projectile is implied, "explosion" for a blast/fireball, "debris" for aftermath, or "warning"
for alerts without visible impact. Do not invent a generic "attack" label.

2. CROSS-VALIDATION: Compare all three signals:
- Does the caption match what the image shows?
- Does the claimed location match what's visible in the image?
- Does the caption match the claimed location?

3. INFERENCE: If any signal is missing or weak, can the other two compensate?
- If no caption: suggest incident type from image
- If no location: suggest area from visible landmarks
- If image is unclear: rely more on caption + location

4. TRUST ASSESSMENT: Based on consistency of all three signals, provide a trust modifier:
- All three agree: +0.2 to +0.3
- Two agree, one missing: +0.1 to +0.15
- Two agree, one disagrees: -0.1 to -0.15
- Major inconsistencies: -0.2 to -0.3
- Cannot determine: 0.0

Respond in this exact JSON format:
{{
  "media_description": "...",
  "detected_incident_type": "%s",
  "severity_estimate": "high|medium|low|unclear",
  "visible_landmarks": ["..."],
  "inferred_location": "...",
  "plausibility": "genuine_photo|screenshot|recycled|unclear",
  "cross_validation": {{
    "caption_media_match": "agree|disagree|neutral",
    "location_media_match": "agree|disagree|neutral",
    "caption_location_match": "agree|disagree|neutral",
    "overall_consistency": "consistent|partial|inconsistent",
    "explanation": "..."
  }},
  "trust_modifier": 0.0,
  "inferred_data": {{
    "suggested_type": "...",
    "suggested_location": "..."
  }}
}}
""" % "|".join(sorted(ALLOWED_TYPES))
    prompt = prompt.strip()

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, image_part],
        )
        text = getattr(response, "text", "") or ""
        payload = json.loads(_extract_json_object(text))
        return _normalize_analysis_payload(payload)
    except Exception as exc:
        logger.error("Gemini vision analysis failed: %s", exc, exc_info=True)
        return _fallback_analysis()


def generate_incident_summary(incident, submissions, media_analysis: dict | None = None) -> str:
    neighborhood_name = get_neighborhood_name(
        incident.grid_cell,
        incident.latitude,
        incident.longitude,
    )
    media_context = ""
    if media_analysis:
        visible_landmarks = ", ".join(media_analysis.get("visible_landmarks", [])) or "None identified"
        media_context = f"""
Media analysis: {media_analysis.get("media_description", "N/A")}
Visible landmarks: {visible_landmarks}
Cross-validation: {media_analysis.get("cross_validation", {}).get("explanation", "N/A")}
Trust assessment: {media_analysis.get("cross_validation", {}).get("overall_consistency", "N/A")}
"""
    prompt = f"""
You are a crisis information analyst for a civilian safety platform in Dubai. Generate a brief, factual 2-3 sentence summary of this incident. Do NOT present uncertain information as fact. Use phrases like "reportedly", "according to public reports", "unconfirmed" where appropriate.

Incident type: {incident.type}
Location: {neighborhood_name}
Number of independent reports: {incident.number_of_reports}
Time range: {incident.timestamp_first_seen.isoformat()} to {incident.timestamp_last_updated.isoformat()}
Confidence tier: {incident.confidence_tier}
Report notes:
{_build_submission_notes(submissions)}
{media_context}

Write a calm, factual summary suitable for concerned residents.
""".strip()
    try:
        incident._media_analysis_context = media_analysis
        return _generate_text(prompt)
    except Exception as exc:
        logger.error("Gemini incident summary generation failed: %s", exc, exc_info=True)
        incident._media_analysis_context = media_analysis
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
    except Exception as exc:
        logger.error("Gemini confidence explanation failed: %s", exc, exc_info=True)
        return _fallback_confidence_explanation(incident)


def extract_incident_type(text_note: str, media_description: str | None = None) -> str:
    allowed_types = [
        *sorted(ALLOWED_TYPES),
    ]
    prompt = f"""
Classify the incident into exactly one of these labels: {", ".join(allowed_types)}.
Return only the label.
If the wording says a location was "hit" or "struck", prefer "missile" when a projectile or impact is implied,
"explosion" for a blast, "debris" for visible aftermath, or "warning" for alert-only language. Never return "attack".

Text note: {text_note or "none"}
Media description: {media_description or "none"}
""".strip()
    try:
        result = _generate_text(prompt).strip().lower()
        return _normalize_incident_type(result)
    except Exception as exc:
        logger.error("Gemini incident type extraction failed: %s", exc, exc_info=True)
        return _fallback_incident_type(f"{text_note or ''} {media_description or ''}".strip())
