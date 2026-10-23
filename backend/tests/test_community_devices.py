"""社区端设备监控与安全曲线用例。

覆盖：平台客户端凭证加载（env 优先/文件兜底/缺失降级）、状态解析、mocked 全流程、
设备列表社区过滤、未绑定设备 fallback 可见性、详情跨社区 404、ICCID 脱敏、
风险快照历史端点（含天数过滤与跨社区 404）。
"""
import json
from datetime import datetime, timedelta

import pytest

from app.config import settings
from app.models.risk_snapshot import RiskScoreSnapshot
from app.services import nbiot, phchn_open_api

from tests.helpers import (
    create_alert,
    create_community,
    create_community_elder,
    create_user,
    create_worker,
    worker_headers,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

BUTTON_SN = "869978086196018"
PIR_SN = "869978086196026"


@pytest.fixture(autouse=True)
def _reset_platform_caches(monkeypatch):
    """隔离平台客户端缓存与真实凭证文件（env 空 + 默认文件路径由各用例自控）。"""
    monkeypatch.setattr(settings, "PHCHN_APP_ID", "")
    monkeypatch.setattr(settings, "PHCHN_APP_SECRET", "")
    monkeypatch.setattr(settings, "PHCHN_PLATFORM_FILE", "")
    phchn_open_api.reset_caches()
    yield
    phchn_open_api.reset_caches()


def _stub_status(sn: str, **overrides) -> dict:
    base = {
        "available": True,
        "reason": None,
        "sn": sn,
        "platform_status": 1,
        "status_label": "在线",
        "last_online_time": None,
        "platform_device_id": None,
        "device_name": None,
        "model": None,
        "attributes": {"signal": 5, "battery": 1, "voltage": 3000, "iccid": None},
        "attributes_updated_at": None,
    }
    base.update(overrides)
    return base


def _fake_fetch_many(monkeypatch, single=None):
    async def _many(sns, use_cache=True):
        return {sn: (single(sn) if single else _stub_status(sn)) for sn in sns}

    monkeypatch.setattr(phchn_open_api, "fetch_devices_status", _many)


# ── 平台客户端 ──────────────────────────────────────────────


async def test_credentials_env_priority(monkeypatch):
    monkeypatch.setattr(settings, "PHCHN_APP_ID", "env-app")
    monkeypatch.setattr(settings, "PHCHN_APP_SECRET", "env-secret")
    creds = phchn_open_api.load_platform_credentials()
    assert creds == {
        "app_id": "env-app",
        "app_secret": "env-secret",
        "base_url": phchn_open_api.DEFAULT_BASE_URL,
    }


async def test_credentials_file_fallback(monkeypatch, tmp_path):
    path = tmp_path / "phchn.json"
    path.write_text(
        json.dumps({"app_id": "file-app", "app_secret": "file-secret", "base_url": "https://x/api"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "PHCHN_PLATFORM_FILE", str(path))
    creds = phchn_open_api.load_platform_credentials()
    assert creds["app_id"] == "file-app"
    assert creds["base_url"] == "https://x/api"


async def test_platform_config_file_present():
    """随包配置必须可用（防止误删导致线上设备页静默降级）。"""
    creds = phchn_open_api.load_platform_credentials()
    assert creds is not None
    assert creds["app_id"]


async def test_fetch_device_status_without_credentials(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "PHCHN_PLATFORM_FILE", str(tmp_path / "none.json"))
    status = await phchn_open_api.fetch_device_status("SN1")
    assert status["available"] is False
    assert status["reason"] == "credentials_missing"
    assert status["status_label"] == "未知"


def test_build_status_parses_properties():
    data = {
        "id": 23712,
        "productId": 22,
        "status": 1,
        "name": "张大爷-一键报警",
        "model": "PH-4GJA-01",
        "lastOnlineTime": 1792643516868,
    }
    props = {
        "signal": {"value": "5", "valueUpdateTime": 1792643517000},
        "battery": {"value": "1", "valueUpdateTime": 1792643517000},
        "voltage": {"value": "3054", "valueUpdateTime": 1792643517000},
        "heartbeat": {"value": "24", "valueUpdateTime": 1792643517000},
        "ambient_temperature": {"value": "25.7", "valueUpdateTime": 1792607230000},
        "manned_unmanned": {"value": None, "valueUpdateTime": None},
    }
    status = phchn_open_api._build_status("SN", data, props)
    assert status["available"] is True
    assert status["status_label"] == "在线"
    assert status["model"] == "PH-4GJA-01"
    assert status["last_online_time"] is not None
    assert status["attributes"]["signal"] == 5
    assert status["attributes"]["voltage"] == 3054
    assert status["attributes"]["heartbeat_hours"] == 24
    assert status["attributes"]["ambient_temperature"] == 25.7
    assert status["attributes"]["manned_unmanned"] is None
    assert status["attributes_updated_at"] is not None


async def test_fetch_device_status_mocked_flow(monkeypatch):
    async def fake_token(client, creds):
        return "tok"

    async def fake_api_get(client, creds, token, path, params):
        if path.endswith("get-by-sn"):
            return {
                "code": 0,
                "data": {"id": 9, "productId": 8, "status": 2, "name": "设备A", "model": "M", "lastOnlineTime": 1792643516868},
            }
        return {
            "code": 0,
            "data": [
                {"identifier": "status", "properties": [{"identifier": "battery", "value": "0", "valueUpdateTime": 1792643517000}]}
            ],
        }

    monkeypatch.setattr(
        phchn_open_api, "load_platform_credentials",
        lambda: {"app_id": "a", "app_secret": "s", "base_url": "http://x"},
    )
    monkeypatch.setattr(phchn_open_api, "_get_token", fake_token)
    monkeypatch.setattr(phchn_open_api, "_api_get", fake_api_get)

    status = await phchn_open_api.fetch_device_status("SN9", use_cache=False)
    assert status["available"] is True
    assert status["platform_status"] == 2
    assert status["status_label"] == "离线"
    assert status["attributes"]["battery"] == 0


# ── 设备列表与详情端点 ──────────────────────────────────────


@pytest.fixture
def registry(monkeypatch):
    # 绑定锚点为 elder_record_id（社区档案 ID）；具体值由 _two_communities_with_elders 创建档案后写入
    mapping = {
        "SN-A": {"sn": "SN-A", "device_type": 6, "label": "按钮A", "elder_record_id": ""},
        "SN-B": {"sn": "SN-B", "device_type": 12, "label": "红外B", "elder_record_id": ""},
    }
    monkeypatch.setattr(nbiot, "load_registry", lambda path=None: (mapping, ""))
    return mapping


async def _two_communities_with_elders(db, registry):
    community_a = await create_community(db, "社区A")
    community_b = await create_community(db, "社区B")
    worker_a = await create_worker(db, community_a.id, "社工A")
    worker_b = await create_worker(db, community_b.id, "社工B")
    wang = await create_user(db, "openid-wang", nickname="王奶奶")
    li = await create_user(db, "openid-li", nickname="李爷爷")
    wang_record = await create_community_elder(db, community_a.id, wang.id)
    li_record = await create_community_elder(db, community_b.id, li.id)
    registry["SN-A"]["elder_record_id"] = str(wang_record.id)
    registry["SN-B"]["elder_record_id"] = str(li_record.id)
    return community_a, community_b, worker_a, worker_b, wang, li


async def test_list_devices_filters_by_community(db, client, registry, monkeypatch):
    community_a, _, worker_a, _, wang, _ = await _two_communities_with_elders(db, registry)
    _fake_fetch_many(monkeypatch)

    resp = await client.get("/api/v1/community/devices", headers=worker_headers(worker_a))
    assert resp.status_code == 200
    body = resp.json()
    assert [d["sn"] for d in body["devices"]] == ["SN-A"]
    assert body["devices"][0]["elder"] == {
        "linked": True,
        "id": body["devices"][0]["elder"]["id"],
        "name": "王奶奶",
        "hint": None,
    }
    assert body["devices"][0]["type_label"] == "紧急报警器"
    assert body["summary"]["total"] == 1
    assert body["summary"]["online"] == 1
    assert body["summary"]["unlinked"] == 0
    assert body["summary"]["platform_available"] is True


async def test_list_devices_summary_low_battery(db, client, registry, monkeypatch):
    _, _, worker_a, _, _, _ = await _two_communities_with_elders(db, registry)

    def _single(sn):
        return _stub_status(sn, attributes={"signal": 2, "battery": 0, "voltage": 2800, "iccid": None})

    _fake_fetch_many(monkeypatch, single=_single)
    resp = await client.get("/api/v1/community/devices", headers=worker_headers(worker_a))
    body = resp.json()
    assert body["summary"]["low_battery"] == 1


async def test_unlinked_device_visible_via_unique_community(db, client, monkeypatch):
    """未绑定老人但全库唯一社区 → 该社区可见，标注未绑定。"""
    community = await create_community(db, "唯一社区")
    worker = await create_worker(db, community.id)
    mapping = {"SN-X": {"sn": "SN-X", "device_type": 6, "label": "按钮X", "elder_note": "平台设备名备注"}}
    monkeypatch.setattr(nbiot, "load_registry", lambda path=None: (mapping, ""))
    _fake_fetch_many(monkeypatch)

    resp = await client.get("/api/v1/community/devices", headers=worker_headers(worker))
    body = resp.json()
    assert len(body["devices"]) == 1
    assert body["devices"][0]["elder"]["linked"] is False
    assert body["devices"][0]["elder"]["hint"] == "设备未绑定到已建档老人"
    assert body["devices"][0]["elder"]["name"] == "平台设备名备注"
    assert body["summary"]["unlinked"] == 1


async def test_device_detail_cross_community_404(db, client, registry, monkeypatch):
    _, _, worker_a, _, _, _ = await _two_communities_with_elders(db, registry)
    _fake_fetch_many(monkeypatch)

    resp = await client.get("/api/v1/community/devices/SN-B", headers=worker_headers(worker_a))
    assert resp.status_code == 404


async def test_device_detail_masks_iccid_and_lists_alerts(db, client, registry, monkeypatch):
    community_a, _, worker_a, _, wang, _ = await _two_communities_with_elders(db, registry)
    await create_alert(
        db, elder_id=wang.id, community_id=community_a.id,
        alert_type="sos", alert_level="urgent", message="王奶奶触发紧急报警",
    )

    async def fake_status(sn, use_cache=True):
        return _stub_status(
            sn,
            attributes={"signal": 5, "battery": 1, "voltage": 3054,
                        "iccid": "898604A52121C2901375", "heartbeat_hours": 24},
        )

    monkeypatch.setattr(phchn_open_api, "fetch_device_status", fake_status)
    resp = await client.get("/api/v1/community/devices/SN-A", headers=worker_headers(worker_a))
    assert resp.status_code == 200
    body = resp.json()
    assert body["platform"]["attributes"]["iccid"] == "898604A5****1375"
    assert body["elder"]["name"] == "王奶奶"
    assert len(body["alerts"]) == 1
    assert body["alerts"][0]["alert_type"] == "sos"


async def test_device_detail_unknown_sn_404(db, client, registry, monkeypatch):
    _, _, worker_a, _, _, _ = await _two_communities_with_elders(db, registry)
    resp = await client.get("/api/v1/community/devices/SN-NOPE", headers=worker_headers(worker_a))
    assert resp.status_code == 404


# ── 风险快照历史（安全曲线） ────────────────────────────────


async def test_risk_history_endpoint(db, client):
    community = await create_community(db, "曲线社区")
    worker = await create_worker(db, community.id)
    elder_user = await create_user(db, "openid-curve", nickname="张大爷")
    enrollment = await create_community_elder(db, community.id, elder_user.id)

    today = datetime.now().date()
    for offset, score, level in [(2, 20, "normal"), (1, 55, "attention"), (0, 70, "warning")]:
        db.add(RiskScoreSnapshot(
            elder_id=enrollment.id, community_id=community.id,
            score=score, level=level, snapshot_date=today - timedelta(days=offset),
        ))
    await db.commit()

    resp = await client.get(
        f"/api/v1/community/elders/{enrollment.id}/risk/history?days=30",
        headers=worker_headers(worker),
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [(i["score"], i["level"]) for i in items] == [(20, "normal"), (55, "attention"), (70, "warning")]
    assert items[0]["date"] < items[-1]["date"]

    # days=2 → 只含今天与昨天
    resp2 = await client.get(
        f"/api/v1/community/elders/{enrollment.id}/risk/history?days=2",
        headers=worker_headers(worker),
    )
    assert [i["score"] for i in resp2.json()["items"]] == [55, 70]


async def test_risk_history_cross_community_404(db, client):
    community_a = await create_community(db, "社区A")
    community_b = await create_community(db, "社区B")
    worker_b = await create_worker(db, community_b.id)
    elder_user = await create_user(db, "openid-a", nickname="甲")
    enrollment = await create_community_elder(db, community_a.id, elder_user.id)

    resp = await client.get(
        f"/api/v1/community/elders/{enrollment.id}/risk/history",
        headers=worker_headers(worker_b),
    )
    assert resp.status_code == 404