"""AC-2 elders 域 IDOR 用例（P3 §5 映射表；文案契约 P2 W-06 逐字断言）。"""
from datetime import date

import pytest
from sqlalchemy import select, func

from app.models.view_event import ViewEvent

from tests.helpers import (
    auth_headers, create_moment, create_relation, create_user, create_view_event,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── AC-2.1 GET /elders/{id}/status ──

async def test_status_no_relation_403(client, db):
    """W-06：无 active 绑定的用户查老人状态 → 403 逐字文案。"""
    stranger = await create_user(db, "stranger-e1", role="family")
    elder = await create_user(db, "elder-e1", role="elder", nickname="王奶奶")
    headers = await auth_headers(client, "stranger-e1")
    resp = await client.get(f"/api/v1/elders/{elder.id}/status", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "请先与老人完成绑定"


async def test_status_active_200(client, db):
    """合法 active 家属 → 200 含 elder_name / today_read（回归路径）。"""
    family = await create_user(db, "family-e1", role="family")
    elder = await create_user(db, "elder-e2", role="elder", nickname="李爷爷")
    await create_relation(db, family.id, elder.id)
    moment = await create_moment(db, family.id, elder.id)
    await create_view_event(db, moment.id, elder.id)  # 今日查看

    resp = await client.get(
        f"/api/v1/elders/{elder.id}/status", headers=await auth_headers(client, "family-e1")
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["elder_name"] == "李爷爷"
    assert body["today_read"] is True


# ── AC-2.2 GET /elders/{id}/activity ──

async def test_activity_no_relation_403(client, db):
    """W-06：无 active 绑定的用户查老人活跃 → 403 逐字文案。"""
    stranger = await create_user(db, "stranger-e2", role="family")
    elder = await create_user(db, "elder-e3", role="elder")
    headers = await auth_headers(client, "stranger-e2")
    resp = await client.get(f"/api/v1/elders/{elder.id}/activity", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "请先与老人完成绑定"


async def test_activity_active_200(client, db):
    """合法 active 家属 → 200 且今日活跃（active=True）出现在 days 中（回归路径）。"""
    family = await create_user(db, "family-e2", role="family")
    elder = await create_user(db, "elder-e4", role="elder")
    await create_relation(db, family.id, elder.id)
    moment = await create_moment(db, family.id, elder.id)
    await create_view_event(db, moment.id, elder.id)  # 今日查看

    resp = await client.get(
        f"/api/v1/elders/{elder.id}/activity?days=7",
        headers=await auth_headers(client, "family-e2"),
    )
    assert resp.status_code == 200
    days = resp.json()["days"]
    assert len(days) == 7
    today_entry = next(d for d in days if d["date"] == str(date.today()))
    assert today_entry["active"] is True


# ── AC-2.3 POST /elders/{id}/checkin 回归 ──

async def test_checkin_regression(client, db):
    """合法家属代签 → 200 + view_events 落库（viewer=老人）；无关系 → 403「无权操作」。"""
    family = await create_user(db, "family-e3", role="family")
    elder = await create_user(db, "elder-e5", role="elder")
    await create_relation(db, family.id, elder.id)
    before = (await db.execute(select(func.count(ViewEvent.id)))).scalar() or 0

    resp = await client.post(
        f"/api/v1/elders/{elder.id}/checkin", headers=await auth_headers(client, "family-e3")
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    events = (await db.execute(
        select(ViewEvent).where(ViewEvent.viewer_id == elder.id)
    )).scalars().all()
    assert len(events) == before + 1
    assert events[0].moment_id is None  # 代签不带 moment

    stranger = await create_user(db, "stranger-e3", role="family")
    resp2 = await client.post(
        f"/api/v1/elders/{elder.id}/checkin", headers=await auth_headers(client, "stranger-e3")
    )
    assert resp2.status_code == 403
    assert resp2.json()["detail"] == "无权操作"
