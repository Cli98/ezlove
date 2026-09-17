from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_worker, get_pagination
from app.models.community import CommunityWorker
from app.services import community_event as event_service
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/community/events", tags=["community-events"])


class EventCreate(BaseModel):
    elder_id: UUID
    event_type: str
    description: str | None = None
    severity: str = "info"


class EventResolveRequest(BaseModel):
    resolution_note: str | None = None


@router.get("")
async def list_events(
    severity: str | None = None,
    event_type: str | None = None,
    is_resolved: bool | None = None,
    pagination: dict = Depends(get_pagination),
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    total = await event_service.count_events(
        db, worker.community_id,
        severity=severity, event_type=event_type, is_resolved=is_resolved,
    )
    events = await event_service.list_events(
        db, worker.community_id,
        severity=severity, event_type=event_type, is_resolved=is_resolved,
        offset=pagination["offset"], limit=pagination["limit"],
    )
    items = [
        {
            "id": str(e.id),
            "elder_id": str(e.elder_id),
            "event_type": e.event_type,
            "source": e.source,
            "description": e.description,
            "severity": e.severity,
            "is_resolved": e.is_resolved,
            "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
            "resolution_note": e.resolution_note,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
    return PaginatedResponse.create(
        items=items, total=total,
        page=pagination["page"], page_size=pagination["page_size"],
    )


@router.post("")
async def create_event(
    data: EventCreate,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    event = await event_service.create_event(
        db, worker.community_id,
        {**data.model_dump(), "source": "manual"},
    )
    return {"id": str(event.id)}


@router.put("/{event_id}/resolve")
async def resolve_event(
    event_id: UUID,
    body: EventResolveRequest | None = None,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    try:
        note = body.resolution_note if body else None
        event = await event_service.resolve_event(db, event_id, worker.id, worker.community_id, resolution_note=note)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sync-alerts")
async def sync_alerts(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    """Sync unresolved family-side alerts to community events."""
    result = await event_service.sync_family_alerts_to_community(
        db, worker.community_id,
    )
    return result
