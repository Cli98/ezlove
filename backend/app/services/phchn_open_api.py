"""phchn 智慧物联网云平台开放 API 客户端（设备监控用）。

鉴权：GET {base}/system/oauth2/access-token?appid=&timestamp=&sign=
      sign = SHA256(appid + 13位毫秒时间戳 + app_secret)，token 有效期约 7200 秒。
业务：get-by-sn 查设备（在线状态/id/productId/型号）、device/service 查物模型属性
      （signal/battery/voltage/heartbeat 等，见《易挂念设备信号电量获取接口与实测值》）。
凭证：settings.PHCHN_APP_ID / PHCHN_APP_SECRET（环境变量优先）；缺省读
      config/phchn_platform.json（低频静态配置，发布通道不改 .env）。

降级约定：平台不可达/鉴权失败/设备缺失 → 返回 available=False 的占位结构并做短负缓存
（避免页面轮询打爆平台）；调用方照常渲染本地数据（绑定关系/告警），本模块不抛异常。
"""
import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger("ezlove.phchn")

DEFAULT_PLATFORM_FILE = Path(__file__).resolve().parents[2] / "config" / "phchn_platform.json"
DEFAULT_BASE_URL = "https://iot.phchn.com/admin-api"

DEVICE_TYPE_LABELS = {2: "门磁", 6: "紧急报警器", 12: "红外探测器"}
PLATFORM_STATUS_LABELS = {0: "未激活", 1: "在线", 2: "离线"}

_REQUEST_TIMEOUT = 10.0
_TOKEN_SAFETY_MARGIN = 300  # 提前 5 分钟刷新 token
_STATUS_CACHE_TTL = 60      # 设备状态正缓存
_STATUS_NEGATIVE_TTL = 30   # 降级结果短缓存

_token_cache: dict = {"token": None, "expires_at": 0.0}
_token_lock = asyncio.Lock()
_status_cache: dict[str, tuple[float, dict]] = {}
_platform_cache: dict = {"mtime": None, "creds": None}


def load_platform_credentials() -> dict | None:
    """凭证：环境变量优先；缺省读 JSON 文件（按 mtime 缓存，改文件无需重启）。"""
    if settings.PHCHN_APP_ID and settings.PHCHN_APP_SECRET:
        return {
            "app_id": settings.PHCHN_APP_ID,
            "app_secret": settings.PHCHN_APP_SECRET,
            "base_url": settings.PHCHN_API_BASE or DEFAULT_BASE_URL,
        }

    file_path = Path(settings.PHCHN_PLATFORM_FILE) if settings.PHCHN_PLATFORM_FILE else DEFAULT_PLATFORM_FILE
    try:
        mtime = file_path.stat().st_mtime
    except OSError:
        logger.warning("未找到 phchn 平台凭证配置：%s", file_path)
        return None

    if _platform_cache["mtime"] != mtime:
        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.exception("读取 phchn 平台凭证配置失败：%s", file_path)
            return None
        _platform_cache.update(
            mtime=mtime,
            creds={
                "app_id": str(raw.get("app_id") or "").strip(),
                "app_secret": str(raw.get("app_secret") or "").strip(),
                "base_url": str(raw.get("base_url") or "").strip() or DEFAULT_BASE_URL,
            },
        )

    creds = _platform_cache["creds"]
    if not creds or not creds["app_id"] or not creds["app_secret"]:
        return None
    return creds


def reset_caches() -> None:
    """测试用：清空 token 与状态缓存。"""
    _token_cache.update(token=None, expires_at=0.0)
    _status_cache.clear()
    _platform_cache.update(mtime=None, creds=None)


def _ms_to_iso(value) -> str | None:
    try:
        return datetime.fromtimestamp(int(value) / 1000).isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError):
        return None


def _to_int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _to_float(value) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


async def _get_token(client: httpx.AsyncClient, creds: dict) -> str | None:
    async with _token_lock:
        now = time.time()
        if _token_cache["token"] and _token_cache["expires_at"] > now + _TOKEN_SAFETY_MARGIN:
            return _token_cache["token"]

        timestamp = str(int(now * 1000))
        sign = hashlib.sha256(
            f"{creds['app_id']}{timestamp}{creds['app_secret']}".encode()
        ).hexdigest()
        resp = await client.get(
            f"{creds['base_url']}/system/oauth2/access-token",
            params={"appid": creds["app_id"], "timestamp": timestamp, "sign": sign},
        )
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data") or {}
        token = data.get("access_token")
        if body.get("code") != 0 or not token:
            logger.warning("phchn 获取 access_token 失败：code=%s msg=%s", body.get("code"), body.get("msg"))
            return None
        expires_in = _to_int(data.get("expires_in")) or 7200
        _token_cache.update(token=token, expires_at=now + expires_in)
        return token


