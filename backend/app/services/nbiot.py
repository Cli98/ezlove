"""NB-IoT 硬件事件接入（phchn 云平台 HTTP 推送）。

平台推送报文（messageType=1，固定返回 HTTP 200）：
    {"messageType": 1,
     "message": {"deviceSn": "358800048678347", "event": 1, "eventType": 0,
                 "content": "紧急报警", "zone": null, "childName": null,
                 "alarmTime": 1751623919507},
     "timestamp": 1751623919982}

事件映射（对接手册《API字段对接.md》）：
    button_press          = (event 1, eventType 0)   → 紧急告警（家属 + 社区）
    battery_low           = (event 5, eventType 0)   → 电量低提醒（社区）
    bathroom_motion_start = (event 2, eventType 20)  → 红外检测到活动（写社区时间线）
    bathroom_motion_end   = (event 2, eventType 19)  → 红外暂无活动（写社区时间线）

红外只记录“有人/无人”状态，不采集影像与声音，社区端展示为日常活动记录。

设备与老人绑定：backend/config/nbiot_devices.json（低频静态数据，避免引入表结构
迁移——发布通道不执行 Alembic 迁移）。绑定锚点唯一：elder_record_id（社区老人
档案 ID，管理后台老人详情页 URL 中的 UUID）；昵称/手机号等字符串不参与匹配，
避免重名误绑。未绑定的设备仍会落一条社区级告警，提示工作人员核实设备归属。

幂等：平台可能重试推送。进程内按 (sn, event, eventType, alarmTime) 去重 6 小时；
落库前再按业务窗口去重（一键报警 10 分钟、电量低 24 小时），避免重启后重复告警。
"""
import json
import logging
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alert import Alert
from app.models.care_relation import CareRelation
from app.models.community import Community, CommunityElder
from app.models.community_event import CommunityEvent
from app.models.user import User

logger = logging.getLogger("ezlove.nbiot")

# 事件映射（数值来自对接手册，勿随意调整）
EVENT_BUTTON_PRESS = (1, 0)
EVENT_BATTERY_LOW = (5, 0)
EVENT_MOTION_START = (2, 20)
EVENT_MOTION_END = (2, 19)
EVENT_DOOR_OPEN = (3, 2)
EVENT_DOOR_CLOSE = (4, 2)

ALERT_TYPE_SOS = "sos"
ALERT_TYPE_BATTERY = "device_battery"

# 业务去重窗口：同一老人在窗口内只落一条同类告警（重试/连按不刷屏）
SOS_DEDUPE_WINDOW = timedelta(minutes=10)
BATTERY_DEDUPE_WINDOW = timedelta(hours=24)
DOOR_EVENT_DEDUPE_WINDOW = timedelta(seconds=60)
MOTION_EVENT_DEDUPE_WINDOW = timedelta(seconds=60)

# 进程内精确去重（同一 alarmTime 的重复推送），重启后由落库窗口兜底
_SEEN_TTL_SECONDS = 6 * 3600
_SEEN_MAX = 5000
_seen: "OrderedDict[str, float]" = OrderedDict()

DEFAULT_DEVICES_FILE = Path(__file__).resolve().parents[2] / "config" / "nbiot_devices.json"
_registry_cache: dict = {"mtime": None, "devices": {}, "fallback_community": ""}


def _devices_path() -> Path:
    if settings.NBIOT_DEVICES_FILE:
        return Path(settings.NBIOT_DEVICES_FILE)
    return DEFAULT_DEVICES_FILE


def load_registry(path: Path | None = None) -> tuple[dict, str]:
    """读取设备绑定配置；按 mtime 缓存，改文件后无需重启（部署仍会重建容器）。"""
    file_path = path or _devices_path()
    try:
        mtime = file_path.stat().st_mtime
    except OSError:
        logger.warning("未找到 NB-IoT 设备绑定配置：%s", file_path)
        return {}, ""

    if _registry_cache["mtime"] != mtime:
        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.exception("读取 NB-IoT 设备绑定配置失败：%s", file_path)
            return {}, ""
        devices = {}
        for item in raw.get("devices") or []:
            sn = str(item.get("sn") or "").strip()
            if sn:
                devices[sn] = item
        _registry_cache.update(
            mtime=mtime,
            devices=devices,
            fallback_community=str(raw.get("fallback_community") or "").strip(),
        )
        logger.info("已加载 NB-IoT 设备绑定 %d 台", len(devices))
    return _registry_cache["devices"], _registry_cache["fallback_community"]


