import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.view_event import ViewEvent
from app.models.care_moment import CareMoment
from app.models.canteen import CanteenRecord
from app.models.alert import Alert
from app.models.care_relation import CareRelation
from app.models.community_event import CommunityEvent
from app.models.user import User


async def get_elder_timeline(
    db: AsyncSession,
    elder_user_id: uuid.UUID,
    community_id: uuid.UUID,
    days: int = 30,
    limit: int = 50,
    offset: int = 0,
    event_types: list[str] | None = None,
) -> dict:
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    items = []

    allowed = set(event_types) if event_types else None

    # 来源1: view_events
    if not allowed or "view" in allowed:
        views = (await db.execute(
            select(ViewEvent).where(
                ViewEvent.viewer_id == elder_user_id,
                ViewEvent.viewed_at >= cutoff,
            ).order_by(desc(ViewEvent.viewed_at))
        )).scalars().all()

        for v in views:
            items.append({
                "id": str(v.id),
                "type": "view",
                "time": v.viewed_at.isoformat(),
                "label": "查看牵挂",
                "description": f"查看了牵挂内容（时长 {v.view_duration or 0}s）",
                "severity": "info",
                "source_id": str(v.moment_id) if v.moment_id else None,
            })

    # 来源2: care_moments 发给该老人的
    if not allowed or "moment" in allowed:
        moments = (await db.execute(
            select(CareMoment, User.nickname)
            .join(User, CareMoment.sender_id == User.id)
            .where(
                CareMoment.elder_id == elder_user_id,
                CareMoment.created_at >= cutoff,
            ).order_by(desc(CareMoment.created_at))
        )).all()

        for m, sender_name in moments:
            items.append({
                "id": str(m.id),
                "type": "moment",
                "time": m.created_at.isoformat(),
                "label": "收到牵挂",
                "description": f"{sender_name} 发来了牵挂：{(m.text_content or '')[:30]}",
                "severity": "info",
                "source_id": str(m.sender_id),
            })

    # 来源3: canteen_records
    if not allowed or "canteen" in allowed:
        records = (await db.execute(
            select(CanteenRecord).where(
                CanteenRecord.community_id == community_id,
                CanteenRecord.parse_status == "success",
                CanteenRecord.created_at >= cutoff,
            ).order_by(desc(CanteenRecord.created_at))
        )).scalars().all()

        elder_id_str = str(elder_user_id)
        for rec in records:
            for att in (rec.parsed_data or {}).get("attendees", []):
                if att.get("elder_id") == elder_id_str:
                    present = att.get("present")
                    meal = (rec.parsed_data or {}).get("meal_type", "")
                    if present is True:
                        items.append({
                            "id": f"canteen-{rec.id}-{elder_id_str}",
                            "type": "canteen_present",
                            "time": rec.created_at.isoformat(),
                            "label": "食堂就餐",
                            "description": f"{meal}正常就餐",
                            "severity": "info",
                            "source_id": str(rec.id),
                        })
                    elif present is False:
                        items.append({
                            "id": f"canteen-{rec.id}-{elder_id_str}",
                            "type": "canteen_absent",
                            "time": rec.created_at.isoformat(),
                            "label": "食堂缺勤",
                            "description": f"{meal}未到食堂就餐",
                            "severity": "warning",
                            "source_id": str(rec.id),
                        })

    # 来源4: alerts
    if not allowed or "alert" in allowed:
        # 社区侧告警
        community_alerts = (await db.execute(
            select(Alert).where(
                Alert.elder_id == elder_user_id,
                Alert.created_at >= cutoff,
            ).order_by(desc(Alert.created_at))
        )).scalars().all()

        for a in community_alerts:
            items.append({
                "id": str(a.id),
                "type": "alert",
                "time": a.created_at.isoformat(),
                "label": "告警" if not a.is_resolved else "告警(已处理)",
                "description": a.message,
                "severity": a.alert_level,
                "source_id": str(a.id),
            })

        # 家属侧告警
        rel_ids = (await db.execute(
            select(CareRelation.id).where(CareRelation.elder_user_id == elder_user_id)
        )).scalars().all()
        if rel_ids:
            family_alerts = (await db.execute(
                select(Alert).where(
                    Alert.care_relation_id.in_(rel_ids),
                    Alert.elder_id.is_(None),
                    Alert.created_at >= cutoff,
                ).order_by(desc(Alert.created_at))
            )).scalars().all()
            for a in family_alerts:
                items.append({
                    "id": str(a.id),
                    "type": "alert",
                    "time": a.created_at.isoformat(),
                    "label": "家属告警" if not a.is_resolved else "家属告警(已处理)",
                    "description": a.message,
                    "severity": a.alert_level,
                    "source_id": str(a.id),
                })

    # 来源5: community_events
    if not allowed or "event" in allowed:
        events = (await db.execute(
            select(CommunityEvent).where(
                CommunityEvent.elder_id == elder_user_id,
                CommunityEvent.community_id == community_id,
                CommunityEvent.created_at >= cutoff,
            ).order_by(desc(CommunityEvent.created_at))
        )).scalars().all()

        type_labels = {
            "fall": "跌倒", "absent": "缺勤", "emergency": "紧急",
            "visit": "走访", "other": "其他",
        }
        for e in events:
            items.append({
                "id": str(e.id),
                "type": "event",
                "time": e.created_at.isoformat(),
                "label": type_labels.get(e.event_type, e.event_type),
                "description": e.description,
                "severity": e.severity,
                "source_id": str(e.id),
            })

    # 按时间降序排列
    items.sort(key=lambda x: x["time"], reverse=True)
    total = len(items)
    paged = items[offset:offset + limit]

    return {
        "items": paged,
        "total": total,
        "has_more": offset + limit < total,
    }


