from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.deps import get_current_worker, get_pagination
from app.models.alert import Alert
from app.models.care_moment import CareMoment
from app.models.community import CommunityWorker, CommunityElder
from app.models.risk_snapshot import RiskScoreSnapshot
from app.models.user import User
from app.models.view_event import ViewEvent
from app.schemas.alert import AlertResponse, AlertRespondRequest
from app.schemas.community import ElderCreate, ElderUpdate, ElderResponse
from app.schemas.pagination import PaginatedResponse
from app.services import community as community_service
from app.services.community_elder_detail import get_elder_full_detail
from app.services import risk_scoring
from app.services import timeline as timeline_service

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/elders")
async def list_elders(
    care_level: str | None = None,
    search: str | None = None,
    pagination: dict = Depends(get_pagination),
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    total = await community_service.count_elders(
        db, worker.community_id, care_level=care_level, search=search
    )
    elders = await community_service.list_elders(
        db, worker.community_id, care_level=care_level, search=search,
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
        db, worker.community_id, data.model_dump(exclude_unset=True)
    )
    return await community_service.get_elder_detail(db, elder.id, worker.community_id)


@router.put("/elders/{elder_id}", response_model=ElderResponse)
async def update_elder(
    elder_id: UUID,
    data: ElderUpdate,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    try:
        elder = await community_service.update_elder_record(
            db, worker.community_id, elder_id, data.model_dump(exclude_unset=True)
        )
        return await community_service.get_elder_detail(db, elder.id, worker.community_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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


async def _get_own_record(
    db: AsyncSession, elder_id: UUID, worker: CommunityWorker
) -> CommunityElder:
    record = (await db.execute(
        select(CommunityElder).where(
            CommunityElder.id == elder_id,
            CommunityElder.community_id == worker.community_id,
        )
    )).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="老人档案不存在")
    return record


def _is_real_wechat(user: User | None) -> bool:
    """导入档案的虚拟账号（import_）与工作人员账号（worker_）不算真实微信。"""
    openid = (user.openid if user else "") or ""
    return bool(user and not openid.startswith(("import_", "worker_")))


def _mask_phone(phone: str | None) -> str | None:
    """手机号只展示首尾，足够现场核对又不把完整号码铺在页面上。"""
    if not phone or len(phone) < 7:
        return None
    return f"{phone[:3]}****{phone[-4:]}"


def _moment_excerpt(moment: CareMoment) -> str:
    """牵挂内容摘要：候选微信没有昵称/手机号时，靠“看过哪条”让工作人员与老人核对。"""
    text = (moment.text_content or "").strip().replace("\n", " ")
    if text:
        return text if len(text) <= 40 else f"{text[:40]}…"
    return {
        "image": "一张照片",
        "video": "一段视频",
        "poster": "一张海报",
        "voice": "一段语音",
    }.get(moment.content_type or "", "一条牵挂")


@router.get("/elders/{elder_id}/wechat-binding")
async def get_wechat_binding(
    elder_id: UUID,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    """档案的微信绑定状态 + 最近登录的候选微信用户（供工作人员一键绑定）。"""
    record = await _get_own_record(db, elder_id, worker)
    current = await db.get(User, record.elder_id) if record.elder_id else None

    rows = (await db.execute(
        select(User)
        .where(
            ~User.openid.startswith("import_"),
            ~User.openid.startswith("worker_"),
            or_(User.role.is_(None), User.role == "elder"),
        )
        .order_by(User.created_at.desc())
        .limit(20)
    )).scalars().all()

    taken: set = set()
    if rows:
        taken = set((await db.execute(
            select(CommunityElder.elder_id).where(
                CommunityElder.elder_id.in_([u.id for u in rows])
            )
        )).scalars().all())

    # 候选账号只有 openid 与默认昵称，无法区分是谁；用“最近查看牵挂”做可辨识信号：
    # 工作人员让老人当场打开一次小程序，刚查看过的那条会显示“刚刚”。
    last_viewed: dict = {}
    view_counts: dict = {}
    last_moment: dict = {}
    ids = [u.id for u in rows]
    if ids:
        stats = (await db.execute(
            select(ViewEvent.viewer_id, func.max(ViewEvent.viewed_at), func.count(ViewEvent.id))
            .where(ViewEvent.viewer_id.in_(ids))
            .group_by(ViewEvent.viewer_id)
        )).all()
        last_viewed = {row[0]: row[1] for row in stats}
        view_counts = {row[0]: row[2] for row in stats}

        # 候选账号大多是匿名微信（无昵称/头像/手机号），补上“最近看过哪条牵挂”作辨认依据。
        # 按时间倒序取最近若干条后逐个账号取首条，避免依赖 PG 专有的 DISTINCT ON。
        recent_views = (await db.execute(
            select(ViewEvent.viewer_id, ViewEvent.moment_id)
            .where(ViewEvent.viewer_id.in_(ids), ViewEvent.moment_id.isnot(None))
            .order_by(ViewEvent.viewed_at.desc())
            .limit(500)
        )).all()
        seen_moment: dict = {}
        for viewer_id, moment_id in recent_views:
            if viewer_id not in seen_moment:
                seen_moment[viewer_id] = moment_id
        moment_ids = [mid for mid in seen_moment.values() if mid]
        moments = {}
        if moment_ids:
            moments = {m.id: m for m in (await db.execute(
                select(CareMoment).where(CareMoment.id.in_(moment_ids))
            )).scalars().all()}
        last_moment = {
            viewer_id: _moment_excerpt(moments[mid])
            for viewer_id, mid in seen_moment.items()
            if mid in moments
        }

    candidates = [
        {
            "id": str(u.id),
            "nickname": u.nickname,
            "avatar_url": u.avatar_url,
            "phone_masked": _mask_phone(u.phone),
            "openid_masked": f"{u.openid[:6]}****{u.openid[-4:]}",
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_viewed_at": the_view.isoformat() if the_view else None,
            "last_view_text": last_moment.get(u.id),
            "view_count": view_counts.get(u.id, 0),
        }
        for u in rows
        if u.id not in taken and u.id != record.elder_id
        for the_view in (last_viewed.get(u.id),)
    ]
    # 最近查看过的排前面；从未查看的按注册时间倒序（rows 已是 desc）
    candidates.sort(key=lambda item: item["last_viewed_at"] or "", reverse=True)

    return {
        "bound": _is_real_wechat(current),
        "elder_name": current.nickname if current else None,
        "bound_avatar": current.avatar_url if _is_real_wechat(current) else None,
        "bound_phone_masked": _mask_phone(current.phone) if _is_real_wechat(current) else None,
        "candidates": candidates,
    }


class WechatBindPayload(BaseModel):
    user_id: UUID


@router.post("/elders/{elder_id}/wechat-binding")
async def bind_wechat(
    elder_id: UUID,
    data: WechatBindPayload,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    """把档案关联到真实微信用户：老人在小程序登录过即可，无需老人自行操作。"""
    record = await _get_own_record(db, elder_id, worker)
    current = await db.get(User, record.elder_id) if record.elder_id else None
    if _is_real_wechat(current):
        raise HTTPException(status_code=409, detail="该档案已绑定微信账号")

    target = await db.get(User, data.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="微信用户不存在")
    if not _is_real_wechat(target):
        raise HTTPException(status_code=400, detail="该账号不是老人微信账号")

    other = (await db.execute(
        select(CommunityElder.id).where(CommunityElder.elder_id == target.id).limit(1)
    )).scalar_one_or_none()
    if other is not None and other != record.id:
        raise HTTPException(status_code=409, detail="该微信已绑定其他老人档案")

    record.elder_id = target.id
    if not target.role:
        target.role = "elder"
    await db.commit()
    return {
        "ok": True,
        "record_id": str(record.id),
        "nickname": target.nickname,
    }


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
        raise HTTPException(status_code=404, detail="提醒不存在")

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


@router.get("/elders/{elder_id}/risk/history")
async def get_elder_risk_history(
    elder_id: UUID,
    days: int = 30,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    """风险分数每日快照（安全曲线数据源；快照由每小时重算任务 upsert）。"""
    days = max(1, min(days, 180))
    result = await db.execute(
        select(CommunityElder).where(
            CommunityElder.id == elder_id,
            CommunityElder.community_id == worker.community_id,
        )
    )
    elder = result.scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人档案不存在")

    since = (datetime.now() - timedelta(days=days - 1)).date()
    rows = (
        await db.execute(
            select(
                RiskScoreSnapshot.snapshot_date,
                RiskScoreSnapshot.score,
                RiskScoreSnapshot.level,
            )
            .where(
                RiskScoreSnapshot.elder_id == elder.id,
                RiskScoreSnapshot.snapshot_date >= since,
            )
            .order_by(RiskScoreSnapshot.snapshot_date.asc())
        )
    ).all()
    return {
        "elder_id": str(elder.id),
        "days": days,
        "items": [
            {"date": snapshot_date.isoformat(), "score": score, "level": level}
            for snapshot_date, score, level in rows
        ],
    }


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
