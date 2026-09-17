from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.deps import get_current_worker, get_current_user
from app.models.community import CommunityWorker, CommunityElder
from app.models.canteen import CanteenRecord
from app.models.user import User
from app.services.canteen import submit_canteen_record
from app.services import canteen_menu as menu_service

router = APIRouter(prefix="/community/canteen", tags=["canteen"])

MAX_EXCEL_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/submit")
async def submit_canteen(
    raw_text: str | None = Form(None),
    file: UploadFile | None = File(None),
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    excel_bytes = None
    if file and file.filename.endswith((".xlsx", ".xls")):
        excel_bytes = await file.read()
        if len(excel_bytes) > MAX_EXCEL_SIZE:
            raise HTTPException(status_code=400, detail="Excel 文件不能超过 10MB")
    elif not raw_text:
        raise HTTPException(status_code=400, detail="请输入文本或上传 Excel 文件")

    record = await submit_canteen_record(
        db,
        worker.community_id,
        worker.id,
        raw_text=raw_text,
        excel_bytes=excel_bytes,
    )
    return {
        "id": str(record.id),
        "parse_status": record.parse_status,
        "parsed_data": record.parsed_data,
    }


@router.get("/records")
async def list_records(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CanteenRecord)
        .where(CanteenRecord.community_id == worker.community_id)
        .order_by(CanteenRecord.created_at.desc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "raw_text": r.raw_text[:100],
            "source_format": r.source_format,
            "parse_status": r.parse_status,
            "parsed_data": r.parsed_data,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("/records/{record_id}")
async def get_record(
    record_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CanteenRecord).where(
        CanteenRecord.id == record_id,
        CanteenRecord.community_id == worker.community_id,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="食堂记录不存在")
    return {
        "id": str(record.id),
        "raw_text": record.raw_text,
        "source_format": record.source_format,
        "parse_status": record.parse_status,
        "parsed_data": record.parsed_data,
        "parsed_at": record.parsed_at.isoformat() if record.parsed_at else None,
        "created_at": record.created_at.isoformat(),
    }


@router.put("/records/{record_id}")
async def correct_record(
    record_id: UUID,
    parsed_data: dict = Body(...),
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CanteenRecord).where(
        CanteenRecord.id == record_id,
        CanteenRecord.community_id == worker.community_id,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="食堂记录不存在")
    record.parsed_data = parsed_data
    record.parse_status = "success"
    await db.commit()
    await db.refresh(record)
    return {"ok": True}


# ── 菜单管理 ──

class MenuDishesUpdate(BaseModel):
    dishes: dict


@router.post("/menu/generate")
async def generate_menu(
    menu_date: str = Form(None),
    meal_type: str = Form("lunch"),
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    d = date.fromisoformat(menu_date) if menu_date else date.today()
    menu = await menu_service.generate_menu(db, worker.community_id, d, meal_type)
    return _menu_response(menu)


@router.get("/menus")
async def list_menus(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    menus = await menu_service.list_menus(db, worker.community_id)
    return [_menu_response(m) for m in menus]


@router.put("/menu/{menu_id}")
async def update_menu(
    menu_id: UUID,
    body: MenuDishesUpdate,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    menu = await menu_service.update_menu_dishes(db, menu_id, worker.community_id, body.dishes)
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")
    return _menu_response(menu)


@router.post("/menu/{menu_id}/publish")
async def publish_menu(
    menu_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    menu = await menu_service.publish_menu(db, menu_id, worker.community_id, worker.id)
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")
    return _menu_response(menu)


@router.delete("/menu/{menu_id}")
async def delete_menu(
    menu_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    ok = await menu_service.delete_menu(db, menu_id, worker.community_id)
    if not ok:
        raise HTTPException(status_code=404, detail="菜单不存在")
    return {"ok": True}


@router.get("/menu/today")
async def get_today_menu(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CommunityElder.community_id).where(
            CommunityElder.elder_id == user.id
        ).limit(1)
    )
    community_id = result.scalar_one_or_none()
    if not community_id:
        return {"menus": []}

    menus = await menu_service.get_today_menu(db, community_id)
    return {"menus": [_menu_response(m) for m in menus]}


def _menu_response(m):
    return {
        "id": str(m.id),
        "menu_date": m.menu_date.isoformat(),
        "meal_type": m.meal_type,
        "dishes": m.dishes,
        "status": m.status,
        "generated_by": m.generated_by,
        "published_at": m.published_at.isoformat() if m.published_at else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