async def _api_get(client: httpx.AsyncClient, creds: dict, token: str, path: str, params: dict) -> dict:
    resp = await client.get(
        f"{creds['base_url']}{path}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    return resp.json()


def _unavailable(sn: str, reason: str) -> dict:
    return {
        "available": False,
        "reason": reason,
        "sn": sn,
        "platform_status": None,
        "status_label": "未知",
        "last_online_time": None,
        "platform_device_id": None,
        "device_name": None,
        "model": None,
        "attributes": {},
        "attributes_updated_at": None,
    }


def _build_status(sn: str, data: dict, props: dict) -> dict:
    def prop_value(identifier):
        entry = props.get(identifier) or {}
        return entry.get("value")

    updated_candidates = [
        entry.get("valueUpdateTime") for entry in props.values() if entry.get("valueUpdateTime")
    ]
    updated_at = _ms_to_iso(max(updated_candidates)) if updated_candidates else None

    status_code = _to_int(data.get("status"))
    return {
        "available": True,
        "reason": None,
        "sn": sn,
        "platform_device_id": data.get("id"),
        "device_name": data.get("name"),
        "model": data.get("model"),
        "platform_status": status_code,
        "status_label": PLATFORM_STATUS_LABELS.get(status_code, "未知"),
        "last_online_time": _ms_to_iso(data.get("lastOnlineTime")),
        "attributes": {
            "signal": _to_int(prop_value("signal")),
            "battery": _to_int(prop_value("battery")),
            "csq": _to_int(prop_value("csq")),
            "voltage": _to_int(prop_value("voltage")),
            "heartbeat_hours": _to_int(prop_value("heartbeat")),
            "ambient_temperature": _to_float(prop_value("ambient_temperature")),
            "manned_unmanned": _to_int(prop_value("manned_unmanned")),
            "tamper_status": _to_int(prop_value("tamper_status")),
            "hardware": prop_value("hardware"),
            "iccid": prop_value("iccid"),
        },
        "attributes_updated_at": updated_at,
    }


async def _query_device(sn: str) -> dict:
    creds = load_platform_credentials()
    if not creds:
        return _unavailable(sn, "credentials_missing")
    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            token = await _get_token(client, creds)
            if not token:
                return _unavailable(sn, "auth_failed")

            device_body = await _api_get(client, creds, token, "/iot/device/get-by-sn", {"deviceSn": sn})
            data = device_body.get("data")
            if device_body.get("code") != 0 or not isinstance(data, dict):
                return _unavailable(sn, "device_not_found")

            props: dict = {}
            try:
                service_body = await _api_get(
                    client, creds, token, "/iot/device/service",
                    {"id": data.get("id"), "productId": data.get("productId") or "", "serviceType": 1},
                )
                for service in service_body.get("data") or []:
                    for entry in service.get("properties") or []:
                        identifier = entry.get("identifier")
                        if identifier:
                            props[identifier] = entry
            except (httpx.HTTPError, ValueError):
                # 属性接口失败不掩盖在线状态：返回基本在线信息 + 空属性
                logger.warning("phchn 设备属性查询失败：sn=%s", sn, exc_info=True)

            return _build_status(sn, data, props)
    except (httpx.HTTPError, ValueError):
        logger.warning("phchn 平台查询失败：sn=%s", sn, exc_info=True)
        return _unavailable(sn, "network_error")


async def fetch_device_status(sn: str, *, use_cache: bool = True) -> dict:
    """查询单台设备实时状态（带短缓存与降级，不抛异常）。"""
    now = time.time()
    if use_cache:
        cached = _status_cache.get(sn)
        if cached and cached[0] > now:
            return cached[1]

    result = await _query_device(sn)
    ttl = _STATUS_CACHE_TTL if result.get("available") else _STATUS_NEGATIVE_TTL
    _status_cache[sn] = (now + ttl, result)
    return result


async def fetch_devices_status(sns: list[str], *, use_cache: bool = True) -> dict[str, dict]:
    """并发查询多台设备状态，返回 sn → 状态。"""
    results = await asyncio.gather(*(fetch_device_status(sn, use_cache=use_cache) for sn in sns))
    return dict(zip(sns, results))