async def get_activity_summary(
    db: AsyncSession,
    elder_user_id: uuid.UUID,
    community_id: uuid.UUID,
    days: int = 30,
) -> dict:
    now = datetime.now()
    cutoff = now - timedelta(days=days)

    # 活跃天数
    active_dates_result = await db.execute(
        select(func.date(ViewEvent.viewed_at))
        .where(ViewEvent.viewer_id == elder_user_id, ViewEvent.viewed_at >= cutoff)
        .group_by(func.date(ViewEvent.viewed_at))
    )
    active_dates = {r[0] for r in active_dates_result.all()}

    # 总查看次数
    total_views = (await db.execute(
        select(func.count(ViewEvent.id)).where(
            ViewEvent.viewer_id == elder_user_id,
            ViewEvent.viewed_at >= cutoff,
        )
    )).scalar() or 0

    # 食堂出勤率
    records = (await db.execute(
        select(CanteenRecord).where(
            CanteenRecord.community_id == community_id,
            CanteenRecord.parse_status == "success",
            CanteenRecord.created_at >= cutoff,
        )
    )).scalars().all()

    elder_id_str = str(elder_user_id)
    total_meals = 0
    present_meals = 0
    for rec in records:
        for att in (rec.parsed_data or {}).get("attendees", []):
            if att.get("elder_id") == elder_id_str:
                total_meals += 1
                if att.get("present") is True:
                    present_meals += 1

    canteen_rate = round(present_meals / total_meals * 100, 1) if total_meals > 0 else None

    # 每日活跃度
    daily = []
    for i in range(days):
        d = (cutoff + timedelta(days=i + 1)).date()
        daily.append({
            "date": str(d),
            "active": d in active_dates,
        })

    # 每日食堂出勤
    daily_canteen = []
    for rec in records:
        rec_date = rec.created_at.date() if rec.created_at else None
        if not rec_date:
            continue
        for att in (rec.parsed_data or {}).get("attendees", []):
            if att.get("elder_id") == elder_id_str:
                daily_canteen.append({
                    "date": str(rec_date),
                    "present": att.get("present", False),
                })

    # 风险分数走势
    from app.models.risk_snapshot import RiskScoreSnapshot
    from app.models.community import CommunityElder as CE
    elder_rec = (await db.execute(
        select(CE.id).where(
            CE.elder_id == elder_user_id,
            CE.community_id == community_id,
        )
    )).scalar_one_or_none()

    risk_history = []
    if elder_rec:
        snap_result = await db.execute(
            select(RiskScoreSnapshot).where(
                RiskScoreSnapshot.elder_id == elder_rec,
                RiskScoreSnapshot.snapshot_date >= cutoff.date(),
            ).order_by(RiskScoreSnapshot.snapshot_date)
        )
        for s in snap_result.scalars().all():
            risk_history.append({
                "date": str(s.snapshot_date),
                "score": s.score,
                "level": s.level,
            })

    return {
        "active_days": len(active_dates),
        "total_days": days,
        "total_views": total_views,
        "canteen_rate": canteen_rate,
        "daily_activity": daily,
        "daily_canteen": daily_canteen,
        "risk_history": risk_history,
    }


