import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str | None] = mapped_column(String, ForeignKey("incidents.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False, default="public")
    media_type: Mapped[str | None] = mapped_column(String, nullable=True)
    media_path: Mapped[str | None] = mapped_column(String, nullable=True)
    text_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    grid_cell: Mapped[str] = mapped_column(String, nullable=False, index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    device_trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    integrity_token: Mapped[str | None] = mapped_column(String, nullable=True)
    duplicate_group_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    perceptual_hash: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    embedding_vector: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String, nullable=False, default="pending", index=True)
    anonymous_token: Mapped[str | None] = mapped_column(String, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    incident = relationship("Incident", back_populates="submissions")

    @property
    def embedding(self) -> list[float]:
        try:
            parsed = json.loads(self.embedding_vector or "[]")
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
