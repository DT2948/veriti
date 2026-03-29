import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from utils.incident_types import DEFAULT_TYPE


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_TYPE)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False, default="public")
    confidence_tier: Mapped[str] = mapped_column(String, nullable=False, default="unverified")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    grid_cell: Mapped[str] = mapped_column(String, nullable=False, index=True)
    timestamp_first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    timestamp_last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    number_of_reports: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    official_overlap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    media_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    submissions = relationship("Submission", back_populates="incident", cascade="all, delete-orphan")

    @property
    def tags_list(self) -> list[str]:
        try:
            parsed = json.loads(self.tags or "[]")
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