def reset_dedup_cache() -> None:
    """测试用：清空进程内精确去重缓存。"""
    _seen.clear()


def _is_duplicate(key: str) -> bool:
    now = time.time()
    while _seen and next(iter(_seen.values())) < now - _SEEN_TTL_SECONDS:
        _seen.popitem(last=False)
    if key in _seen and now - _seen[key] < _SEEN_TTL_SECONDS:
        _seen.move_to_end(key)
        return True
    _seen[key] = now
    if len(_seen) > _SEEN_MAX:
        _seen.popitem(last=False)
    return False


async def handle_push(db: AsyncSession, payload: dict, devices: dict | None = None) -> dict:
    """处理一条平台推送；devices 仅测试注入，生产走配置文件。"""
    if str(payload.get("messageType")) != "1":
        logger.info("忽略非设备事件推送：messageType=%s", payload.get("messageType"))
        return {"accepted": False, "reason": "not_device_event"}

    message = payload.get("message") or {}
    sn = str(message.get("deviceSn") or "").strip()
    try:
        event = int(message.get("event"))
        event_type = int(message.get("eventType"))
    except (TypeError, ValueError):
        logger.warning("推送事件字段非法：deviceSn=%s message=%s", sn, message)
        return {"accepted": False, "reason": "invalid_event"}

    if devices is None:
        devices, fallback_community = load_registry()
    else:
        fallback_community = ""
    device = devices.get(sn)
    if not device:
        logger.warning("收到未登记设备的推送：sn=%s event=%s eventType=%s", sn, event, event_type)
        return {"accepted": False, "reason": "unknown_device"}

    dedup_key = f"{sn}:{event}:{event_type}:{message.get('alarmTime') or ''}"
    if _is_duplicate(dedup_key):
        logger.info("重复推送已忽略：%s", dedup_key)
        return {"accepted": True, "duplicate": True, "created": 0}

    key = (event, event_type)
    if key == EVENT_BUTTON_PRESS:
        created = await _handle_sos(db, device, message, fallback_community)
    elif key == EVENT_BATTERY_LOW:
        created = await _handle_battery_low(db, device, message, fallback_community)
    elif key in (EVENT_MOTION_START, EVENT_MOTION_END):
        created = await _handle_motion_event(db, device, event_type)
    elif key in (EVENT_DOOR_OPEN, EVENT_DOOR_CLOSE):
        created = await _handle_door_event(db, device, event)
    else:
        logger.info("未处理的设备事件：sn=%s event=%s eventType=%s", sn, event, event_type)
        created = 0

    return {"accepted": True, "created": created}


async def resolve_device_elder(db: AsyncSession, device: dict) -> tuple[User | None, CommunityElder | None]:
    """解析设备绑定的老人与社区档案（设备监控页复用）。

    唯一锚点：elder_record_id（社区老人档案 ID，管理后台老人详情页 URL 中的 UUID）。
    昵称/手机号等字符串不参与匹配，避免重名误绑。
    """
    record_id = str(device.get("elder_record_id") or "").strip()
    if not record_id:
        return None, None
    try:
        record_uuid = uuid.UUID(record_id)
    except ValueError:
        logger.warning("设备配置 elder_record_id 非法（sn=%s）：%s", device.get("sn"), record_id)
        return None, None

    enrollment = (await db.execute(
        select(CommunityElder).where(CommunityElder.id == record_uuid).limit(1)
    )).scalar_one_or_none()
    if enrollment is None:
        return None, None
    elder = await db.get(User, enrollment.elder_id)
    return elder, enrollment


async def resolve_fallback_community(
    db: AsyncSession, fallback_community: str, device: dict
) -> Community | None:
    """未绑定老人时确定告警归属社区：配置名 > 设备级社区名 > 全库唯一社区。"""
    name = fallback_community or str(device.get("community_name") or "").strip()
    if name:
        community = (await db.execute(
            select(Community).where(Community.name == name).limit(1)
        )).scalar_one_or_none()
        if community is not None:
            return community

    communities = (await db.execute(select(Community).limit(2))).scalars().all()
    return communities[0] if len(communities) == 1 else None


