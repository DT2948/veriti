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
    verification_status: str
    submitted_at: datetime
    message: str


class SubmissionStatus(BaseModel):
    id: str
    verification_status: str
    incident_id: str | None = None
