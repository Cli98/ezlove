"""AC-3 跨社区越权用例（P3 §5 映射表；文案契约 P2 W-07/W-08 逐字断言）。"""
import pytest

from app.models.alert_rule import AlertRule

from tests.helpers import (
    create_community, create_community_elder, create_user, create_worker, worker_headers,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_rule(db, community_id, threshold_hours: int = 12,
                     enabled: bool = True) -> AlertRule:
    rule = AlertRule(
        community_id=community_id, care_level="A", rule_type="unread",
        threshold_hours=threshold_hours, enabled=enabled,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


# ── AC-3.1 PUT /community/elders/{id} ──

async def test_cross_community_elder_404(client, db):
    """W-07：A 社区 worker 更新 B 社区档案 → 404 逐字文案，B 社区数据无变更。"""
    community_a = await create_community(db, "A 社区")
    community_b = await create_community(db, "B 社区")
    worker_a = await create_worker(db, community_a.id, name="A 社工")
    elder_user = await create_user(db, "elder-c1", role="elder")
    record_b = await create_community_elder(db, community_b.id, elder_user.id)

    resp = await client.put(
        f"/api/v1/community/elders/{record_b.id}",
        json={"care_level": "C", "address": "越权写入"},
        headers=worker_headers(worker_a),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "老人档案不存在"
    await db.refresh(record_b)
    assert record_b.care_level == "A"  # B 社区数据未被改动


async def test_own_community_elder_200(client, db):
    """本社区 worker 更新 → 200（回归路径）。"""
    community = await create_community(db, "A 社区")
    worker = await create_worker(db, community.id)
    elder_user = await create_user(db, "elder-c2", role="elder")
    record = await create_community_elder(db, community.id, elder_user.id)

    resp = await client.put(
        f"/api/v1/community/elders/{record.id}",
        json={"care_level": "B", "address": "幸福路 1 号"},
        headers=worker_headers(worker),
    )
    assert resp.status_code == 200
    assert resp.json()["care_level"] == "B"


# ── AC-3.2 PUT /community/alert-rules/{id} ──

async def test_cross_community_rule_404(client, db):
    """W-08：A 社区 worker 更新 B 社区规则 → 404 逐字文案，B 规则无变更。"""
    community_a = await create_community(db, "A 社区")
    community_b = await create_community(db, "B 社区")
    worker_a = await create_worker(db, community_a.id, name="A 社工")
    rule_b = await _make_rule(db, community_b.id, threshold_hours=12)

    resp = await client.put(
        f"/api/v1/community/alert-rules/{rule_b.id}",
        json={"threshold_hours": 168},
        headers=worker_headers(worker_a),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "规则不存在"
    await db.refresh(rule_b)
    assert rule_b.threshold_hours == 12  # B 社区规则未被改动


async def test_own_community_rule_200(client, db):
    """本社区 worker 更新 → 200（回归路径）。"""
    community = await create_community(db, "A 社区")
    worker = await create_worker(db, community.id)
    rule = await _make_rule(db, community.id, threshold_hours=12)

    resp = await client.put(
        f"/api/v1/community/alert-rules/{rule.id}",
        json={"threshold_hours": 24, "enabled": False},
        headers=worker_headers(worker),
    )
    assert resp.status_code == 200
    assert resp.json()["threshold_hours"] == 24
    assert resp.json()["enabled"] is False


# ── AC-3.3 更新后读回一致性 ──

async def test_update_readback_consistency(client, db):
    """update 后 GET 读值 == 写入值（elders 档案与 alert-rules 双端）。"""
    community = await create_community(db, "A 社区")
    worker = await create_worker(db, community.id)
    elder_user = await create_user(db, "elder-c3", role="elder")
    record = await create_community_elder(db, community.id, elder_user.id)
    rule = await _make_rule(db, community.id, threshold_hours=12)

    # 档案：PUT 后 GET /community/elders/{id} 读回
    put_body = {
        "care_level": "C",
        "address": "幸福路 8 号",
        "emergency_contact_name": "张三",
        "emergency_contact_phone": "13800000000",
        "health_notes": "高血压，每日服药",
    }
    resp = await client.put(
        f"/api/v1/community/elders/{record.id}", json=put_body,
        headers=worker_headers(worker),
    )
    assert resp.status_code == 200
    detail = (await client.get(
        f"/api/v1/community/elders/{record.id}", headers=worker_headers(worker)
    )).json()
    assert detail["care_level"] == "C"
    assert detail["address"] == "幸福路 8 号"
    assert detail["emergency_contact_name"] == "张三"
    assert detail["emergency_contact_phone"] == "13800000000"
    assert detail["health_notes"] == "高血压，每日服药"

    # 规则：PUT 后 GET /community/alert-rules 读回
    resp2 = await client.put(
        f"/api/v1/community/alert-rules/{rule.id}",
        json={"threshold_hours": 48, "enabled": True, "config": {"channel": "workstation"}},
        headers=worker_headers(worker),
    )
    assert resp2.status_code == 200
    rules = (await client.get(
        "/api/v1/community/alert-rules", headers=worker_headers(worker)
    )).json()
    target = next(r for r in rules if r["id"] == str(rule.id))
    assert target["threshold_hours"] == 48
    assert target["enabled"] is True
    assert target["config"] == {"channel": "workstation"}
