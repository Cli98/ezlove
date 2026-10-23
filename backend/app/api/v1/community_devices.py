"""社区端设备监控 API（硬件设备实时状态 + 关联老人视图）。

数据源：config/nbiot_devices.json（设备绑定）+ nbiot 解析（老人/社区归属）+
phchn 开放 API（实时状态，见 services/phchn_open_api.py）。零表结构依赖；
平台不可用时照常返回本地数据（占位降级，前端友好提示）。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_worker
from app.models.alert import Alert
from app.models.community import CommunityWorker
from app.services import nbiot, phchn_open_api

router = APIRouter(prefix="/community", tags=["community-devices"])


def _mask_sn(sn: str) -> str:
    """SN 中间脱敏：前 4 + **** + 后 4。"""
    return f"{sn[:4]}****{sn[-4:]}" if len(sn) > 8 else sn


def _mask_iccid(iccid: str | None) -> str | None:
    """ICCID 脱敏：保留前 8 后 4（运维换卡报号够用）。"""
    if not iccid or len(iccid) < 10:
        return iccid
    return f"{iccid[:8]}****{iccid[-4:]}"


def _type_label(device: dict) -> str:
    return phchn_open_api.DEVICE_TYPE_LABELS.get(device.get("device_type"), "设备")


async def _resolve_visible_devices(db: AsyncSession, worker: CommunityWorker) -> list[dict]:
    """加载配置内设备并解析绑定/归属；只返回当前社区可见的设备。

    可见性：绑定老人属于当前社区；或未绑定但归属社区（fallback）为当前社区。
    """
    registry, fallback_community = nbiot.load_registry()
    visible: list[dict] = []
    for sn, device in registry.items():
        elder, enrollment = await nbiot.resolve_device_elder(db, device)
        if enrollment is not None:
            if enrollment.community_id != worker.community_id:
                continue
            visible.append({"sn": sn, "device": device, "elder": elder, "enrollment": enrollment})
            continue

        community = await nbiot.resolve_fallback_community(db, fallback_community, device)
        if community is None or community.id != worker.community_id:
            continue
        visible.append({"sn": sn, "device": device, "elder": elder, "enrollment": None})
    return visible


@router.get("/devices")
async def list_devices(
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    visible = await _resolve_visible_devices(db, worker)
    status_map = await phchn_open_api.fetch_devices_status([item["sn"] for item in visible])

    # 关联老人的最近社区告警（列表页附带展示，按老人取最新一条）
    elder_ids = [item["enrollment"].elder_id for item in visible if item["enrollment"] is not None]
    latest_alert: dict = {}
    if elder_ids:
        rows = (
            await db.execute(
                select(Alert)
                .where(Alert.elder_id.in_(elder_ids), Alert.community_id == worker.community_id)
                .order_by(Alert.created_at.desc())
            )
        ).scalars().all()
        for alert in rows:
            latest_alert.setdefault(alert.elder_id, alert)

    devices = []
    for item in visible:
        device = item["device"]
        enrollment = item["enrollment"]
        elder = item["elder"]
        alert = latest_alert.get(enrollment.elder_id) if enrollment is not None else None
        devices.append(
            {
                "sn": item["sn"],
                "sn_masked": _mask_sn(item["sn"]),
                "label": device.get("label") or _type_label(device),
                "device_type": device.get("device_type"),
                "type_label": _type_label(device),
                "elder": {
                    "linked": enrollment is not None,
                    "id": str(enrollment.id) if enrollment is not None else None,
                    "name": (elder.nickname if elder is not None else None)
                    or device.get("elder_note")
                    or None,
                    "hint": None if enrollment is not None else "设备未绑定到已建档老人",
                },
                "platform": status_map[item["sn"]],
                "last_alert": (
                    {
                        "alert_type": alert.alert_type,
                        "alert_level": alert.alert_level,
                        "message": alert.message,
                        "is_resolved": alert.is_resolved,
                        "created_at": alert.created_at.isoformat(),
                    }
                    if alert is not None
                    else None
                ),
            }
        )

    attributes = [entry["platform"].get("attributes") or {} for entry in devices]
    summary = {
        "total": len(devices),
        "online": sum(1 for entry in devices if entry["platform"].get("platform_status") == 1),
        "offline": sum(
            1
            for entry in devices
            if entry["platform"].get("available") and entry["platform"].get("platform_status") in (0, 2)
        ),
        "low_battery": sum(1 for attr in attributes if attr.get("battery") == 0),
        "unlinked": sum(1 for entry in devices if not entry["elder"]["linked"]),
        "platform_available": any(entry["platform"].get("available") for entry in devices),
    }
    return {"summary": summary, "devices": devices}


@router.get("/devices/{sn}")
async def device_detail(
    sn: str,
    worker: CommunityWorker = Depends(get_current_worker),
    db: AsyncSession = Depends(get_db),
):
    registry, fallback_community = nbiot.load_registry()
    device = registry.get(sn)
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    elder, enrollment = await nbiot.resolve_device_elder(db, device)
    if enrollment is not None:
        if enrollment.community_id != worker.community_id:
            raise HTTPException(status_code=404, detail="设备不在当前社区")
    else:
        community = await nbiot.resolve_fallback_community(db, fallback_community, device)
        if community is None or community.id != worker.community_id:
            raise HTTPException(status_code=404, detail="设备不在当前社区")

    status = await phchn_open_api.fetch_device_status(sn, use_cache=False)  # 详情页取实时值

    # 最近告警：绑定老人按 elder_id；未绑定按工单文案中的 SN 尾号匹配
    alerts_query = select(Alert).where(Alert.community_id == worker.community_id)
    if elder is not None:
        alerts_query = alerts_query.where(Alert.elder_id == elder.id)
    else:
        alerts_query = alerts_query.where(Alert.message.like(f"%尾号{sn[-4:]}%"))
    alerts = (
        await db.execute(alerts_query.order_by(desc(Alert.created_at)).limit(10))
    ).scalars().all()

    risk = None
    if enrollment is not None:
        risk = {
            "score": enrollment.risk_score,
            "level": enrollment.risk_level,
            "calculated_at": enrollment.risk_calculated_at.isoformat()
            if enrollment.risk_calculated_at
            else None,
        }

    attributes = dict(status.get("attributes") or {})
    attributes["iccid"] = _mask_iccid(attributes.get("iccid"))

    return {
        "sn": sn,
        "sn_masked": _mask_sn(sn),
        "label": device.get("label") or _type_label(device),
        "device_type": device.get("device_type"),
        "type_label": _type_label(device),
        "elder": {
            "linked": enrollment is not None,
            "id": str(enrollment.id) if enrollment is not None else None,
            "name": (elder.nickname if elder is not None else None)
            or device.get("elder_note")
            or None,
        },
        "risk": risk,
        "platform": {**status, "attributes": attributes},
        "alerts": [
            {
                "id": str(alert.id),
                "alert_type": alert.alert_type,
                "alert_level": alert.alert_level,
                "message": alert.message,
                "is_resolved": alert.is_resolved,
                "created_at": alert.created_at.isoformat(),
            }
            for alert in alerts
        ],
    }