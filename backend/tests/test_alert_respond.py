"""告警人工确认（误报 / 真实有效）用例。

结论以固定前缀写入 response_note（alerts 表无独立字段），
前端按【误报】/【有效】前缀解析展示。
"""
import pytest

from tests.helpers import create_alert, create_community, create_user, create_worker, worker_headers

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _prepare(db, suffix: str):
    community = await create_community(db, name=f"确认测试社区{suffix}")
    worker = await create_worker(db, community.id)
    elder = await create_user(db, f"elder-confirm-{suffix}", role="elder")
    return community, worker, elder


async def test_respond_false_alarm_adds_prefix_and_clears_pending(client, db):
    """误报：response_note 带【误报】前缀，告警从待处理列表消失。"""
    community, worker, elder = await _prepare(db, "a")
    alert = await create_alert(
        db, community_id=community.id, elder_id=elder.id,
        alert_type="sos", alert_level="urgent", message="语音报警器触发紧急报警",
    )

    resp = await client.post(
        f"/api/v1/community/alerts/{alert.id}/respond",
        headers=worker_headers(worker),
        json={"conclusion": "false_alarm", "response_note": "老人误触"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_resolved"] is True
    assert body["response_note"] == "【误报】老人误触"
    assert body["responded_at"] is not None
    assert body["resolved_at"] is not None

    pending = await client.get("/api/v1/community/alerts/pending", headers=worker_headers(worker))
    assert all(item["id"] != str(alert.id) for item in pending.json())


async def test_respond_valid_without_note_keeps_prefix_only(client, db):
    """真实有效且不填说明：response_note 只有【有效】前缀。"""
    community, worker, elder = await _prepare(db, "b")
    alert = await create_alert(
        db, community_id=community.id, elder_id=elder.id,
        alert_type="sos", alert_level="urgent", message="一键报警按钮触发紧急报警",
    )

    resp = await client.post(
        f"/api/v1/community/alerts/{alert.id}/respond",
        headers=worker_headers(worker),
        json={"conclusion": "valid"},
    )

    assert resp.status_code == 200
    assert resp.json()["response_note"] == "【有效】"
    assert resp.json()["is_resolved"] is True


async def test_respond_without_conclusion_keeps_plain_note(client, db):
    """不传结论（兼容旧调用）：response_note 原样保存，不加前缀。"""
    community, worker, elder = await _prepare(db, "c")
    alert = await create_alert(
        db, community_id=community.id, elder_id=elder.id,
        alert_level="warning", message="无活动提醒",
    )

    resp = await client.post(
        f"/api/v1/community/alerts/{alert.id}/respond",
        headers=worker_headers(worker),
        json={"response_note": "已电话确认"},
    )

    assert resp.status_code == 200
    assert resp.json()["response_note"] == "已电话确认"


async def test_respond_rejects_unknown_conclusion(client, db):
    """结论只接受 false_alarm / valid，其他值返回 422。"""
    community, worker, elder = await _prepare(db, "d")
    alert = await create_alert(db, community_id=community.id, elder_id=elder.id)

    resp = await client.post(
        f"/api/v1/community/alerts/{alert.id}/respond",
        headers=worker_headers(worker),
        json={"conclusion": "unknown", "response_note": "x"},
    )

    assert resp.status_code == 422