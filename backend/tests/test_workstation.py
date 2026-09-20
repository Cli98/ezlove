"""AC-5 工作台 / AC-6 dashboard 用例（P3 §5 映射表）。

直调（不走 HTTP）：_check_no_signal / morning_silence_check（app.tasks.alert_checker）。
集成：GET /api/v1/community/dashboard 的 workstation 三列表与三 total 契约。
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.alert import Alert
from app.models.community_event import CommunityEvent
from app.tasks.alert_checker import SIGNAL_EVENT_TYPES, _check_no_signal, morning_silence_check

from tests.helpers import (
    create_alert, create_community, create_community_elder, create_user, create_worker,
    worker_headers,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── AC-5.1 timed_out 口径（urgent + 已过期 deadline）──

async def test_timed_out_not_empty(client, db):
    """过期 urgent 告警 → timed_out 含该条且 timed_out_total==1。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    elder = await create_user(db, "elder-w1", role="elder")
    now = datetime.now()
    await create_alert(
        db, community_id=community.id, elder_id=elder.id, alert_level="urgent",
        response_deadline=now - timedelta(hours=1), message="超时告警",
    )
    resp = await client.get("/api/v1/community/dashboard", headers=worker_headers(worker))
    ws = resp.json()["workstation"]
    assert resp.status_code == 200
    assert ws["timed_out_total"] == 1
    assert len(ws["timed_out"]) == 1
    assert ws["timed_out"][0]["message"] == "超时告警"


async def test_timed_not_overdue_excluded(client, db):
    """未过期 urgent 与已过期 warning 均不进 timed_out（口径=urgent+过期）。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    elder = await create_user(db, "elder-w2", role="elder")
    now = datetime.now()
    await create_alert(
        db, community_id=community.id, elder_id=elder.id, alert_level="urgent",
        response_deadline=now + timedelta(hours=10),  # 未过期
    )
    await create_alert(
        db, community_id=community.id, elder_id=elder.id, alert_level="warning",
        response_deadline=now - timedelta(hours=1),  # 过期但非 urgent
    )
    resp = await client.get("/api/v1/community/dashboard", headers=worker_headers(worker))
    ws = resp.json()["workstation"]
    assert ws["timed_out"] == []
    assert ws["timed_out_total"] == 0


# ── AC-5.2 manual_confirm 是活动信号（直调 _check_no_signal）──

async def test_no_signal_manual_confirm(db):
    """插入 manual_confirm CommunityEvent 后 _check_no_signal 返回 (False, "")。"""
    community = await create_community(db)
    elder_user = await create_user(db, "elder-w3", role="elder")
    record = await create_community_elder(db, community.id, elder_user.id, care_level="A")
    db.add(CommunityEvent(
        community_id=community.id, elder_id=elder_user.id,
        event_type="manual_confirm", source="manual", description="社工上门确认",
        severity="info", is_resolved=False,
    ))
    await db.commit()

    flagged, msg = await _check_no_signal(
        db, record, community.id, threshold_hours=18, now=datetime.now()
    )
    assert flagged is False
    assert msg == ""


# ── AC-5.3 SIGNAL_EVENT_TYPES 唯一定义 + 两消费方判定一致 ──

async def test_signal_types_single_definition(db):
    """静态：全库唯一定义且 alert_checker 内两处引用；直调：同一事件两处结论一致。"""
    from pathlib import Path

    app_dir = Path(__file__).resolve().parents[1] / "app"
    definitions = []
    references = 0
    for py in app_dir.rglob("*.py"):
        src = py.read_text()
        if "SIGNAL_EVENT_TYPES = " in src:
            definitions.append(str(py))
        references += src.count("SIGNAL_EVENT_TYPES")
    assert definitions == [str(app_dir / "tasks" / "alert_checker.py")]  # 唯一定义
    assert references >= 3  # 1 定义 + _check_no_signal / morning_silence_check 两处引用
    assert SIGNAL_EVENT_TYPES == frozenset({"visit", "manual_confirm"})

    # 语义一致：source=alert 的 other 事件不算信号（_check_no_signal 仍判无信号）
    community = await create_community(db)
    elder_user = await create_user(db, "elder-w4", role="elder")
    record = await create_community_elder(db, community.id, elder_user.id, care_level="A")
    db.add(CommunityEvent(
        community_id=community.id, elder_id=elder_user.id,
        event_type="other", source="alert", description="告警同步事件",
        severity="info", is_resolved=False,
    ))
    await db.commit()
    flagged, msg = await _check_no_signal(
        db, record, community.id, threshold_hours=18, now=datetime.now()
    )
    assert flagged is True  # alert 同步事件不构成活动信号
    assert "无任何活动信号" in msg


# ── AC-5.4 晨检不被告警同步事件压制（直调 morning_silence_check）──

async def test_morning_not_suppressed_by_alert_sync(db):
    """仅 source=alert 事件时 morning_silence_check 仍产生告警（OP-1）。"""
    community = await create_community(db)
    elder_user = await create_user(db, "elder-w5", role="elder", nickname="赵婆婆")
    await create_community_elder(db, community.id, elder_user.id, care_level="A")
    db.add(CommunityEvent(
        community_id=community.id, elder_id=elder_user.id,
        event_type="other", source="alert", description="家属侧未读告警同步",
        severity="info", is_resolved=False,
    ))
    await db.commit()

    await morning_silence_check()
    alerts = (await db.execute(
        select(Alert).where(Alert.elder_id == elder_user.id,
                            Alert.trigger_rule == "morning_silence")
    )).scalars().all()
    assert len(alerts) == 1  # 未被压制
    assert alerts[0].alert_level == "urgent"  # A 类 → urgent


# ── AC-5.3 行为级配对：晨检侧 manual_confirm 亦算活动信号（P5-iter2 D2）──

async def test_morning_manual_confirm_counts_as_signal(db):
    """晨检窗口内 manual_confirm 事件 → morning_silence_check 不产生晨间告警。

    与 test_morning_not_suppressed_by_alert_sync 正反配对（同为窗口内
    CommunityEvent）：source=alert 的 other 事件不算信号（仍告警）、
    manual_confirm 算信号（不告警）——两用例共同锁定 SIGNAL_EVENT_TYPES
    在晨检消费方的行为级口径（AC-5.3：同一事件对两处信号判定结论一致）。
    """
    community = await create_community(db)
    elder_user = await create_user(db, "elder-w7", role="elder", nickname="周爷爷")
    await create_community_elder(db, community.id, elder_user.id, care_level="A")
    db.add(CommunityEvent(
        community_id=community.id, elder_id=elder_user.id,
        event_type="manual_confirm", source="manual", description="社工上门确认老人状态",
        severity="info", is_resolved=False,
    ))
    await db.commit()

    await morning_silence_check()
    alerts = (await db.execute(
        select(Alert).where(Alert.elder_id == elder_user.id,
                            Alert.trigger_rule == "morning_silence")
    )).scalars().all()
    assert alerts == []  # manual_confirm 在晨检窗口内算活动信号 → 不产生晨间告警


# ── AC-5.5 timed_out 不被 limit(20) 截断 ──

async def test_timed_out_not_truncated(client, db):
    """25 条构造（最老 1 条过期 urgent、24 条更晚未超时）→ timed_out 含最老条且 total==1。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    elder = await create_user(db, "elder-w6", role="elder")
    now = datetime.now()
    oldest = await create_alert(
        db, community_id=community.id, elder_id=elder.id, alert_level="urgent",
        created_at=now - timedelta(hours=5),
        response_deadline=now - timedelta(hours=1), message="最老的超时告警",
    )
    for i in range(24):
        await create_alert(
            db, community_id=community.id, elder_id=elder.id, alert_level="warning",
            created_at=now - timedelta(hours=4) + timedelta(minutes=10 * i),
        )

    resp = await client.get("/api/v1/community/dashboard", headers=worker_headers(worker))
    ws = resp.json()["workstation"]
    # pending_alerts 列表截断到 20，total 独立计数 25
    assert len(ws["pending_alerts"]) == 20
    assert ws["pending_alerts_total"] == 25
    # timed_out 独立查询：含被 pending_alerts limit(20) 排除在外的最老条
    assert ws["timed_out_total"] == 1
    assert len(ws["timed_out"]) == 1
    assert ws["timed_out"][0]["id"] == str(oldest.id)
    assert ws["timed_out"][0]["message"] == "最老的超时告警"