async def _recent_alert_exists(
    db: AsyncSession,
    *,
    alert_type: str,
    window: timedelta,
    elder_id=None,
    community_id=None,
) -> bool:
    stmt = select(Alert.id).where(
        Alert.alert_type == alert_type,
        Alert.is_resolved == False,  # noqa: E712
        Alert.created_at >= datetime.now() - window,
    )
    if elder_id is not None:
        stmt = stmt.where(Alert.elder_id == elder_id)
    elif community_id is not None:
        stmt = stmt.where(Alert.community_id == community_id)
    else:
        return False
    return (await db.execute(stmt.limit(1))).scalar_one_or_none() is not None


async def _handle_sos(
    db: AsyncSession, device: dict, message: dict, fallback_community: str
) -> int:
    elder, enrollment = await resolve_device_elder(db, device)
    label = str(device.get("label") or "紧急报警设备")
    zone = str(message.get("zone") or "").strip()
    content = str(message.get("content") or "").strip()
    now = datetime.now()

    if elder is None:
        community = await resolve_fallback_community(db, fallback_community, device)
        if community is None:
            logger.error("设备 %s 未绑定老人且无法确定社区，报警未落库", device.get("sn"))
            return 0
        if await _recent_alert_exists(
            db, alert_type=ALERT_TYPE_SOS, window=SOS_DEDUPE_WINDOW,
            community_id=community.id,
        ):
            return 0
        db.add(Alert(
            elder_id=None,
            community_id=community.id,
            alert_type=ALERT_TYPE_SOS,
            alert_level="urgent",
            message=(
                f"未绑定设备「{label}」（SN尾号{str(device.get('sn'))[-4:]}）触发紧急报警，"
                "请核实设备归属并绑定老人"
            ),
            trigger_rule="device_button_press",
            response_deadline=now + timedelta(minutes=30),
        ))
        await db.flush()
        return 1

    if await _recent_alert_exists(
        db, alert_type=ALERT_TYPE_SOS, window=SOS_DEDUPE_WINDOW, elder_id=elder.id,
    ):
        return 0

    elder_name = elder.nickname or "老人"
    location = f"（{zone}）" if zone else ""
    detail = f"，{content}" if content and content not in label else ""
    text = f"{elder_name} 的{label}{location}触发紧急报警{detail}，请尽快联系确认安全"

    created = 0
    relations = (await db.execute(
        select(CareRelation).where(
            CareRelation.elder_user_id == elder.id,
            CareRelation.status == "active",
        )
    )).scalars().all()
    for relation in relations:
        db.add(Alert(
            care_relation_id=relation.id,
            elder_id=elder.id,
            alert_type=ALERT_TYPE_SOS,
            alert_level="urgent",
            message=text,
            trigger_rule="device_button_press",
        ))
        await db.flush()
        created += 1
        try:
            from app.services.notification import notify_family_device_alert
            await notify_family_device_alert(db, relation.id, elder_name, label)
        except Exception:
            logger.exception("发送设备紧急告警家属通知失败")

    if enrollment is not None:
        alert = Alert(
            elder_id=elder.id,
            community_id=enrollment.community_id,
            alert_type=ALERT_TYPE_SOS,
            alert_level="urgent",
            message=text,
            trigger_rule="device_button_press",
            assigned_worker_id=enrollment.assigned_worker_id,
            response_deadline=now + timedelta(minutes=30),
        )
        db.add(alert)
        await db.flush()
        created += 1
        try:
            from app.services.notification import notify_worker_alert
            await notify_worker_alert(db, alert.id)
        except Exception:
            logger.exception("发送设备紧急告警网格员通知失败")

    logger.info(
        "设备紧急告警已落库：sn=%s elder=%s 家属告警=%d 社区告警=%d",
        device.get("sn"), elder.id, len(relations), 1 if enrollment else 0,
    )
    return created


