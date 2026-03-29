from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IncidentBase(BaseModel):
    type: str
    emoji: str
    title: str
    summary: str | None = None
    source_type: str
    confidence_tier: str
    confidence_score: float
    latitude: float
    longitude: float
    grid_cell: str
    timestamp_first_seen: datetime
    timestamp_last_updated: datetime
    number_of_reports: int
    official_overlap: bool
    media_count: int
    tags: list[str] = []
    verification_notes: str | None = None
    is_active: bool


class IncidentResponse(IncidentBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentListResponse(BaseModel):
    total: int
    items: list[IncidentResponse]


class IncidentMapResponse(BaseModel):
    id: str
    type: str
    emoji: str
    title: str
    confidence_tier: str
    confidence_score: float
    latitude: float
    longitude: float
    number_of_reports: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
