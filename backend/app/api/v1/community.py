from datetime import datetime

import uuid
from asyncio import get_event_loop
from functools import partial

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.deps import get_current_worker, get_pagination
from app.models.alert import Alert
from app.models.community import CommunityWorker, CommunityElder
from app.schemas.alert import AlertResponse, AlertRespondRequest
from app.schemas.community import ElderCreate, ElderUpdate, ElderResponse
from app.schemas.pagination import PaginatedResponse
from app.services import community as community_service
from app.services.community_elder_detail import get_elder_full_detail
from app.services import risk_scoring
from app.services import timeline as timeline_service
from app.api.v1.upload import IMAGE_TYPES, MAX_IMAGE_SIZE, CHUNK_SIZE, UPLOAD_DIR, _detect_type, _write_file

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/elders")
async def list_elders(
    care_level: str | None = None,
    search: str | None = None,
    area: str | None = None,
    follow_up_only: bool = False,
    pagination: dict = Depends(get_pagination),
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    total = await community_service.count_elders(
        db, worker.community_id, care_level=care_level, search=search,
        area=area, follow_up_only=follow_up_only,
    )
    elders = await community_service.list_elders(
        db, worker.community_id, care_level=care_level, search=search,
        area=area, follow_up_only=follow_up_only,
        offset=pagination["offset"], limit=pagination["limit"],
    )
    return PaginatedResponse.create(
        items=elders, total=total,
        page=pagination["page"], page_size=pagination["page_size"],
    )


@router.post("/elders", response_model=ElderResponse)
async def create_elder(
    data: ElderCreate,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    elder = await community_service.create_elder_record(
        db, worker.community_id, data.model_dump()
    )
    return elder


@router.put("/elders/{elder_id}", response_model=ElderResponse)
async def update_elder(
    elder_id: UUID,
    data: ElderUpdate,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    try:
        elder = await community_service.update_elder_record(
            db, elder_id, worker.community_id, data.model_dump(exclude_unset=True)
        )
        return elder
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/elders/{elder_id}/avatar")
async def upload_elder_avatar(
    elder_id: UUID,
    file: UploadFile = File(...),
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 jpg/png/gif/webp 图片")
    chunks: list[bytes] = []
    total_size = 0
    while chunk := await file.read(CHUNK_SIZE):
        total_size += len(chunk)
        if total_size > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="头像不能超过 5MB")
        chunks.append(chunk)
    content = b"".join(chunks)
    detected = _detect_type(content) if len(content) >= 12 else None
    if not detected or detected[1] != "image":
        raise HTTPException(status_code=400, detail="图片内容无效")
    filename = f"{uuid.uuid4().hex}.{detected[0]}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    await get_event_loop().run_in_executor(None, partial(_write_file, UPLOAD_DIR / filename, content))
    url = f"/static/uploads/{filename}"
    try:
        await community_service.update_elder_record(db, elder_id, worker.community_id, {"avatar_url": url})
    except ValueError as e:
        (UPLOAD_DIR / filename).unlink(missing_ok=True)
        raise HTTPException(status_code=404, detail=str(e))
    return {"url": url}


@router.get("/elders/{elder_id}")
async def get_elder(
    elder_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    detail = await community_service.get_elder_detail(db, elder_id, worker.community_id)
    if not detail:
        raise HTTPException(status_code=404, detail="老人档案不存在")
    return detail


@router.get("/elders/{elder_id}/full")
async def get_elder_full(
    elder_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    detail = await get_elder_full_detail(db, elder_id, worker.community_id)
    if not detail:
        raise HTTPException(status_code=404, detail="老人档案不存在")
    return detail


@router.get("/alerts/pending", response_model=list[AlertResponse])
async def pending_alerts(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert)
        .where(
            Alert.community_id == worker.community_id,
            Alert.is_resolved == False,
        )
        .order_by(Alert.created_at.desc())
    )
    return result.scalars().all()


@router.post("/alerts/{alert_id}/respond", response_model=AlertResponse)
async def respond_alert(
    alert_id: UUID,
    data: AlertRespondRequest,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.community_id == worker.community_id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    alert.responded_at = datetime.now()
    alert.response_note = data.response_note
    alert.is_resolved = True
    alert.resolved_at = datetime.now()
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("/elders/{elder_id}/risk")
async def get_elder_risk(
    elder_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CommunityElder).where(
            CommunityElder.id == elder_id,
            CommunityElder.community_id == worker.community_id,
        )
    )
    elder = result.scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人档案不存在")
    return {
        "risk_score": elder.risk_score,
        "risk_level": elder.risk_level,
        "risk_calculated_at": elder.risk_calculated_at.isoformat() if elder.risk_calculated_at else None,
        "risk_details": elder.risk_details,
    }


@router.post("/elders/{elder_id}/risk/recalculate")
async def recalculate_elder_risk(
    elder_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CommunityElder).where(
            CommunityElder.id == elder_id,
            CommunityElder.community_id == worker.community_id,
        )
    )
    elder = result.scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人档案不存在")

    score_data = await risk_scoring.calculate_risk_score(db, elder)
    await db.commit()
    return score_data


@router.get("/elders/{elder_id}/risk/ai-analysis")
async def get_elder_ai_analysis(
    elder_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CommunityElder).where(
            CommunityElder.id == elder_id,
            CommunityElder.community_id == worker.community_id,
        )
    )
    elder = result.scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人档案不存在")

    return await risk_scoring.get_ai_analysis(db, elder)


@router.get("/risk-ranking")
async def risk_ranking(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User
    result = await db.execute(
        select(CommunityElder, User.nickname)
        .join(User, CommunityElder.elder_id == User.id)
        .where(
            CommunityElder.community_id == worker.community_id,
            CommunityElder.risk_score.isnot(None),
        )
        .order_by(CommunityElder.risk_score.desc())
    )
    rows = result.all()
    return [
        {
            "elder_id": str(elder.id),
            "name": name,
            "care_level": elder.care_level,
            "risk_score": elder.risk_score,
            "risk_level": elder.risk_level,
        }
        for elder, name in rows
    ]


@router.get("/elders/{elder_id}/timeline")
async def get_elder_timeline(
    elder_id: UUID,
    days: int = 30,
    limit: int = 50,
    offset: int = 0,
    types: str | None = None,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CommunityElder).where(
            CommunityElder.id == elder_id,
            CommunityElder.community_id == worker.community_id,
        )
    )
    elder = result.scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人档案不存在")

    event_types = types.split(",") if types else None
    return await timeline_service.get_elder_timeline(
        db, elder.elder_id, worker.community_id,
        days=days, limit=limit, offset=offset, event_types=event_types,
    )


@router.get("/elders/{elder_id}/day-activity")
async def get_elder_day_activity(
    elder_id: UUID,
    date: str = None,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CommunityElder).where(
            CommunityElder.id == elder_id,
            CommunityElder.community_id == worker.community_id,
        )
    )
    elder = result.scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人档案不存在")

    from datetime import date as date_type
    target = date or str(date_type.today())
    return await timeline_service.get_day_activity(
        db, elder.elder_id, worker.community_id, target,
    )


@router.get("/elders/{elder_id}/activity-summary")
async def get_elder_activity_summary(
    elder_id: UUID,
    days: int = 30,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CommunityElder).where(
            CommunityElder.id == elder_id,
            CommunityElder.community_id == worker.community_id,
        )
    )
    elder = result.scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人档案不存在")

    return await timeline_service.get_activity_summary(
        db, elder.elder_id, worker.community_id, days=days,
    )


@router.get("/dashboard")
async def dashboard(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    from app.services import community_event as event_service
    data = await event_service.get_dashboard_data(db, worker.community_id)
    return data


@router.get("/dashboard/building")
async def building_elders(
    building: str,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    from app.services.community_event import get_building_elders
    return await get_building_elders(db, worker.community_id, building)


@router.post("/elders/{elder_id}/confirm-active")
async def confirm_elder_active(
    elder_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    from app.models.community_event import CommunityEvent as CE
    result = await db.execute(
        select(CommunityElder).where(
            CommunityElder.id == elder_id,
            CommunityElder.community_id == worker.community_id,
        )
    )
    elder = result.scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人档案不存在")

    from app.models.user import User
    name_result = await db.execute(select(User.nickname).where(User.id == elder.elder_id))
    name = name_result.scalar_one_or_none() or "未知"

    event = CE(
        community_id=worker.community_id,
        elder_id=elder.elder_id,
        event_type="manual_confirm",
        source="manual",
        description=f"工作人员确认{name}今日活跃状态",
        severity="info",
        is_resolved=True,
        resolved_by=worker.id,
        resolved_at=datetime.now(),
    )
    db.add(event)
    await db.commit()
    return {"ok": True, "message": f"已确认{name}活跃"}
