import json
import logging
import uuid
from datetime import datetime, timedelta, date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import CommunityElder, CommunityWorker
from app.models.community_event import CommunityEvent
from app.models.alert import Alert
from app.models.user import User
from app.models.view_event import ViewEvent
from app.models.canteen import CanteenRecord

logger = logging.getLogger("ezlove.agent")

TOOLS = [
    {
        "name": "query_inactive_elders",
        "description": "查询今日未活跃的老人列表，可按楼栋或护理等级筛选",
        "input_schema": {
            "type": "object",
            "properties": {
                "building": {"type": "string", "description": "楼栋名称，如'祥盛家园3号楼'"},
                "care_level": {"type": "string", "description": "护理等级: A/B/C"},
            },
        },
    },
    {
        "name": "get_building_summary",
        "description": "查询楼栋或小区的统计摘要（老人数、活跃率、告警数）",
        "input_schema": {
            "type": "object",
            "properties": {
                "area": {"type": "string", "description": "小区名称，如'祥盛家园'"},
                "building": {"type": "string", "description": "楼栋名称，如'祥盛家园3号楼'"},
            },
        },
    },
    {
        "name": "get_elder_status",
        "description": "根据姓名查询某位老人的当前状态",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "老人姓名"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_today_alerts",
        "description": "获取今日告警汇总",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "list_unconfirmed_elders",
        "description": "列出今日A/B级未活跃（待确认）的老人",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "confirm_elder_active",
        "description": "确认某位老人今日活跃状态。网格员通过电话/走访确认老人安全后使用此工具记录",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "老人姓名"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_weekly_trend",
        "description": "获取社区或指定楼栋过去7天的活跃趋势数据",
        "input_schema": {
            "type": "object",
            "properties": {
                "building": {"type": "string", "description": "楼栋名称（可选，不填则返回全社区）"},
            },
        },
    },
]


async def execute_tool(
    db: AsyncSession,
    community_id: uuid.UUID,
    tool_name: str,
    tool_input: dict,
    worker_id: uuid.UUID | None = None,
) -> str:
    today_start = datetime.combine(date.today(), datetime.min.time())

    if tool_name == "query_inactive_elders":
        return await _query_inactive(db, community_id, today_start, tool_input)
    elif tool_name == "get_building_summary":
        return await _building_summary(db, community_id, today_start, tool_input)
    elif tool_name == "get_elder_status":
        return await _elder_status(db, community_id, tool_input)
    elif tool_name == "get_today_alerts":
        return await _today_alerts(db, community_id)
    elif tool_name == "list_unconfirmed_elders":
        return await _unconfirmed(db, community_id, today_start)
    elif tool_name == "confirm_elder_active":
        return await _confirm_active(db, community_id, tool_input, worker_id)
    elif tool_name == "get_weekly_trend":
        return await _weekly_trend(db, community_id, tool_input)
    else:
        return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)


async def _get_active_ids(db, community_id, today_start):
    elder_ids_result = await db.execute(
        select(CommunityElder.elder_id).where(CommunityElder.community_id == community_id)
    )
    elder_ids = [r[0] for r in elder_ids_result.all()]
    if not elder_ids:
        return set()

    active = set()
    view_result = await db.execute(
        select(ViewEvent.viewer_id).where(
            ViewEvent.viewer_id.in_(elder_ids),
            ViewEvent.viewed_at >= today_start,
        ).distinct()
    )
    active.update(view_result.scalars().all())

    event_result = await db.execute(
        select(CommunityEvent.elder_id).where(
            CommunityEvent.elder_id.in_(elder_ids),
            CommunityEvent.created_at >= today_start,
        ).distinct()
    )
    active.update(event_result.scalars().all())

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
                    active.add(uuid.UUID(att["elder_id"]))
                except (ValueError, AttributeError):
                    pass

    return active


async def _query_inactive(db, community_id, today_start, inp):
    active_ids = await _get_active_ids(db, community_id, today_start)

    stmt = (
        select(CommunityElder, User.nickname)
        .join(User, CommunityElder.elder_id == User.id)
        .where(CommunityElder.community_id == community_id)
    )
    if inp.get("building"):
        stmt = stmt.where(CommunityElder.address.like(f"{inp['building']}%"))
    if inp.get("care_level"):
        stmt = stmt.where(CommunityElder.care_level == inp["care_level"])

    result = await db.execute(stmt)
    inactive = []
    for elder, name in result.all():
        if elder.elder_id not in active_ids:
            inactive.append({
                "id": str(elder.id),
                "name": name,
                "care_level": elder.care_level,
                "address": elder.address,
                "risk_score": elder.risk_score,
            })

    return json.dumps({
        "count": len(inactive),
        "elders": inactive[:30],
    }, ensure_ascii=False)


async def _building_summary(db, community_id, today_start, inp):
    active_ids = await _get_active_ids(db, community_id, today_start)

    stmt = (
        select(CommunityElder, User.nickname)
        .join(User, CommunityElder.elder_id == User.id)
        .where(CommunityElder.community_id == community_id)
    )
    if inp.get("building"):
        stmt = stmt.where(CommunityElder.address.like(f"{inp['building']}%"))
    elif inp.get("area"):
        stmt = stmt.where(CommunityElder.address.like(f"{inp['area']}%"))

    result = await db.execute(stmt)
    rows = result.all()

    total = len(rows)
    active = sum(1 for e, n in rows if e.elder_id in active_ids)
    levels = {"A": 0, "B": 0, "C": 0}
    for e, n in rows:
        levels[e.care_level] = levels.get(e.care_level, 0) + 1

    alert_count = (await db.execute(
        select(func.count(Alert.id)).where(
            Alert.community_id == community_id,
            Alert.is_resolved == False,
            Alert.elder_id.in_([e.elder_id for e, n in rows]) if rows else Alert.elder_id.is_(None),
        )
    )).scalar() or 0

    return json.dumps({
        "area": inp.get("area") or inp.get("building", "全社区"),
        "total_elders": total,
        "active_count": active,
        "active_rate": round(active / total * 100, 1) if total > 0 else 0,
        "levels": levels,
        "pending_alerts": alert_count,
    }, ensure_ascii=False)