async def _handle_battery_low(
    db: AsyncSession, device: dict, message: dict, fallback_community: str
) -> int:
    elder, enrollment = await resolve_device_elder(db, device)
    label = str(device.get("label") or "设备")

    community_id = enrollment.community_id if enrollment is not None else None
    if community_id is None:
        community = await resolve_fallback_community(db, fallback_community, device)
        if community is None:
            logger.error("设备 %s 电量低但无法确定社区，提醒未落库", device.get("sn"))
            return 0
        community_id = community.id

    if await _recent_alert_exists(
        db,
        alert_type=ALERT_TYPE_BATTERY,
        window=BATTERY_DEDUPE_WINDOW,
        elder_id=elder.id if elder is not None else None,
        community_id=community_id,
    ):
        return 0

    subject = (elder.nickname if elder is not None else None) or (
        f"SN尾号{str(device.get('sn'))[-4:]}"
    )
    alert = Alert(
        elder_id=elder.id if elder is not None else None,
        community_id=community_id,
        alert_type=ALERT_TYPE_BATTERY,
        alert_level="warning",
        message=f"{subject} 的{label}电量低，请提醒更换电池",
        trigger_rule="device_battery_low",
        assigned_worker_id=enrollment.assigned_worker_id if enrollment is not None else None,
    )
    db.add(alert)
    await db.flush()

    try:
        from app.services.notification import notify_worker_alert
        await notify_worker_alert(db, alert.id)
    except Exception:
        logger.exception("发送设备电量提醒失败")

    logger.info("设备电量低提醒已落库：sn=%s", device.get("sn"))
    return 1


async def _handle_door_event(db: AsyncSession, device: dict, event: int) -> int:
    """门磁开合写入社区事件表，供老人详情时间线展示。

    门磁开合属于生活信号，不产生告警；未绑定老人时跳过。
    同一老人同一状态 60 秒内只记一条，避免平台连续上报刷屏。
    """
    elder, enrollment = await resolve_device_elder(db, device)
    if elder is None or enrollment is None:
        logger.info("门磁事件未绑定老人，跳过时间线：sn=%s event=%s", device.get("sn"), event)
        return 0

    is_open = event == EVENT_DOOR_OPEN[0]
    event_type = "door_open" if is_open else "door_close"
    label = "门磁打开" if is_open else "门磁关闭"

    recent = (await db.execute(
        select(CommunityEvent.id).where(
            CommunityEvent.elder_id == elder.id,
            CommunityEvent.event_type == event_type,
            CommunityEvent.created_at >= datetime.now() - DOOR_EVENT_DEDUPE_WINDOW,
        ).limit(1)
    )).scalar_one_or_none()
    if recent is not None:
        return 0

    db.add(CommunityEvent(
        community_id=enrollment.community_id,
        elder_id=elder.id,
        event_type=event_type,
        source="device",
        description=f"{label}（{device.get('label') or '门磁传感器'}）",
        severity="info",
    ))
    await db.flush()
    logger.info("门磁事件已写入时间线：sn=%s event=%s elder=%s", device.get("sn"), event, elder.id)
    return 1


async def _handle_motion_event(db: AsyncSession, device: dict, event_type: int) -> int:
    """红外有人/无人写入社区时间线。

    只记录“有人/无人”二态，不采集影像与声音；同一老人同一状态 60 秒内只记一条，
    避免平台连续上报刷屏。未绑定老人时跳过。
    """
    elder, enrollment = await resolve_device_elder(db, device)
    if elder is None or enrollment is None:
        logger.info("红外事件未绑定老人，跳过时间线：sn=%s eventType=%s", device.get("sn"), event_type)
        return 0

    is_motion = event_type == EVENT_MOTION_START[1]
    event_key = "motion_start" if is_motion else "motion_end"
    label = "红外检测到活动" if is_motion else "红外暂无活动"

    recent = (await db.execute(
        select(CommunityEvent.id).where(
            CommunityEvent.elder_id == elder.id,
            CommunityEvent.event_type == event_key,
            CommunityEvent.created_at >= datetime.now() - MOTION_EVENT_DEDUPE_WINDOW,
        ).limit(1)
    )).scalar_one_or_none()
    if recent is not None:
        return 0

    db.add(CommunityEvent(
        community_id=enrollment.community_id,
        elder_id=elder.id,
        event_type=event_key,
        source="device",
        description=f"{label}（{device.get('label') or '红外探测器'}）",
        severity="info",
    ))
    await db.flush()
    logger.info("红外事件已写入时间线：sn=%s eventType=%s elder=%s", device.get("sn"), event_type, elder.id)
    return 1
