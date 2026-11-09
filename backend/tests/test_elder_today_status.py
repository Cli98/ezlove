"""老人档案与工作台的今日动态使用同一活动信号口径。"""

from datetime import datetime, timedelta

import pytest

from app.models.community_event import CommunityEvent
from app.models.canteen import CanteenRecord
from app.utils import datetime as ez_dt
from tests.helpers import (
    create_community,
    create_community_elder,
    create_user,
    create_worker,
    worker_headers,
)


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_today_motion_marks_archive_and_detail_active(client, db):
    """今日红外检测到有人时，档案列表不能再显示暂无新动态。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    elder = await create_user(db, "elder-today-motion", role="elder", nickname="测试老人")
    record = await create_community_elder(db, community.id, elder.id)
    db.add(CommunityEvent(
        community_id=community.id,
        elder_id=elder.id,
        event_type="motion_start",
        source="device",
        description="红外检测到活动",
        created_at=datetime.now(),
    ))
    await db.commit()

    headers = worker_headers(worker)
    archive = (await client.get("/api/v1/community/elders", headers=headers)).json()
    detail = (await client.get(
        f"/api/v1/community/elders/{record.id}/full", headers=headers
    )).json()
    dashboard = (await client.get("/api/v1/community/dashboard", headers=headers)).json()

    assert archive["items"][0]["today_active"] is True
    assert detail["today_active"] is True
    assert dashboard["today_active_count"] == 1
    assert dashboard["trends"]["daily_active"][-1]["count"] == 1


@pytest.mark.parametrize(
    ("event_type", "source"),
    [("motion_end", "device"), ("other", "alert"), ("visit", "alert")],
)
async def test_non_activity_event_does_not_mark_today_active(
    client, db, event_type, source
):
    """红外无人及告警同步事件不能证明老人今日有活动。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    elder = await create_user(db, f"elder-{event_type}", role="elder")
    record = await create_community_elder(db, community.id, elder.id)
    db.add(CommunityEvent(
        community_id=community.id,
        elder_id=elder.id,
        event_type=event_type,
        source=source,
        created_at=datetime.now(),
    ))
    await db.commit()

    headers = worker_headers(worker)
    archive = (await client.get("/api/v1/community/elders", headers=headers)).json()
    detail = (await client.get(
        f"/api/v1/community/elders/{record.id}/full", headers=headers
    )).json()
    dashboard = (await client.get("/api/v1/community/dashboard", headers=headers)).json()

    assert archive["items"][0]["today_active"] is False
    assert detail["today_active"] is False
    assert dashboard["today_active_count"] == 0
    assert dashboard["trends"]["daily_active"][-1]["count"] == 0


async def test_other_community_event_does_not_mark_today_active(client, db):
    """同一老人其他社区的设备事件不改变本社区今日状态。"""
    community = await create_community(db, "甲社区")
    other_community = await create_community(db, "乙社区")
    worker = await create_worker(db, community.id)
    elder = await create_user(db, "elder-two-communities", role="elder")
    record = await create_community_elder(db, community.id, elder.id)
    await create_community_elder(db, other_community.id, elder.id)
    db.add(CommunityEvent(
        community_id=other_community.id,
        elder_id=elder.id,
        event_type="motion_start",
        source="device",
        created_at=datetime.now(),
    ))
    await db.commit()

    headers = worker_headers(worker)
    archive = (await client.get("/api/v1/community/elders", headers=headers)).json()
    detail = (await client.get(
        f"/api/v1/community/elders/{record.id}/full", headers=headers
    )).json()
    dashboard = (await client.get("/api/v1/community/dashboard", headers=headers)).json()

    assert archive["items"][0]["today_active"] is False
    assert detail["today_active"] is False
    assert dashboard["today_active_count"] == 0


