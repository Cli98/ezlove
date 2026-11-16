"""关怀事项列表只承载人工待办：设备活动与告警同步项不应出现。

门磁/红外事件是老人在家轨迹，告警类已在 alerts 侧用「误报/有效」确认，
二者若再进关怀事项列表，就会变成永远处理不完的假待办。
"""
import io

import pytest
from openpyxl import load_workbook

from app.models.community_event import CommunityEvent
from tests.helpers import (
    create_community,
    create_community_elder,
    create_user,
    create_worker,
    worker_headers,
)

# 与 conftest 的 session 级 engine 对齐，避免 asyncpg 连接跨 event loop 复用
pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_event(db, community_id, elder_id, **kwargs) -> CommunityEvent:
    event = CommunityEvent(community_id=community_id, elder_id=elder_id, **kwargs)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def _seed_mixed(db):
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    elder = await create_user(db, "elder-events-mixed")
    await create_community_elder(db, community.id, elder.id)
    device = await _seed_event(
        db, community.id, elder.id,
        event_type="door_open", source="device",
        description="门磁打开（门磁传感器）", severity="info",
    )
    alert = await _seed_event(
        db, community.id, elder.id,
        event_type="other", source="alert",
        description="同步自告警的待办", severity="warning",
    )
    manual = await _seed_event(
        db, community.id, elder.id,
        event_type="visit", source="manual",
        description="上门探访", severity="info",
    )
    canteen = await _seed_event(
        db, community.id, elder.id,
        event_type="absent", source="canteen",
        description="午餐未到", severity="warning",
    )
    return worker, device, alert, manual, canteen


async def test_events_list_hides_device_activity_and_alert_sync(client, db):
    """门磁活动与告警同步项不进入列表，只保留人工待办。"""
    worker, device, alert, manual, canteen = await _seed_mixed(db)

    resp = await client.get("/api/v1/community/events", headers=worker_headers(worker))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == {str(manual.id), str(canteen.id)}


async def test_events_list_include_activity_returns_everything(client, db):
    """排查/审计场景可显式要求包含设备活动与告警同步项。"""
    worker, device, alert, manual, canteen = await _seed_mixed(db)

    resp = await client.get(
        "/api/v1/community/events?include_activity=true", headers=worker_headers(worker)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 4
    assert {item["id"] for item in body["items"]} == {
        str(device.id), str(alert.id), str(manual.id), str(canteen.id),
    }


async def test_export_events_hides_device_activity(client, db):
    """导出与列表同口径，不把门磁轨迹写进关怀事项 Excel。"""
    worker, *_ = await _seed_mixed(db)

    resp = await client.get("/api/v1/community/export/events", headers=worker_headers(worker))
    assert resp.status_code == 200, resp.text
    sheet = load_workbook(io.BytesIO(resp.content)).active
    rows = list(sheet.iter_rows(min_row=2, values_only=True))
    assert len(rows) == 2
    assert {row[3] for row in rows} == {"食堂", "手动"}