async def _elder_status(db, community_id, inp):
    name = inp.get("name", "")
    result = await db.execute(
        select(CommunityElder, User.nickname)
        .join(User, CommunityElder.elder_id == User.id)
        .where(
            CommunityElder.community_id == community_id,
            User.nickname.like(f"%{name}%"),
        )
    )
    rows = result.all()
    if not rows:
        return json.dumps({"error": f"未找到名为'{name}'的老人"}, ensure_ascii=False)

    today_start = datetime.combine(date.today(), datetime.min.time())
    active_ids = await _get_active_ids(db, community_id, today_start)

    elders = []
    for elder, ename in rows[:5]:
        elders.append({
            "id": str(elder.id),
            "name": ename,
            "care_level": elder.care_level,
            "address": elder.address,
            "risk_score": elder.risk_score,
            "risk_level": elder.risk_level,
            "today_active": elder.elder_id in active_ids,
            "health_notes": elder.health_notes,
        })

    return json.dumps({"results": elders}, ensure_ascii=False)


async def _today_alerts(db, community_id):
    today_start = datetime.combine(date.today(), datetime.min.time())
    alerts = (await db.execute(
        select(Alert).where(
            Alert.community_id == community_id,
            Alert.is_resolved == False,
        ).order_by(Alert.created_at.desc()).limit(20)
    )).scalars().all()

    elder_ids = [a.elder_id for a in alerts if a.elder_id]
    name_map = {}
    if elder_ids:
        name_result = await db.execute(
            select(User.id, User.nickname).where(User.id.in_(elder_ids))
        )
        name_map = {r[0]: r[1] for r in name_result.all()}

    items = [{
        "elder_name": name_map.get(a.elder_id, "未知"),
        "type": a.alert_type,
        "level": a.alert_level,
        "message": a.message,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    } for a in alerts]

    return json.dumps({
        "count": len(items),
        "alerts": items,
    }, ensure_ascii=False)


async def _unconfirmed(db, community_id, today_start):
    active_ids = await _get_active_ids(db, community_id, today_start)

    result = await db.execute(
        select(CommunityElder, User.nickname)
        .join(User, CommunityElder.elder_id == User.id)
        .where(
            CommunityElder.community_id == community_id,
            CommunityElder.care_level.in_(["A", "B"]),
        )
    )
    unconfirmed = []
    for elder, name in result.all():
        if elder.elder_id not in active_ids:
            unconfirmed.append({
                "id": str(elder.id),
                "name": name,
                "care_level": elder.care_level,
                "address": elder.address,
                "risk_score": elder.risk_score,
            })

    unconfirmed.sort(key=lambda x: (0 if x["care_level"] == "A" else 1, -(x["risk_score"] or 0)))

    return json.dumps({
        "count": len(unconfirmed),
        "elders": unconfirmed[:30],
    }, ensure_ascii=False)


async def _confirm_active(db, community_id, inp, worker_id):
    name = inp.get("name", "")
    result = await db.execute(
        select(CommunityElder, User.nickname)
        .join(User, CommunityElder.elder_id == User.id)
        .where(
            CommunityElder.community_id == community_id,
            User.nickname.like(f"%{name}%"),
        )
    )
    rows = result.all()
    if not rows:
        return json.dumps({"error": f"未找到名为'{name}'的老人"}, ensure_ascii=False)

    if len(rows) > 1:
        candidates = [
            {"name": n, "care_level": e.care_level, "address": e.address, "id": str(e.id)}
            for e, n in rows[:10]
        ]
        return json.dumps({
            "ambiguous": True,
            "message": f"找到 {len(rows)} 位匹配的老人，请指定全名",
            "candidates": candidates,
        }, ensure_ascii=False)

    elder, elder_name = rows[0]
    event = CommunityEvent(
        id=uuid.uuid4(),
        community_id=community_id,
        elder_id=elder.elder_id,
        event_type="manual_confirm",
        source="manual",
        description=f"通过AI助手确认{elder_name}今日活跃",
        severity="info",
        is_resolved=True,
        resolved_by=worker_id,
        resolved_at=datetime.now(),
        created_at=datetime.now(),
    )
    db.add(event)
    await db.commit()

    return json.dumps({
        "success": True,
        "message": f"已确认 {elder_name}（{elder.care_level}级，{elder.address}）今日活跃",
        "elder_id": str(elder.id),
        "elder_name": elder_name,
    }, ensure_ascii=False)


async def _weekly_trend(db, community_id, inp):
    from app.services.community_event import _build_trends, _extract_building

    elder_stmt = select(func.count(CommunityElder.id)).where(
        CommunityElder.community_id == community_id
    )
    total = (await db.execute(elder_stmt)).scalar() or 0

    trends = await _build_trends(db, community_id, total)

    building = inp.get("building")
    if building:
        building_data = trends.get("building_trends", {}).get(building)
        if building_data:
            return json.dumps({
                "building": building,
                "daily_rates": building_data,
                "dates": [d["date"] for d in trends["daily_active"]],
            }, ensure_ascii=False)
        else:
            return json.dumps({"error": f"未找到楼栋'{building}'的趋势数据"}, ensure_ascii=False)

    return json.dumps({
        "daily_active": trends["daily_active"],
        "daily_alerts": trends["daily_alerts"],
    }, ensure_ascii=False)