async def get_day_activity(
    db: AsyncSession,
    elder_user_id: uuid.UUID,
    community_id: uuid.UUID,
    target_date: str,
) -> dict:
    from datetime import date as date_type
    d = date_type.fromisoformat(target_date)
    day_start = datetime(d.year, d.month, d.day)
    day_end = day_start + timedelta(days=1)

    signals = []

    # ViewEvent
    views = (await db.execute(
        select(ViewEvent).where(
            ViewEvent.viewer_id == elder_user_id,
            ViewEvent.viewed_at >= day_start,
            ViewEvent.viewed_at < day_end,
        ).order_by(ViewEvent.viewed_at)
    )).scalars().all()
    for v in views:
        signals.append({
            "hour": v.viewed_at.hour,
            "minute": v.viewed_at.minute,
            "type": "view",
            "label": "查看牵挂",
        })

    # Canteen
    records = (await db.execute(
        select(CanteenRecord).where(
            CanteenRecord.community_id == community_id,
            CanteenRecord.parse_status == "success",
            CanteenRecord.created_at >= day_start,
            CanteenRecord.created_at < day_end,
        )
    )).scalars().all()
    elder_id_str = str(elder_user_id)
    for rec in records:
        for att in (rec.parsed_data or {}).get("attendees", []):
            if att.get("elder_id") == elder_id_str and att.get("present") is True:
                meal = (rec.parsed_data or {}).get("meal_type", "就餐")
                signals.append({
                    "hour": rec.created_at.hour if rec.created_at else 12,
                    "minute": rec.created_at.minute if rec.created_at else 0,
                    "type": "canteen",
                    "label": f"{meal}就餐",
                })

    # CommunityEvent
    events = (await db.execute(
        select(CommunityEvent).where(
            CommunityEvent.elder_id == elder_user_id,
            CommunityEvent.community_id == community_id,
            CommunityEvent.created_at >= day_start,
            CommunityEvent.created_at < day_end,
        ).order_by(CommunityEvent.created_at)
    )).scalars().all()
    type_labels = {"fall": "跌倒", "visit": "走访", "emergency": "紧急", "manual_confirm": "确认活跃"}
    for e in events:
        signals.append({
            "hour": e.created_at.hour if e.created_at else 0,
            "minute": e.created_at.minute if e.created_at else 0,
            "type": "event",
            "label": type_labels.get(e.event_type, e.event_type),
            "severity": e.severity,
        })

    # Alerts
    alerts = (await db.execute(
        select(Alert).where(
            Alert.elder_id == elder_user_id,
            Alert.created_at >= day_start,
            Alert.created_at < day_end,
        )
    )).scalars().all()
    for a in alerts:
        signals.append({
            "hour": a.created_at.hour if a.created_at else 0,
            "minute": a.created_at.minute if a.created_at else 0,
            "type": "alert",
            "label": a.message[:20] if a.message else "告警",
            "severity": a.alert_level,
        })

    signals.sort(key=lambda x: (x["hour"], x.get("minute", 0)))

    # 计算空白段（A/B 类 6h+ 无信号）
    from app.models.community import CommunityElder as CE
    care_level_result = await db.execute(
        select(CE.care_level).where(CE.elder_id == elder_user_id, CE.community_id == community_id)
    )
    care_level = care_level_result.scalar_one_or_none()

    gaps = []
    if care_level in ("A", "B") and signals:
        signal_hours = sorted(set(s["hour"] for s in signals))
        prev = 6
        for h in signal_hours:
            if h - prev >= 6:
                severity = "red" if h - prev >= 12 else "amber"
                gaps.append({"start_hour": prev, "end_hour": h, "severity": severity})
            prev = h
        if 22 - prev >= 6:
            severity = "red" if 22 - prev >= 12 else "amber"
            gaps.append({"start_hour": prev, "end_hour": 22, "severity": severity})
    elif care_level in ("A", "B") and not signals:
        gaps.append({"start_hour": 6, "end_hour": 22, "severity": "red"})

    return {
        "date": target_date,
        "signals": signals,
        "gaps": gaps,
    }
