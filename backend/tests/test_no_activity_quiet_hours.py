"""无活动提醒的夜间静默口径（2026-11-20 确认）。

红外是状态型传感器，老人整夜不出现在探测区时不翻转也就不上报；门磁夜里也不开关门。
滚动 12 小时窗口若跨夜累计，每天凌晨必然凑满时长而误报。
本用例锁定：夜间 22:00-07:00 不计入时长，且只在白天检查。
"""
from datetime import datetime

import pytest

from app.models.community_event import CommunityEvent
from app.tasks import alert_checker
from tests.helpers import (
    create_community,
    create_community_elder,
    create_user,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

SN = "862361073555016"
LAST_SIGNAL = datetime(2026, 11, 19, 14, 7)  # 前一天下午最后一次关门（门磁信号）


async def _prepare(db, monkeypatch):
    """一个 A 级老人 + 一台已绑定的红外设备 + 昨天下午的最后活动信号。"""
    community = await create_community(db, name="无活动口径社区")
    elder = await create_user(db, "elder-quiet-hours", role="elder")
    record = await create_community_elder(db, community.id, elder.id, care_level="A")
    # 绑定时间设到过去，避免 baseline 被建档时间顶到"现在"
    record.created_at = datetime(2026, 11, 17, 8, 0)
    db.add(CommunityEvent(
        community_id=community.id,
        elder_id=elder.id,
        event_type="door_close",
        source="device",
        description="门磁关闭（门磁传感器）",
        severity="info",
        created_at=LAST_SIGNAL,
    ))
    await db.commit()

    monkeypatch.setattr(
        alert_checker,
        "load_registry",
        lambda: ({SN: {"sn": SN, "device_type": 12, "label": "红外探测器",
                       "elder_record_id": str(record.id)}}, ""),
    )
    return community, elder


async def test_effective_hours_excludes_night():
    """纯函数：夜间时段整体扣除。"""
    # 20:00 → 次日 12:00：真实 16 小时，扣除 22:00-07:00 共 9 小时
    assert alert_checker._effective_hours(
        datetime(2026, 11, 19, 20, 0), datetime(2026, 11, 20, 12, 0)
    ) == pytest.approx(7.0)
    # 整天都在夜里：有效时长为 0
    assert alert_checker._effective_hours(
        datetime(2026, 11, 20, 23, 0), datetime(2026, 11, 21, 6, 0)
    ) == pytest.approx(0.0)
    # 纯白天不扣
    assert alert_checker._effective_hours(
        datetime(2026, 11, 20, 8, 0), datetime(2026, 11, 20, 19, 0)
    ) == pytest.approx(11.0)


async def test_night_check_does_not_alert(db, monkeypatch):
    """凌晨检查：真实间隔 12.3 小时，扣除夜间后仅 7.9 小时，不报警。"""
    await _prepare(db, monkeypatch)

    await alert_checker.no_activity_trace_check(now=datetime(2026, 11, 20, 2, 26))

    from sqlalchemy import select
    from app.models.alert import Alert

    alerts = (await db.execute(
        select(Alert).where(Alert.trigger_rule == "no_activity_trace")
    )).scalars().all()
    assert alerts == []


async def test_daytime_over_threshold_alerts(db, monkeypatch):
    """白天检查：扣除夜间后满 12 小时，正常产生提醒。"""
    community, elder = await _prepare(db, monkeypatch)

    await alert_checker.no_activity_trace_check(now=datetime(2026, 11, 20, 13, 0))

    from sqlalchemy import select
    from app.models.alert import Alert

    alerts = (await db.execute(
        select(Alert).where(
            Alert.trigger_rule == "no_activity_trace",
            Alert.elder_id == elder.id,
        )
    )).scalars().all()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.community_id == community.id
    assert alert.alert_level == "info"
    assert "没有活动迹象" in alert.message
    assert "已超过13小时" in alert.message


async def test_evening_check_still_quiet(db, monkeypatch):
    """22:00 之后不再检查（窗口外），即便时长足够也不报警。"""
    await _prepare(db, monkeypatch)

    await alert_checker.no_activity_trace_check(now=datetime(2026, 11, 20, 23, 10))

    from sqlalchemy import select
    from app.models.alert import Alert

    alerts = (await db.execute(
        select(Alert).where(Alert.trigger_rule == "no_activity_trace")
    )).scalars().all()
    assert alerts == []