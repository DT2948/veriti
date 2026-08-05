from datetime import datetime

from pydantic import BaseModel


class SubmissionCreate(BaseModel):
    text_note: str | None = None
    latitude: float
    longitude: float
    device_trust_score: float | None = None
    integrity_token: str | None = None


class SubmissionResponse(BaseModel):
    id: str
    correlation_id: str
    verification_status: str
    submitted_at: datetime
    message: str


class SubmissionStatus(BaseModel):
    id: str
    correlation_id: str
    verification_status: str
    incident_id: str | None = None
    submitted_at: datetime
    processed_at: datetime | None = None
    verification_duration_ms: float | None = None
    gemini_mode: str
    fallback_used: bool = False
