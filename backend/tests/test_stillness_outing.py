"""设备关怀三条规则：红外短时静止、红外无生活轨迹、门磁长时间未触发。

阈值、生效时段、重复间隔全部来自 alert_rules（管理后台「告警规则」页可改），
内置默认见 services/alert_rules.py 的 DEFAULTS / RULE_DEFAULTS。
2026-10-28 与白莉娜老师确认：红外 1 小时不动 / 12 小时无生活轨迹，门磁 24 小时未触发（8:00–8:00）。
2026-10-29 白老师补充：预警是平台展示口径（不发电话/微信）、设备离线要给规则“断电”、
走访/人工确认/食堂就餐算活动、门磁装好满 24 小时无记录先核实设备。
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.canteen import CanteenRecord
from app.models.community_event import CommunityEvent
from app.services import alert_rules as rules_service
from app.tasks import alert_checker

from tests.helpers import create_community, create_community_elder, create_user, create_worker

pytestmark = pytest.mark.asyncio(loop_scope="session")

FULL_DAY = {"check_hours": [0, 24]}  # 绕过默认 7:00–22:00 时段，让用例任何时刻都能跑


@pytest.fixture(autouse=True)
def _reset_offline_state():
    """离线状态是进程内缓存，用例之间必须隔离。"""
    alert_checker._offline_since.clear()
    yield
    alert_checker._offline_since.clear()


def _patch_registry(monkeypatch, record_id, device_type: int, sn: str):
    devices = {sn: {"sn": sn, "device_type": device_type, "elder_record_id": str(record_id)}}
    monkeypatch.setattr(alert_checker, "load_registry", lambda path=None: (devices, ""))


async def _set_rule(db, community_id, rule_type: str, care_level: str = "A", *,
                    hours: int, enabled: bool = True, **config) -> AlertRule:
    """写入社区自定义规则（这三条判定的唯一配置源）。"""
    rule = AlertRule(
        community_id=community_id, care_level=care_level, rule_type=rule_type,
        threshold_hours=hours, enabled=enabled, config=config or None,
    )
    db.add(rule)
    await db.commit()
    return rule


async def _motion_elder(db, tag: str, idle_hours: float | None = 10,
                        care_level: str = "A", event_type: str = "motion_start"):
    """红外设备老人 + 一条 idle_hours 小时前的设备活动（idle_hours=None 表示无任何活动记录）。"""
    community = await create_community(db)
    elder = await create_user(db, f"{tag}-elder", role="elder", nickname="姚增德")
    record = await create_community_elder(db, community.id, elder.id, care_level=care_level)
    # 档案建档时间提前，基线不再被“刚建档”重置
    record.created_at = datetime.now() - timedelta(days=30)
    if idle_hours is not None:
        db.add(CommunityEvent(
            community_id=community.id, elder_id=elder.id, event_type=event_type,
            source="device", description="设备检测到活动", severity="info",
            created_at=datetime.now() - timedelta(hours=idle_hours),
        ))
    await db.commit()
    await db.refresh(record)
    return community, elder, record


async def _alerts(db, trigger_rule: str) -> list[Alert]:
    result = await db.execute(select(Alert).where(Alert.trigger_rule == trigger_rule))
    return list(result.scalars().all())


# ── 红外短时静止（默认 1 小时）──

async def test_stillness_alert_when_no_activity(db, monkeypatch):
    """超过配置阈值没检测到活动 → 产生静止提醒。"""
    community, elder, record = await _motion_elder(db, "still-1", idle_hours=10)
    await _set_rule(db, community.id, "stillness", hours=1, **FULL_DAY)
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-TEST-1")

    await alert_checker.stillness_check()

    alerts = await _alerts(db, "stillness")
    assert len(alerts) == 1
    assert alerts[0].alert_type == "stillness"
    assert alerts[0].alert_level == "urgent"          # A 类 → urgent
    assert alerts[0].elder_id == elder.id
    assert "10小时没有活动迹象" in alerts[0].message
    assert "跌倒风险" in alerts[0].message


async def test_stillness_recent_activity_suppresses(db, monkeypatch):
    """阈值内有活动 → 不产生提醒。"""
    community, _, record = await _motion_elder(db, "still-2", idle_hours=0.2)
    await _set_rule(db, community.id, "stillness", hours=1, **FULL_DAY)
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-TEST-2")

    await alert_checker.stillness_check()
    assert await _alerts(db, "stillness") == []


async def test_stillness_outside_active_window(db, monkeypatch):
    """当前钟点不在生效时段内（如夜间）→ 不判定。"""
    hour = datetime.now().hour
    community, _, record = await _motion_elder(db, "still-3", idle_hours=10)
    # 只覆盖 next-hour 的窗口，使 now.hour 必然落在时段外
    await _set_rule(db, community.id, "stillness", hours=1,
                    check_hours=[(hour + 1) % 24, (hour + 2) % 24])
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-TEST-3")

    await alert_checker.stillness_check()
    assert await _alerts(db, "stillness") == []


async def test_stillness_rule_disabled(db, monkeypatch):
    """规则开关关闭 → 完全不判定（管理后台可关）。"""
    community, _, record = await _motion_elder(db, "still-4", idle_hours=10)
    await _set_rule(db, community.id, "stillness", hours=1, enabled=False, **FULL_DAY)
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-TEST-4")

    await alert_checker.stillness_check()
    assert await _alerts(db, "stillness") == []


async def test_stillness_dedupes_with_morning_silence(db, monkeypatch):
    """已有未解决的晨检提醒 → 静止预警不重复落库。"""
    community, elder, record = await _motion_elder(db, "still-5", idle_hours=10)
    await _set_rule(db, community.id, "stillness", hours=1, **FULL_DAY)
    await _alerts(db, "stillness")  # 基线：确认为空
    db.add(Alert(
        elder_id=elder.id, community_id=community.id, alert_type="morning_silence",
        alert_level="warning", message="晨检提醒", trigger_rule="morning_silence",
        is_resolved=False,
    ))
    await db.commit()
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-TEST-5")

    await alert_checker.stillness_check()
    assert await _alerts(db, "stillness") == []


async def test_stillness_respects_dedupe_interval(db, monkeypatch):
    """重复间隔内已有未解决的静止告警 → 不新增第二条。"""
    community, elder, record = await _motion_elder(db, "still-6", idle_hours=10)
    await _set_rule(db, community.id, "stillness", hours=1, dedupe_hours=6, **FULL_DAY)
    db.add(Alert(
        elder_id=elder.id, community_id=community.id, alert_type="stillness",
        alert_level="urgent", message="上一次静止提醒", trigger_rule="stillness",
        is_resolved=False, created_at=datetime.now() - timedelta(hours=2),
    ))
    await db.commit()
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-TEST-6")

    await alert_checker.stillness_check()
    assert len(await _alerts(db, "stillness")) == 1  # 仍是那条历史告警，未新增


async def test_stillness_escalated_to_no_activity_trace(db, monkeypatch):
    """静止时长已达“无生活轨迹”阈值 → 由升级规则出告警，静止规则不重复提醒。"""
    community, _, record = await _motion_elder(db, "still-7", idle_hours=10)
    await _set_rule(db, community.id, "stillness", hours=1, **FULL_DAY)
    await _set_rule(db, community.id, "no_activity_trace", hours=6, **FULL_DAY)
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-TEST-7")

    await alert_checker.stillness_check()
    assert await _alerts(db, "stillness") == []

    await alert_checker.no_activity_trace_check()
    alerts = await _alerts(db, "no_activity_trace")
    assert len(alerts) == 1
    assert "10小时无生活轨迹" in alerts[0].message


# ── 红外无生活轨迹（默认 12 小时，全天生效）──

async def test_no_activity_trace_alert(db, monkeypatch):
    """全天没有任何活动迹象 → 无生活轨迹提醒。"""
    community, _, record = await _motion_elder(db, "trace-1", idle_hours=20)
    await _set_rule(db, community.id, "no_activity_trace", hours=12)  # 默认时段即全天
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-TRACE-1")

    await alert_checker.no_activity_trace_check()

    alerts = await _alerts(db, "no_activity_trace")
    assert len(alerts) == 1
    assert alerts[0].alert_level == "urgent"
    assert "无生活轨迹" in alerts[0].message
    # 规则全名 17 字符，写进 alerts.alert_type（varchar16）会直接报错，故用短名
    assert alerts[0].alert_type == "no_activity"


async def test_no_activity_trace_recent_activity_suppresses(db, monkeypatch):
    """阈值内有活动 → 不提醒。"""
    community, _, record = await _motion_elder(db, "trace-2", idle_hours=5)
    await _set_rule(db, community.id, "no_activity_trace", hours=12)
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-TRACE-2")

    await alert_checker.no_activity_trace_check()
    assert await _alerts(db, "no_activity_trace") == []


# ── 门磁长时间未触发（默认 24 小时，每日 8:00 检查 8:00–8:00）──

async def _door_elder(db, tag: str, last_trigger_hours: float | None, care_level: str = "A"):
    community = await create_community(db)
    elder = await create_user(db, f"{tag}-elder", role="elder", nickname="赵奶奶")
    record = await create_community_elder(db, community.id, elder.id, care_level=care_level)
    if last_trigger_hours is not None:
        db.add(CommunityEvent(
            community_id=community.id, elder_id=elder.id, event_type="door_open",
            source="device", description="门磁打开", severity="info",
            created_at=datetime.now() - timedelta(hours=last_trigger_hours),
        ))
    await db.commit()
    await db.refresh(record)
    return community, elder, record


async def test_no_outing_alert_when_door_not_triggered(db, monkeypatch):
    """窗口内没有开门动作 → 产生外出关怀提醒。"""
    community, elder, record = await _door_elder(db, "outing-1", last_trigger_hours=100)
    await _set_rule(db, community.id, "no_outing", hours=24,
                    check_hour=datetime.now().hour, dedupe_hours=24)
    _patch_registry(monkeypatch, record.id, alert_checker.DOOR_DEVICE_TYPE, "DOOR-TEST-1")

    await alert_checker.no_outing_check()

    alerts = await _alerts(db, "no_outing")
    assert len(alerts) == 1
    assert alerts[0].elder_id == elder.id
    assert alerts[0].alert_level == "warning"          # A 类 → warning
    assert "100小时没有开门外出记录" in alerts[0].message


async def test_no_outing_skips_outside_check_hour(db, monkeypatch):
    """未到每日检查时点 → 不判定（8:00 窗口语义）。"""
    community, _, record = await _door_elder(db, "outing-2", last_trigger_hours=100)
    await _set_rule(db, community.id, "no_outing", hours=24,
                    check_hour=(datetime.now().hour + 1) % 24)
    _patch_registry(monkeypatch, record.id, alert_checker.DOOR_DEVICE_TYPE, "DOOR-TEST-2")

    await alert_checker.no_outing_check()
    assert await _alerts(db, "no_outing") == []


async def test_no_outing_skips_without_door_history(db, monkeypatch):
    """刚装门磁（未满一个周期）→ 先不下“未外出”结论。"""
    community, _, record = await _door_elder(db, "outing-3", last_trigger_hours=None)
    await _set_rule(db, community.id, "no_outing", hours=24,
                    check_hour=datetime.now().hour)
    _patch_registry(monkeypatch, record.id, alert_checker.DOOR_DEVICE_TYPE, "DOOR-TEST-3")

    await alert_checker.no_outing_check()
    assert await _alerts(db, "no_outing") == []


async def test_no_outing_recent_door_close_counts_as_trigger(db, monkeypatch):
    """窗口内有过关门（与开门同为触发）→ 不提醒。"""
    community, _, record = await _door_elder(db, "outing-4", last_trigger_hours=2)
    await _set_rule(db, community.id, "no_outing", hours=24,
                    check_hour=datetime.now().hour)
    _patch_registry(monkeypatch, record.id, alert_checker.DOOR_DEVICE_TYPE, "DOOR-TEST-4")

    await alert_checker.no_outing_check()
    assert await _alerts(db, "no_outing") == []


# ── 规则可配置：DB 覆盖内置默认 + seed 幂等补齐 ──

async def test_db_threshold_overrides_builtin_default(db, monkeypatch):
    """内置默认 1 小时；社区改成 6 小时后，静止 3 小时的老人不应被提醒。"""
    community, _, record = await _motion_elder(db, "cfg-1", idle_hours=3)
    await _set_rule(db, community.id, "stillness", hours=6, **FULL_DAY)
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-CFG-1")

    await alert_checker.stillness_check()
    assert await _alerts(db, "stillness") == []

    # 同一社区把阈值调回 1 小时 → 立即生效（读的是 alert_rules，不是常量）
    rule = (await db.execute(select(AlertRule).where(AlertRule.community_id == community.id))).scalar_one()
    rule.threshold_hours = 1
    await db.commit()

    await alert_checker.stillness_check()
    assert len(await _alerts(db, "stillness")) == 1


async def test_seed_backfills_missing_rules_idempotently(db):
    """老社区无需迁移：seed 只补缺失规则，已自定义的值不被覆盖，重复执行不产生新行。"""
    community = await create_community(db)
    custom = await _set_rule(db, community.id, "stillness", hours=8)

    created = await rules_service.seed_default_rules(db, community.id)
    await db.commit()

    assert all(r.rule_type != "stillness" or r.care_level != "A" for r in created)
    rules = {
        (r.care_level, r.rule_type): r
        for r in (await db.execute(select(AlertRule).where(AlertRule.community_id == community.id))).scalars()
    }
    assert rules[("A", "stillness")] is custom
    assert custom.threshold_hours == 8                     # 自定义值未被覆盖
    assert rules[("A", "no_activity_trace")].threshold_hours == 12
    assert rules[("B", "no_outing")].threshold_hours == 24
    assert rules[("C", "no_outing")].config["check_hour"] == 8   # 默认 8:00 窗口

    assert await rules_service.seed_default_rules(db, community.id) == []


async def test_load_rule_config_merges_params(db):
    """config 只存差异项，其余参数回退 RULE_DEFAULTS。"""
    community = await create_community(db)
    await _set_rule(db, community.id, "no_outing", hours=36, dedupe_hours=12)
    await _set_rule(db, community.id, "no_outing", care_level="B", hours=36, enabled=False)

    cfg = await rules_service.load_rule_config(db, community.id, "no_outing")
    assert cfg["A"] == {"hours": 36, "enabled": True,
                        "params": {"check_hour": 8, "dedupe_hours": 12}}
    assert cfg["B"]["enabled"] is False
    assert cfg["C"] == {"hours": 24, "enabled": True,        # 未配置 → 内置默认
                        "params": {"check_hour": 8, "dedupe_hours": 24}}


# ── 活动信号白名单 ──

async def test_signal_types_include_device_activity():
    """门磁开合与红外有人算活动信号，红外“无人”不算。"""
    assert {"door_open", "door_close", "motion_start"} <= alert_checker.SIGNAL_EVENT_TYPES
    assert "motion_end" not in alert_checker.SIGNAL_EVENT_TYPES


# ── 2026-10-29 白老师确认口径的落地用例 ──

async def test_visit_event_counts_as_activity(db, monkeypatch):
    """网格员走访/人工确认也算活动 → 不再报静止（白老师：按建议实施）。"""
    community, _, record = await _motion_elder(db, "signal-1", idle_hours=None)
    db.add(CommunityEvent(
        community_id=community.id, elder_id=record.elder_id, event_type="visit",
        source="worker", description="网格员上门走访", severity="info",
        created_at=datetime.now() - timedelta(minutes=30),
    ))
    await db.commit()
    await _set_rule(db, community.id, "stillness", hours=1, **FULL_DAY)
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-SIG-1")

    await alert_checker.stillness_check()
    assert await _alerts(db, "stillness") == []


async def test_canteen_presence_counts_as_activity(db, monkeypatch):
    """食堂就餐也算活动（避免“人刚在食堂吃过饭，系统还报没动静”）。"""
    community, elder, record = await _motion_elder(db, "signal-2", idle_hours=None)
    worker = await create_worker(db, community.id)
    db.add(CanteenRecord(
        community_id=community.id, raw_text="今日午餐", parse_status="success",
        recorded_by=worker.id,
        parsed_data={"attendees": [{"elder_id": str(elder.id), "present": True}]},
        created_at=datetime.now() - timedelta(minutes=20),
    ))
    await db.commit()
    await _set_rule(db, community.id, "stillness", hours=1, **FULL_DAY)
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-SIG-2")

    await alert_checker.stillness_check()
    assert await _alerts(db, "stillness") == []


async def test_door_verify_alert_when_installed_but_never_triggered(db, monkeypatch):
    """装好满 24 小时仍无任何开关门记录 → 提醒核实设备（只提一次）。"""
    community, _, record = await _door_elder(db, "outing-5", last_trigger_hours=None)
    record.created_at = datetime.now() - timedelta(days=3)
    await db.commit()
    await _set_rule(db, community.id, "no_outing", hours=24, check_hour=datetime.now().hour)
    _patch_registry(monkeypatch, record.id, alert_checker.DOOR_DEVICE_TYPE, "DOOR-VERIFY-1")

    await alert_checker.no_outing_check()
    alerts = await _alerts(db, "door_verify")
    assert len(alerts) == 1
    assert alerts[0].alert_type == "device_check"
    assert "核实门磁" in alerts[0].message

    await alert_checker.no_outing_check()
    assert len(await _alerts(db, "door_verify")) == 1  # 同一老人不重复提醒


async def test_offline_device_suspends_stillness(db, monkeypatch):
    """设备离线超阈值 → 静止规则暂停（断电），避免把设备故障报成老人没活动。"""
    community, _, record = await _motion_elder(db, "offline-1", idle_hours=10)
    await _set_rule(db, community.id, "stillness", hours=1, **FULL_DAY)
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-OFF-1")
    alert_checker._offline_since["PIR-OFF-1"] = datetime.now() - timedelta(hours=2)

    await alert_checker.stillness_check()
    assert await _alerts(db, "stillness") == []


async def test_device_offline_check_pauses_and_auto_resolves(db, monkeypatch):
    """离线 → 生成设备提醒并断电；恢复在线 → 自动解除。"""
    community, elder, record = await _motion_elder(db, "offline-2", idle_hours=10)
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-OFF-2")
    monkeypatch.setattr(alert_checker, "DEVICE_OFFLINE_HOURS", 0)

    async def fake_status(sns, *, use_cache=True):
        return {sn: {"available": True, "platform_status": 2} for sn in sns}

    monkeypatch.setattr(alert_checker.phchn_open_api, "fetch_devices_status", fake_status)
    await alert_checker.device_offline_check()

    alerts = await _alerts(db, "device_offline")
    assert len(alerts) == 1
    assert alerts[0].elder_id == elder.id
    assert alerts[0].alert_type == "device_offline"
    assert "已暂停该设备的活跃提醒" in alerts[0].message

    await alert_checker.device_offline_check()   # 未解决前不重复
    assert len(await _alerts(db, "device_offline")) == 1

    async def online(sns, *, use_cache=True):
        return {sn: {"available": True, "platform_status": 1} for sn in sns}

    monkeypatch.setattr(alert_checker.phchn_open_api, "fetch_devices_status", online)
    await alert_checker.device_offline_check()
    row = (await db.execute(select(Alert).where(Alert.trigger_rule == "device_offline"))).scalar_one()
    await db.refresh(row)
    assert row.is_resolved is True
    assert row.response_note == "设备已恢复在线，自动解除"


async def test_device_offline_check_skips_when_platform_unavailable(db, monkeypatch):
    """平台接口不可用时不判定，避免平台故障误停全部规则。"""
    community, _, record = await _motion_elder(db, "offline-3", idle_hours=10)
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-OFF-3")
    monkeypatch.setattr(alert_checker, "DEVICE_OFFLINE_HOURS", 0)

    async def unavailable(sns, *, use_cache=True):
        return {sn: {"available": False} for sn in sns}

    monkeypatch.setattr(alert_checker.phchn_open_api, "fetch_devices_status", unavailable)
    await alert_checker.device_offline_check()

    assert await _alerts(db, "device_offline") == []
    assert alert_checker._offline_since == {}


async def test_device_care_alerts_are_platform_only_by_default(db, monkeypatch):
    """白老师：预警是平台展示口径，默认不发微信/电话。"""
    community, _, record = await _motion_elder(db, "notify-1", idle_hours=10)
    await _set_rule(db, community.id, "stillness", hours=1, **FULL_DAY)
    _patch_registry(monkeypatch, record.id, alert_checker.MOTION_DEVICE_TYPE, "PIR-NOTIFY-1")

    calls = []

    async def fake_notify(*args, **kwargs):
        calls.append(args)

    from app.services import notification
    monkeypatch.setattr(notification, "notify_worker_alert", fake_notify)

    await alert_checker.stillness_check()
    assert len(await _alerts(db, "stillness")) == 1
    assert calls == []
