import uuid
from datetime import datetime, timezone, date, timedelta
from sqlalchemy import select, func, and_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_event import CommunityEvent
from app.models.community import CommunityElder, CommunityWorker


async def list_events(
    db: AsyncSession,
    community_id: uuid.UUID,
    severity: str | None = None,
    event_type: str | None = None,
    is_resolved: bool | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[CommunityEvent]:
    stmt = select(CommunityEvent).where(CommunityEvent.community_id == community_id)
    if severity:
        stmt = stmt.where(CommunityEvent.severity == severity)
    if event_type:
        stmt = stmt.where(CommunityEvent.event_type == event_type)
    if is_resolved is not None:
        stmt = stmt.where(CommunityEvent.is_resolved == is_resolved)
    stmt = stmt.order_by(CommunityEvent.created_at.desc())
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_events(
    db: AsyncSession,
    community_id: uuid.UUID,
    severity: str | None = None,
    event_type: str | None = None,
    is_resolved: bool | None = None,
) -> int:
    stmt = select(func.count(CommunityEvent.id)).where(CommunityEvent.community_id == community_id)
    if severity:
        stmt = stmt.where(CommunityEvent.severity == severity)
    if event_type:
        stmt = stmt.where(CommunityEvent.event_type == event_type)
    if is_resolved is not None:
        stmt = stmt.where(CommunityEvent.is_resolved == is_resolved)
    result = await db.execute(stmt)
    return result.scalar() or 0


async def create_event(
    db: AsyncSession,
    community_id: uuid.UUID,
    data: dict,
) -> CommunityEvent:
    event = CommunityEvent(community_id=community_id, **data)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def resolve_event(
    db: AsyncSession,
    event_id: uuid.UUID,
    worker_id: uuid.UUID,
    community_id: uuid.UUID,
    resolution_note: str | None = None,
) -> CommunityEvent:
    stmt = select(CommunityEvent).where(
        CommunityEvent.id == event_id,
        CommunityEvent.community_id == community_id,
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        raise ValueError("事件不存在")
    event.is_resolved = True
    event.resolved_by = worker_id
    event.resolved_at = datetime.now(timezone.utc)
    if resolution_note:
        event.resolution_note = resolution_note
    await db.commit()
    await db.refresh(event)
    return event


async def get_dashboard_data(
    db: AsyncSession,
    community_id: uuid.UUID,
) -> dict:
    stmt = select(
        CommunityElder.care_level,
        func.count(CommunityElder.id),
    ).where(
        CommunityElder.community_id == community_id
    ).group_by(CommunityElder.care_level)
    result = await db.execute(stmt)
    level_counts = {row[0]: row[1] for row in result.all()}

    total = sum(level_counts.values())

    today_start = datetime.combine(date.today(), datetime.min.time())

    active_ids = await _get_today_active_ids(db, community_id, today_start)

    areas = await _build_areas(db, community_id, active_ids)

    today_active = sum(
        b["active_count"] for a in areas for b in a["buildings"]
    )

    pending_stmt = select(func.count(CommunityEvent.id)).where(
        CommunityEvent.community_id == community_id,
        CommunityEvent.is_resolved == False,
        CommunityEvent.severity.in_(["urgent", "warning"]),
    )
    pending_result = await db.execute(pending_stmt)
    pending_events = pending_result.scalar() or 0

    risk_stmt = select(
        CommunityElder.risk_level,
        func.count(CommunityElder.id),
    ).where(
        CommunityElder.community_id == community_id,
        CommunityElder.risk_level.isnot(None),
    ).group_by(CommunityElder.risk_level)
    risk_result = await db.execute(risk_stmt)
    risk_distribution = {row[0]: row[1] for row in risk_result.all()}

    workstation = await _build_workstation(db, community_id, active_ids, today_start)
    trends = await _build_trends(db, community_id, total)

    return {
        "total_elders": total,
        "level_a": level_counts.get("A", 0),
        "level_b": level_counts.get("B", 0),
        "level_c": level_counts.get("C", 0),
        "today_active_count": today_active,
        "today_active_rate": round(today_active / total * 100, 1) if total > 0 else 0,
        "pending_events": pending_events,
        "risk_distribution": risk_distribution,
        "areas": areas,
        "workstation": workstation,
        "trends": trends,
    }


async def _build_trends(
    db: AsyncSession,
    community_id: uuid.UUID,
    total_elders: int,
) -> dict:
    from app.models.view_event import ViewEvent
    from app.models.canteen import CanteenRecord
    from app.models.alert import Alert

    today = date.today()
    week_start = datetime.combine(today - timedelta(days=6), datetime.min.time())

    elder_ids_stmt = select(CommunityElder.elder_id).where(
        CommunityElder.community_id == community_id
    )
    elder_ids_result = await db.execute(elder_ids_stmt)
    elder_ids = set(r[0] for r in elder_ids_result.all())
    if not elder_ids:
        return {"daily_active": [], "daily_alerts": [], "building_trends": {}}

    view_stmt = select(
        ViewEvent.viewer_id,
        cast(ViewEvent.viewed_at, Date).label("day"),
    ).where(
        ViewEvent.viewer_id.in_(elder_ids),
        ViewEvent.viewed_at >= week_start,
    )
    view_result = await db.execute(view_stmt)
    view_by_day: dict[date, set[uuid.UUID]] = {}
    for viewer_id, day in view_result.all():
        view_by_day.setdefault(day, set()).add(viewer_id)

    event_stmt = select(
        CommunityEvent.elder_id,
        cast(CommunityEvent.created_at, Date).label("day"),
    ).where(
        CommunityEvent.elder_id.in_(elder_ids),
        CommunityEvent.community_id == community_id,
        CommunityEvent.created_at >= week_start,
    )
    event_result = await db.execute(event_stmt)
    event_by_day: dict[date, set[uuid.UUID]] = {}
    for elder_id, day in event_result.all():
        event_by_day.setdefault(day, set()).add(elder_id)

    canteen_stmt = select(CanteenRecord).where(
        CanteenRecord.community_id == community_id,
        CanteenRecord.parse_status == "success",
        CanteenRecord.created_at >= week_start,
    )
    canteen_result = await db.execute(canteen_stmt)
    canteen_by_day: dict[date, set[uuid.UUID]] = {}
    for rec in canteen_result.scalars().all():
        rec_date_str = (rec.parsed_data or {}).get("date")
        if rec_date_str:
            try:
                rec_date = date.fromisoformat(rec_date_str)
            except ValueError:
                rec_date = rec.created_at.date()
        else:
            rec_date = rec.created_at.date()
        for att in (rec.parsed_data or {}).get("attendees", []):
            if att.get("present") is True and att.get("elder_id"):
                try:
                    canteen_by_day.setdefault(rec_date, set()).add(uuid.UUID(att["elder_id"]))
                except (ValueError, AttributeError):
                    pass

    alert_day = cast(Alert.created_at, Date).label("day")
    alert_new_stmt = select(
        alert_day,
        func.count(Alert.id),
    ).where(
        Alert.community_id == community_id,
        Alert.created_at >= week_start,
    ).group_by(alert_day)
    new_alerts_result = await db.execute(alert_new_stmt)
    new_alerts_map = {day: cnt for day, cnt in new_alerts_result.all()}

    resolved_day = cast(Alert.resolved_at, Date).label("day")
    alert_resolved_stmt = select(
        resolved_day,
        func.count(Alert.id),
    ).where(
        Alert.community_id == community_id,
        Alert.resolved_at >= week_start,
        Alert.resolved_at.isnot(None),
    ).group_by(resolved_day)
    resolved_result = await db.execute(alert_resolved_stmt)
    resolved_map = {day: cnt for day, cnt in resolved_result.all()}

    elder_addr_stmt = select(
        CommunityElder.elder_id,
        CommunityElder.address,
    ).where(CommunityElder.community_id == community_id)
    elder_addr_result = await db.execute(elder_addr_stmt)
    elder_building: dict[uuid.UUID, str] = {}
    building_elder_count: dict[str, int] = {}
    for eid, addr in elder_addr_result.all():
        bldg = _extract_building(addr)
        elder_building[eid] = bldg
        building_elder_count[bldg] = building_elder_count.get(bldg, 0) + 1

    daily_active = []
    daily_alerts = []
    building_daily_active: dict[str, list[float]] = {b: [] for b in building_elder_count}

    for i in range(7):
        d = today - timedelta(days=6 - i)
        active = set()
        active.update(view_by_day.get(d, set()))
        active.update(event_by_day.get(d, set()))
        active.update(canteen_by_day.get(d, set()))
        count = len(active)
        rate = round(count / total_elders * 100, 1) if total_elders > 0 else 0
        daily_active.append({
            "date": d.strftime("%m-%d"),
            "count": count,
            "rate": rate,
        })
        daily_alerts.append({
            "date": d.strftime("%m-%d"),
            "new": new_alerts_map.get(d, 0),
            "resolved": resolved_map.get(d, 0),
        })

        bldg_active: dict[str, int] = {}
        for eid in active:
            bldg = elder_building.get(eid)
            if bldg:
                bldg_active[bldg] = bldg_active.get(bldg, 0) + 1
        for bldg in building_elder_count:
            total_b = building_elder_count[bldg]
            active_b = bldg_active.get(bldg, 0)
            building_daily_active[bldg].append(
                round(active_b / total_b * 100, 1) if total_b > 0 else 0
            )

    return {
        "daily_active": daily_active,
        "daily_alerts": daily_alerts,
        "building_trends": building_daily_active,
    }


def _extract_building(address: str) -> str:
    if not address:
        return "未分配"
    idx = address.find("号楼")
    if idx > 0:
        return address[:idx + 2]
    return address


def _extract_area(building_name: str) -> str:
    for suffix in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
        idx = building_name.find(suffix)
        if idx > 0:
            return building_name[:idx]
    return building_name


async def _get_today_active_ids(
    db: AsyncSession,
    community_id: uuid.UUID,
    today_start: datetime,
) -> set[uuid.UUID]:
    from app.models.view_event import ViewEvent
    from app.models.canteen import CanteenRecord

    elder_ids_stmt = select(CommunityElder.elder_id).where(
        CommunityElder.community_id == community_id
    )
    elder_ids_result = await db.execute(elder_ids_stmt)
    elder_ids = [r[0] for r in elder_ids_result.all()]
    if not elder_ids:
        return set()

    active_ids: set[uuid.UUID] = set()

    view_stmt = select(ViewEvent.viewer_id).where(
        ViewEvent.viewer_id.in_(elder_ids),
        ViewEvent.viewed_at >= today_start,
    ).distinct()
    view_result = await db.execute(view_stmt)
    active_ids.update(view_result.scalars().all())

    event_stmt = select(CommunityEvent.elder_id).where(
        CommunityEvent.elder_id.in_(elder_ids),
        CommunityEvent.created_at >= today_start,
    ).distinct()
    event_result = await db.execute(event_stmt)
    active_ids.update(event_result.scalars().all())

    canteen_recs = (await db.execute(
        select(CanteenRecord).where(
            CanteenRecord.community_id == community_id,
            CanteenRecord.parse_status == "success",
            CanteenRecord.created_at >= today_start,
        )
    )).scalars().all()
    for rec in canteen_recs:
        for att in (rec.parsed_data or {}).get("attendees", []):
            if att.get("present") is True and att.get("elder_id"):
                try:
                    active_ids.add(uuid.UUID(att["elder_id"]))
                except (ValueError, AttributeError):
                    pass

    return active_ids


async def _build_areas(
    db: AsyncSession,
    community_id: uuid.UUID,
    active_ids: set[uuid.UUID],
) -> list[dict]:
    from app.models.alert import Alert

    stmt = select(
        CommunityElder.address,
        CommunityElder.care_level,
        CommunityElder.elder_id,
        CommunityElder.risk_level,
    ).where(
        CommunityElder.community_id == community_id,
    )
    result = await db.execute(stmt)
    rows = result.all()

    alert_stmt = select(
        Alert.elder_id,
        func.count(Alert.id),
    ).where(
        Alert.community_id == community_id,
        Alert.is_resolved == False,
    ).group_by(Alert.elder_id)
    alert_result = await db.execute(alert_stmt)
    alert_map = {r[0]: r[1] for r in alert_result.all()}

    building_data: dict[str, dict] = {}
    for address, care_level, elder_id, risk_level in rows:
        building = _extract_building(address)
        if building not in building_data:
            building_data[building] = {
                "elder_count": 0,
                "active_count": 0,
                "alert_count": 0,
                "levels": {"A": 0, "B": 0, "C": 0},
                "risk_counts": {"critical": 0, "warning": 0},
            }
        bd = building_data[building]
        bd["elder_count"] += 1
        if elder_id in active_ids:
            bd["active_count"] += 1
        bd["alert_count"] += alert_map.get(elder_id, 0)
        bd["levels"][care_level] = bd["levels"].get(care_level, 0) + 1
        if risk_level in ("critical", "warning"):
            bd["risk_counts"][risk_level] = bd["risk_counts"].get(risk_level, 0) + 1

    area_map: dict[str, list] = {}
    for building_name, bd in sorted(building_data.items()):
        area = _extract_area(building_name)
        rate = round(bd["active_count"] / bd["elder_count"] * 100, 1) if bd["elder_count"] > 0 else 0
        if bd["risk_counts"]["critical"] > 0:
            status = "red"
        elif bd["risk_counts"]["warning"] > 0 or rate < 50:
            status = "yellow"
        else:
            status = "green"

        building_info = {
            "name": building_name,
            "elder_count": bd["elder_count"],
            "active_count": bd["active_count"],
            "active_rate": rate,
            "alert_count": bd["alert_count"],
            "status": status,
        }
        area_map.setdefault(area, []).append(building_info)

    return [
        {"name": area_name, "buildings": buildings}
        for area_name, buildings in area_map.items()
    ]


async def _build_workstation(
    db: AsyncSession,
    community_id: uuid.UUID,
    active_ids: set[uuid.UUID],
    today_start: datetime,
) -> dict:
    from app.models.user import User
    from app.models.alert import Alert

    ab_stmt = (
        select(CommunityElder, User.nickname)
        .join(User, CommunityElder.elder_id == User.id)
        .where(
            CommunityElder.community_id == community_id,
            CommunityElder.care_level.in_(["A", "B"]),
        )
    )
    ab_result = await db.execute(ab_stmt)
    pending_confirmations = []
    for elder, name in ab_result.all():
        if elder.elder_id not in active_ids:
            pending_confirmations.append({
                "id": str(elder.id),
                "elder_id": str(elder.elder_id),
                "name": name,
                "care_level": elder.care_level,
                "address": elder.address,
                "risk_score": elder.risk_score,
                "risk_level": elder.risk_level,
            })

    pending_confirmations.sort(
        key=lambda x: (0 if x["care_level"] == "A" else 1, -(x["risk_score"] or 0))
    )

    alert_stmt = (
        select(Alert)
        .where(
            Alert.community_id == community_id,
            Alert.is_resolved == False,
        )
        .order_by(Alert.created_at.desc())
        .limit(20)
    )
    alert_result = await db.execute(alert_stmt)
    alerts = alert_result.scalars().all()

    elder_ids = [a.elder_id for a in alerts if a.elder_id]
    name_map = {}
    if elder_ids:
        name_result = await db.execute(
            select(User.id, User.nickname).where(User.id.in_(elder_ids))
        )
        name_map = {r[0]: r[1] for r in name_result.all()}

    pending_alerts = [
        {
            "id": str(a.id),
            "elder_name": name_map.get(a.elder_id, "未知"),
            "alert_type": a.alert_type,
            "alert_level": a.alert_level,
            "message": a.message,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "trigger_rule": a.trigger_rule,
        }
        for a in alerts
    ]

    timed_out = [
        a for a in pending_alerts
        if a["alert_level"] == "critical"
    ]

    return {
        "pending_confirmations": pending_confirmations[:30],
        "pending_alerts": pending_alerts,
        "timed_out": timed_out,
    }


async def get_building_elders(
    db: AsyncSession,
    community_id: uuid.UUID,
    building: str,
) -> list[dict]:
    from app.models.user import User
    from app.models.care_relation import CareRelation

    today_start = datetime.combine(date.today(), datetime.min.time())
    active_ids = await _get_today_active_ids(db, community_id, today_start)

    stmt = (
        select(CommunityElder, User.nickname)
        .join(User, CommunityElder.elder_id == User.id)
        .where(
            CommunityElder.community_id == community_id,
            CommunityElder.address.like(f"{building}%"),
        )
        .order_by(CommunityElder.address)
    )
    result = await db.execute(stmt)
    elders = result.all()

    elder_ids = [e[0].elder_id for e in elders]
    has_family_map = {}
    if elder_ids:
        fam_stmt = select(CareRelation.elder_user_id).where(
            CareRelation.elder_user_id.in_(elder_ids),
            CareRelation.status == "active",
        ).distinct()
        fam_result = await db.execute(fam_stmt)
        has_family_map = {eid: True for eid in fam_result.scalars().all()}

    return [
        {
            "id": str(elder.id),
            "elder_id": str(elder.elder_id),
            "name": name,
            "care_level": elder.care_level,
            "address": elder.address or "未分配",
            "today_active": elder.elder_id in active_ids,
            "has_family": has_family_map.get(elder.elder_id, False),
            "risk_score": elder.risk_score,
            "risk_level": elder.risk_level,
        }
        for elder, name in elders
    ]


async def sync_family_alerts_to_community(
    db: AsyncSession,
    community_id: uuid.UUID,
) -> dict:
    """
    Find unresolved family-side alerts for elders in this community.
    Create corresponding community_events for any that don't already exist.
    """
    from app.models.care_relation import CareRelation
    from app.models.alert import Alert

    # 1. Get all elder_ids in this community
    elder_stmt = select(CommunityElder.elder_id).where(
        CommunityElder.community_id == community_id
    )
    elder_result = await db.execute(elder_stmt)
    elder_ids = list(elder_result.scalars().all())

    if not elder_ids:
        return {"synced": 0, "total_alerts": 0}

    # 2. Find care_relations where elder_user_id IN (elder_ids)
    rel_stmt = select(CareRelation.id).where(
        CareRelation.elder_user_id.in_(elder_ids)
    )
    rel_result = await db.execute(rel_stmt)
    relation_ids = list(rel_result.scalars().all())

    if not relation_ids:
        return {"synced": 0, "total_alerts": 0}

    # 3. Find unresolved alerts for those relations
    alert_stmt = select(Alert).where(
        Alert.care_relation_id.in_(relation_ids),
        Alert.is_resolved == False,
    )
    alert_result = await db.execute(alert_stmt)
    alerts = list(alert_result.scalars().all())

    # 4. For each alert, check if a community_event already exists (by description match)
    synced = 0
    for alert in alerts:
        # Find the elder_id for this alert's care_relation
        elder_for_rel_stmt = select(CareRelation.elder_user_id).where(
            CareRelation.id == alert.care_relation_id
        )
        elder_for_rel_result = await db.execute(elder_for_rel_stmt)
        elder_user_id = elder_for_rel_result.scalar_one_or_none()

        if not elder_user_id:
            continue

        # Check if a community_event already exists with matching description
        existing_stmt = select(CommunityEvent.id).where(
            CommunityEvent.community_id == community_id,
            CommunityEvent.source == "alert",
            CommunityEvent.description == alert.message,
        )
        existing_result = await db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if not existing:
            # 5. Create a community_event with source='alert'
            severity_map = {"critical": "urgent", "warning": "warning", "info": "info"}
            severity = severity_map.get(alert.alert_level, "info")

            event = CommunityEvent(
                community_id=community_id,
                elder_id=elder_user_id,
                event_type="other",
                source="alert",
                description=alert.message,
                severity=severity,
                is_resolved=False,
            )
            db.add(event)
            synced += 1

    if synced > 0:
        await db.commit()

    return {"synced": synced, "total_alerts": len(alerts)}