async def test_canteen_attendance_marks_archive_active(client, db):
    """今日食堂出勤与档案详情一样计入今日动态。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    elder = await create_user(db, "elder-canteen-today", role="elder")
    await create_community_elder(db, community.id, elder.id)
    db.add(CanteenRecord(
        community_id=community.id,
        recorded_by=worker.id,
        raw_text="测试出勤",
        parse_status="success",
        parsed_data={"attendees": [{"elder_id": str(elder.id), "present": True}]},
        created_at=datetime.now(),
    ))
    await db.commit()

    archive = (await client.get(
        "/api/v1/community/elders", headers=worker_headers(worker)
    )).json()
    assert archive["items"][0]["today_active"] is True


async def test_yesterday_motion_does_not_mark_today_active(client, db):
    """昨日红外活动仍保留在记录中，但不计入今天。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    elder = await create_user(db, "elder-yesterday-motion", role="elder")
    await create_community_elder(db, community.id, elder.id)
    db.add(CommunityEvent(
        community_id=community.id,
        elder_id=elder.id,
        event_type="motion_start",
        source="device",
        created_at=ez_dt.today_start() - timedelta(seconds=1),
    ))
    await db.commit()

    archive = (await client.get(
        "/api/v1/community/elders", headers=worker_headers(worker)
    )).json()
    assert archive["items"][0]["today_active"] is False


@pytest.mark.parametrize(
    ("recorded_today", "attendance_today"),
    [(True, False), (False, True)],
)
async def test_canteen_attendance_uses_meal_date(
    client, db, recorded_today, attendance_today
):
    """补录或提前录入时，以就餐日期而不是上传日期判断今日状态。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    elder = await create_user(db, "elder-meal-date", role="elder")
    record = await create_community_elder(db, community.id, elder.id)
    today = ez_dt.today_start()
    recorded_at = today if recorded_today else today - timedelta(days=1)
    meal_date = today.date() if attendance_today else (today - timedelta(days=1)).date()
    db.add(CanteenRecord(
        community_id=community.id,
        recorded_by=worker.id,
        raw_text="补录测试",
        parse_status="success",
        parsed_data={
            "date": meal_date.isoformat(),
            "attendees": [{"elder_id": str(elder.id), "present": True}],
        },
        created_at=recorded_at,
    ))
    await db.commit()

    headers = worker_headers(worker)
    archive = (await client.get("/api/v1/community/elders", headers=headers)).json()
    detail = (await client.get(
        f"/api/v1/community/elders/{record.id}/full", headers=headers
    )).json()
    dashboard = (await client.get("/api/v1/community/dashboard", headers=headers)).json()

    assert archive["items"][0]["today_active"] is attendance_today
    assert detail["today_active"] is attendance_today
    assert dashboard["today_active_count"] == int(attendance_today)
    assert dashboard["trends"]["daily_active"][-1]["count"] == int(attendance_today)


async def test_future_motion_does_not_mark_today_active(client, db):
    """明天的时间戳不应提前改变今天的状态。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    elder = await create_user(db, "elder-future-motion", role="elder")
    record = await create_community_elder(db, community.id, elder.id)
    db.add(CommunityEvent(
        community_id=community.id,
        elder_id=elder.id,
        event_type="motion_start",
        source="device",
        created_at=ez_dt.today_start() + timedelta(days=1),
    ))
    await db.commit()

    headers = worker_headers(worker)
    archive = (await client.get("/api/v1/community/elders", headers=headers)).json()
    detail = (await client.get(
        f"/api/v1/community/elders/{record.id}/full", headers=headers
    )).json()
    dashboard = (await client.get("/api/v1/community/dashboard", headers=headers)).json()

    assert archive["items"][0]["today_active"] is False
    assert detail["today_active"] is False
    assert dashboard["today_active_count"] == 0


async def test_canteen_compact_date_backfill_marks_today_active(client, db):
    """食堂补录日期为 YYYYMMDD 时，也应与 Python 日期解析口径一致。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    elder = await create_user(db, "elder-compact-meal-date", role="elder")
    await create_community_elder(db, community.id, elder.id)
    today = ez_dt.today_start()
    db.add(CanteenRecord(
        community_id=community.id,
        recorded_by=worker.id,
        raw_text="紧凑日期补录测试",
        parse_status="success",
        parsed_data={
            "date": today.strftime("%Y%m%d"),
            "attendees": [{"elder_id": str(elder.id), "present": True}],
        },
        created_at=today - timedelta(days=1),
    ))
    await db.commit()

    headers = worker_headers(worker)
    archive = (await client.get("/api/v1/community/elders", headers=headers)).json()
    dashboard = (await client.get("/api/v1/community/dashboard", headers=headers)).json()

    assert archive["items"][0]["today_active"] is True
    assert dashboard["trends"]["daily_active"][-1]["count"] == 1
