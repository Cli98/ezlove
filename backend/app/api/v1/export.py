from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.database import get_db
from app.deps import get_current_worker
from app.models.community import CommunityWorker
from app.services import export as export_service

router = APIRouter(prefix="/community/export", tags=["export"])

EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _excel_response(data: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(data),
        media_type=EXCEL_CONTENT_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/elders")
async def export_elders(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    data = await export_service.export_elder_list(db, worker.community_id)
    return _excel_response(data, "elders.xlsx")


@router.get("/events")
async def export_events(
    start: date | None = Query(None),
    end: date | None = Query(None),
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    data = await export_service.export_events(db, worker.community_id, start_date=start, end_date=end)
    return _excel_response(data, "events.xlsx")


@router.get("/canteen")
async def export_canteen(
    start: date | None = Query(None),
    end: date | None = Query(None),
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    data = await export_service.export_canteen_records(db, worker.community_id, start_date=start, end_date=end)
    return _excel_response(data, "canteen.xlsx")


@router.get("/activity-summary")
async def export_activity(
    days: int = Query(30, ge=1, le=90),
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    data = await export_service.export_activity_summary(db, worker.community_id, days=days)
    return _excel_response(data, "activity_summary.xlsx")