# ── AC-6.1 total 与列表长度解耦 + 空社区契约 ──

async def test_totals_decoupled(client, db):
    """35 位待确认→total=35 且 len(列表)≤30；25 条告警→total=25 且 ≤20。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    for i in range(35):
        elder = await create_user(db, f"elder-total-{i}", role="elder")
        await create_community_elder(db, community.id, elder.id, care_level="A")
    now = datetime.now()
    for i in range(25):
        await create_alert(
            db, community_id=community.id, alert_level="warning",
            created_at=now - timedelta(minutes=25 - i),
        )

    resp = await client.get("/api/v1/community/dashboard", headers=worker_headers(worker))
    ws = resp.json()["workstation"]
    assert ws["pending_confirmations_total"] == 35
    assert len(ws["pending_confirmations"]) <= 30
    assert ws["pending_alerts_total"] == 25
    assert len(ws["pending_alerts"]) <= 20


async def test_empty_community_totals(client, db):
    """空社区（无告警、无 A/B 类老人）→ 三列表空数组、三 total 字段存在且 =0。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    resp = await client.get("/api/v1/community/dashboard", headers=worker_headers(worker))
    assert resp.status_code == 200
    ws = resp.json()["workstation"]
    assert ws["pending_confirmations"] == []
    assert ws["pending_alerts"] == []
    assert ws["timed_out"] == []
    assert ws["pending_confirmations_total"] == 0
    assert ws["pending_alerts_total"] == 0
    assert ws["timed_out_total"] == 0


# ── AC-6.2 响应兼容：既有字段名不变 ──

async def test_response_compat(client, db):
    """dashboard 响应含全部既有顶层字段与 workstation 字段（P3 §3.1 契约）。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    resp = await client.get("/api/v1/community/dashboard", headers=worker_headers(worker))
    body = resp.json()
    for key in (
        "total_elders", "level_a", "level_b", "level_c",
        "today_active_count", "today_active_rate", "pending_events",
        "risk_distribution", "areas", "workstation", "trends",
    ):
        assert key in body, f"缺少顶层字段 {key}"
    ws = body["workstation"]
    for key in (
        "pending_confirmations", "pending_alerts", "timed_out",
        "pending_confirmations_total", "pending_alerts_total", "timed_out_total",
    ):
        assert key in ws, f"workstation 缺少字段 {key}"
