import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import CommunityElder
from app.models.user import User
from app.models.care_moment import CareMoment
from app.models.view_event import ViewEvent
from app.models.care_relation import CareRelation
from app.models.alert import Alert
from app.services.timeline import get_elder_timeline, get_activity_summary

WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


async def get_elder_full_detail(
    db: AsyncSession,
    elder_id: uuid.UUID,
    community_id: uuid.UUID,
) -> dict | None:
    """
    Fetch comprehensive elder details for the community side,
    including family-side data. Scoped to community_id.
    """
    # 1. Fetch community_elder record scoped to community_id, joined with user
    stmt = (
        select(CommunityElder, User)
        .join(User, CommunityElder.elder_id == User.id)
        .where(
            CommunityElder.id == elder_id,
            CommunityElder.community_id == community_id,
        )
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if not row:
        return None

    elder_record, user = row

    # 2. Build elder info block
    elder_info = {
        "id": str(elder_record.id),
        "name": user.nickname,
        "phone": user.phone,
        "care_level": elder_record.care_level,
        "address": elder_record.address,
        "health_notes": elder_record.health_notes,
        "emergency_contact": {
            "name": elder_record.emergency_contact_name,
            "phone": elder_record.emergency_contact_phone,
        },
    }

    # 3. Today active（多源：ViewEvent + 食堂 + 社区活动）+ last active
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_active = False

    active_stmt = (
        select(ViewEvent.id)
        .where(ViewEvent.viewer_id == user.id, ViewEvent.viewed_at >= today_start)
        .limit(1)
    )
    active_result = await db.execute(active_stmt)
    if active_result.scalar_one_or_none() is not None:
        today_active = True

    if not today_active:
        from app.models.community_event import CommunityEvent as CE
        event_stmt = select(CE.id).where(
            CE.elder_id == user.id, CE.created_at >= today_start
        ).limit(1)
        if (await db.execute(event_stmt)).scalar_one_or_none():
            today_active = True

    if not today_active:
        from app.models.canteen import CanteenRecord
        canteen_recs = (await db.execute(
            select(CanteenRecord).where(
                CanteenRecord.community_id == community_id,
                CanteenRecord.parse_status == "success",
                CanteenRecord.created_at >= today_start,
            )
        )).scalars().all()
        elder_id_str = str(user.id)
        for rec in canteen_recs:
            for att in (rec.parsed_data or {}).get("attendees", []):
                if att.get("elder_id") == elder_id_str and att.get("present") is True:
                    today_active = True
                    break
            if today_active:
                break

    last_stmt = (
        select(ViewEvent.viewed_at)
        .where(ViewEvent.viewer_id == user.id)
        .order_by(ViewEvent.viewed_at.desc())
        .limit(1)
    )
    last_result = await db.execute(last_stmt)
    last_active_at = last_result.scalar_one_or_none()

    # 4. Care moments sent to this elder (last 20)
    moments_stmt = (
        select(CareMoment, User.nickname.label("sender_name"))
        .join(User, CareMoment.sender_id == User.id)
        .where(CareMoment.elder_id == user.id)
        .order_by(CareMoment.created_at.desc())
        .limit(20)
    )
    moments_result = await db.execute(moments_stmt)
    moments_rows = moments_result.all()

    # 5. Check read status for each moment
    moment_ids = [m[0].id for m in moments_rows]
    read_map: dict[uuid.UUID, bool] = {}
    if moment_ids:
        read_stmt = (
            select(ViewEvent.moment_id)
            .where(ViewEvent.moment_id.in_(moment_ids), ViewEvent.viewer_id == user.id)
            .distinct()
        )
        read_result = await db.execute(read_stmt)
        read_map = {mid: True for mid in read_result.scalars().all()}

    care_moments = []
    for moment, sender_name in moments_rows:
        care_moments.append({
            "id": str(moment.id),
            "text_content": moment.text_content,
            "created_at": moment.created_at.isoformat(),
            "is_read": read_map.get(moment.id, False),
            "sender_name": sender_name,
        })

    # 6. 7-day activity calendar
    days = 7
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    cal_stmt = (
        select(func.date(ViewEvent.viewed_at))
        .where(ViewEvent.viewer_id == user.id, ViewEvent.viewed_at >= start)
        .group_by(func.date(ViewEvent.viewed_at))
    )
    cal_result = await db.execute(cal_stmt)
    active_dates = {r[0] for r in cal_result.all()}

    activity_calendar = []
    for i in range(days):
        d = (start + timedelta(days=i)).date()
        activity_calendar.append({
            "date": str(d),
            "active": d in active_dates,
        })

    # 7. Alerts related to this elder's care_relations
    relations_stmt = select(CareRelation).where(CareRelation.elder_user_id == user.id)
    relations_result = await db.execute(relations_stmt)
    relations = list(relations_result.scalars().all())

    relation_ids = [r.id for r in relations]
    alerts_list = []
    if relation_ids:
        alerts_stmt = (
            select(Alert)
            .where(Alert.care_relation_id.in_(relation_ids))
            .order_by(Alert.created_at.desc())
        )
        alerts_result = await db.execute(alerts_stmt)
        alerts = list(alerts_result.scalars().all())
        alerts_list = [
            {
                "id": str(a.id),
                "alert_type": a.alert_type,
                "alert_level": a.alert_level,
                "message": a.message,
                "is_resolved": a.is_resolved,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ]

    # 8. Family relations
    family_relations = []
    if relation_ids:
        for rel in relations:
            fam_stmt = select(User.nickname).where(User.id == rel.family_user_id)
            fam_result = await db.execute(fam_stmt)
            fam_name = fam_result.scalar_one_or_none()
            family_relations.append({
                "relation_id": str(rel.id),
                "family_member_name": fam_name,
                "relation_label": rel.relation_label,
                "status": rel.status,
            })

    # 9. 时间线和活跃度（异步聚合）
    recent_timeline = await get_elder_timeline(db, user.id, community_id, days=7, limit=10)
    activity_summary = await get_activity_summary(db, user.id, community_id, days=30)

    # 10. 社区侧告警
    community_alerts_stmt = (
        select(Alert)
        .where(Alert.elder_id == user.id, Alert.community_id == community_id)
        .order_by(Alert.created_at.desc())
    )
    community_alerts_result = await db.execute(community_alerts_stmt)
    for a in community_alerts_result.scalars().all():
        alerts_list.append({
            "id": str(a.id),
            "alert_type": a.alert_type,
            "alert_level": a.alert_level,
            "message": a.message,
            "is_resolved": a.is_resolved,
            "created_at": a.created_at.isoformat(),
            "escalation_level": a.escalation_level,
            "trigger_rule": a.trigger_rule,
        })

    return {
        "elder": elder_info,
        "today_active": today_active,
        "last_active_at": last_active_at.isoformat() if last_active_at else None,
        "care_moments": care_moments,
        "activity_calendar": activity_calendar,
        "alerts": alerts_list,
        "family_relations": family_relations,
        "recent_timeline": recent_timeline.get("items", []),
        "activity_summary": activity_summary,
        "risk": {
            "score": elder_record.risk_score,
            "level": elder_record.risk_level,
            "calculated_at": elder_record.risk_calculated_at.isoformat() if elder_record.risk_calculated_at else None,
            "details": elder_record.risk_details,
        },
    }
