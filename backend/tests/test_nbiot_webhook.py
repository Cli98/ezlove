"""NB-IoT 硬件推送接入用例（对接手册《API字段对接.md》）。

覆盖：button_press / battery_low / bathroom_motion_*、未登记设备、
幂等去重、未绑定老人兜底、URL 密钥校验、非法报文。
"""
import pytest
from sqlalchemy import select

from app.config import settings
from app.models.alert import Alert
from app.services import nbiot

from tests.helpers import (
    create_community,
    create_community_elder,
    create_relation,
    create_user,
    create_worker,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

BUTTON_SN = "869978086196018"
PIR_SN = "869978086196026"


@pytest.fixture(autouse=True)
def _reset_dedup_cache():
    nbiot.reset_dedup_cache()
    yield
    nbiot.reset_dedup_cache()


@pytest.fixture
def devices(monkeypatch):
    """替换配置文件读取，避免用例依赖真实 SN 的绑定内容。

    绑定锚点为 elder_record_id（社区档案 ID）：用例创建档案后写入 mapping 再推送。
    """
    mapping = {
        BUTTON_SN: {
            "sn": BUTTON_SN, "device_type": 6, "label": "一键报警按钮",
            "elder_record_id": "",
        },
        PIR_SN: {
            "sn": PIR_SN, "device_type": 12, "label": "红外探测器",
            "elder_record_id": "",
        },
    }
    monkeypatch.setattr(nbiot, "load_registry", lambda path=None: (mapping, ""))
    return mapping


def _push(sn: str, event: int, event_type: int, alarm_time: int = 1751623919507,
          content: str = "紧急报警", zone: str | None = None) -> dict:
    return {
        "messageType": 1,
        "message": {
            "deviceSn": sn,
            "event": event,
            "eventType": event_type,
            "content": content,
            "zone": zone,
            "childName": None,
            "alarmTime": alarm_time,
        },
        "timestamp": 1751623919982,
    }


async def _all_alerts(db) -> list[Alert]:
    result = await db.execute(select(Alert).order_by(Alert.created_at))
    return list(result.scalars().all())


async def test_config_file_has_two_real_devices():
    """随包配置必须包含两台真实设备（防止误删导致线上静默丢事件）。"""
    registry, _ = nbiot.load_registry()
    assert BUTTON_SN in registry
    assert PIR_SN in registry
    assert registry[BUTTON_SN]["device_type"] == 6
    assert registry[PIR_SN]["device_type"] == 12


async def test_button_press_creates_family_and_community_alerts(client, db, devices):
    community = await create_community(db)
    await create_worker(db, community.id)
    elder = await create_user(db, "nbiot-elder-1", role="elder", nickname="张大爷")
    family = await create_user(db, "nbiot-family-1", role="family", nickname="小张")
    relation = await create_relation(db, family.id, elder.id)
    record = await create_community_elder(db, community.id, elder.id)
    devices[BUTTON_SN]["elder_record_id"] = str(record.id)

    resp = await client.post(
        "/api/v1/webhook/nbiot",
        json=_push(BUTTON_SN, 1, 0, zone="卧室"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0 and body["created"] == 2

    alerts = await _all_alerts(db)
    assert len(alerts) == 2

    family_alert = next(a for a in alerts if a.care_relation_id == relation.id)
    assert family_alert.alert_type == "sos"
    assert family_alert.alert_level == "urgent"
    assert family_alert.trigger_rule == "device_button_press"
    assert "张大爷" in family_alert.message and "卧室" in family_alert.message

    community_alert = next(a for a in alerts if a.community_id == community.id)
    assert community_alert.elder_id == elder.id
    assert community_alert.response_deadline is not None


async def test_button_press_duplicate_push_is_idempotent(client, db, devices):
    community = await create_community(db)
    elder = await create_user(db, "nbiot-elder-2", role="elder", nickname="张大爷")
    family = await create_user(db, "nbiot-family-2", role="family")
    await create_relation(db, family.id, elder.id)
    record = await create_community_elder(db, community.id, elder.id)
    devices[BUTTON_SN]["elder_record_id"] = str(record.id)

    payload = _push(BUTTON_SN, 1, 0)
    assert (await client.post("/api/v1/webhook/nbiot", json=payload)).json()["created"] == 2
    # 平台重试：同 alarmTime 直接命中进程内去重
    assert (await client.post("/api/v1/webhook/nbiot", json=payload)).json()["created"] == 0
    # 新 alarmTime 但仍在 10 分钟窗口内：命中落库窗口去重
    retry = _push(BUTTON_SN, 1, 0, alarm_time=1751623919999)
    assert (await client.post("/api/v1/webhook/nbiot", json=retry)).json()["created"] == 0

    assert len(await _all_alerts(db)) == 2


async def test_button_press_unbound_elder_falls_back_to_community(client, db, devices):
    community = await create_community(db)
    await create_worker(db, community.id)

    resp = await client.post(
        "/api/v1/webhook/nbiot",
        json=_push(BUTTON_SN, 1, 0, alarm_time=1751623920001),
    )
    assert resp.status_code == 200 and resp.json()["created"] == 1

    alerts = await _all_alerts(db)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.elder_id is None
    assert alert.community_id == community.id
    assert alert.alert_type == "sos"
    assert "未绑定设备" in alert.message


async def test_button_press_unknown_record_id_falls_back(client, db, devices):
    """elder_record_id 指向不存在的档案 → 按未绑定兜底，绝不误绑他人。"""
    community = await create_community(db)
    await create_worker(db, community.id)
    devices[BUTTON_SN]["elder_record_id"] = "00000000-0000-0000-0000-000000000000"

    resp = await client.post(
        "/api/v1/webhook/nbiot",
        json=_push(BUTTON_SN, 1, 0, alarm_time=1751623920004),
    )
    assert resp.status_code == 200 and resp.json()["created"] == 1
    alerts = await _all_alerts(db)
    assert len(alerts) == 1
    assert alerts[0].elder_id is None
    assert "未绑定设备" in alerts[0].message


async def test_battery_low_creates_single_community_alert(client, db, devices):
    community = await create_community(db)
    elder = await create_user(db, "nbiot-elder-3", role="elder", nickname="张大爷")
    record = await create_community_elder(db, community.id, elder.id)
    devices[BUTTON_SN]["elder_record_id"] = str(record.id)

    resp = await client.post(
        "/api/v1/webhook/nbiot",
        json=_push(BUTTON_SN, 5, 0, content="电量低于20%"),
    )
    assert resp.json()["created"] == 1

    alerts = await _all_alerts(db)
    assert len(alerts) == 1
    assert alerts[0].alert_type == "device_battery"
    assert alerts[0].alert_level == "warning"
    assert alerts[0].trigger_rule == "device_battery_low"

    # 24 小时窗口内重复上报只留一条
    again = _push(BUTTON_SN, 5, 0, alarm_time=1751623920002)
    assert (await client.post("/api/v1/webhook/nbiot", json=again)).json()["created"] == 0


async def test_motion_events_only_logged(client, db, devices):
    community = await create_community(db)
    elder = await create_user(db, "nbiot-elder-4", role="elder", nickname="张大爷")
    await create_community_elder(db, community.id, elder.id)

    assert (await client.post(
        "/api/v1/webhook/nbiot", json=_push(PIR_SN, 2, 20, content="红外触发"),
    )).json()["created"] == 0
    assert (await client.post(
        "/api/v1/webhook/nbiot", json=_push(PIR_SN, 2, 19, content="离开，时长12分钟"),
    )).json()["created"] == 0

    assert await _all_alerts(db) == []


async def test_unknown_device_is_ignored(client, db, devices):
    resp = await client.post(
        "/api/v1/webhook/nbiot",
        json=_push("000000000000000", 1, 0),
    )
    assert resp.status_code == 200
    assert resp.json()["accepted"] is False
    assert await _all_alerts(db) == []


async def test_non_device_message_is_ignored(client, db, devices):
    resp = await client.post(
        "/api/v1/webhook/nbiot",
        json={"messageType": 2, "message": {}, "timestamp": 1},
    )
    assert resp.status_code == 200
    assert resp.json()["accepted"] is False


async def test_invalid_json_returns_200(client, db, devices):
    resp = await client.post(
        "/api/v1/webhook/nbiot",
        content=b"not-json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["msg"] == "ignored"


async def test_token_is_enforced_when_configured(client, db, devices, monkeypatch):
    monkeypatch.setattr(settings, "NBIOT_WEBHOOK_SECRET", "s3cret")

    payload = _push(BUTTON_SN, 1, 0, alarm_time=1751623920003)
    assert (await client.post("/api/v1/webhook/nbiot", json=payload)).status_code == 401
    assert (await client.post(
        "/api/v1/webhook/nbiot?token=wrong", json=payload,
    )).status_code == 401
    assert (await client.post(
        "/api/v1/webhook/nbiot?token=s3cret", json=payload,
    )).status_code == 200
    assert (await client.post(
        "/api/v1/webhook/nbiot", json=payload, headers={"X-NBIOT-Token": "s3cret"},
    )).status_code == 200
