from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import get_db
from models.incident import Incident
from schemas.incident import IncidentListResponse, IncidentMapResponse, IncidentResponse


router = APIRouter(prefix="/incidents", tags=["incidents"])


def _to_incident_response(incident: Incident) -> IncidentResponse:
    return IncidentResponse(
        id=incident.id,
        type=incident.type,
        title=incident.title,
        summary=incident.summary,
        source_type=incident.source_type,
        confidence_tier=incident.confidence_tier,
        confidence_score=incident.confidence_score,
        latitude=incident.latitude,
        longitude=incident.longitude,
        grid_cell=incident.grid_cell,
        timestamp_first_seen=incident.timestamp_first_seen,
        timestamp_last_updated=incident.timestamp_last_updated,
        number_of_reports=incident.number_of_reports,
        official_overlap=incident.official_overlap,
        media_count=incident.media_count,
        tags=incident.tags_list,
        verification_notes=incident.verification_notes,
        is_active=incident.is_active,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
    )


@router.get("/map", response_model=list[IncidentMapResponse])
def list_map_incidents(db: Session = Depends(get_db)) -> list[IncidentMapResponse]:
    incidents = db.scalars(
        select(Incident).where(Incident.is_active.is_(True)).order_by(Incident.timestamp_last_updated.desc())
    ).all()
    return [
        IncidentMapResponse(
            id=incident.id,
            type=incident.type,
            title=incident.title,
            confidence_tier=incident.confidence_tier,
            confidence_score=incident.confidence_score,
            latitude=incident.latitude,
            longitude=incident.longitude,
            number_of_reports=incident.number_of_reports,
            is_active=incident.is_active,
        )
        for incident in incidents
    ]


@router.get("", response_model=IncidentListResponse)
def list_incidents(
    confidence_tier: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> IncidentListResponse:
    try:
        stmt = select(Incident).where(Incident.is_active.is_(True))
        count_stmt = select(func.count()).select_from(Incident).where(Incident.is_active.is_(True))
        if confidence_tier:
            stmt = stmt.where(Incident.confidence_tier == confidence_tier)
            count_stmt = count_stmt.where(Incident.confidence_tier == confidence_tier)

        incidents = db.scalars(
            stmt.order_by(Incident.timestamp_last_updated.desc()).offset(offset).limit(limit)
        ).all()
        total = db.scalar(count_stmt) or 0
        return IncidentListResponse(total=total, items=[_to_incident_response(item) for item in incidents])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch incidents: {exc}",
        ) from exc


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: str, db: Session = Depends(get_db)) -> IncidentResponse:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return _to_incident_response(incident)
