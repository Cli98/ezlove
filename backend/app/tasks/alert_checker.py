import logging
import uuid
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, or_, func, desc, update

from app.config import settings
from app.database import async_session
from app.models.care_relation import CareRelation
from app.models.care_moment import CareMoment
from app.models.view_event import ViewEvent
from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.community import Community, CommunityElder
from app.models.canteen import CanteenRecord
from app.models.community_event import CommunityEvent
from app.models.user import User
from app.services import alert_rules as rules_service
from app.services import phchn_open_api
from app.services.nbiot import load_registry

logger = logging.getLogger("ezlove.alert_checker")
scheduler = AsyncIOScheduler()

# 老人姓名缓存，避免同一轮检测中重复查询 User 表
_name_cache: dict = {}

# 构成"老人有活动迹象"的社区事件类型白名单（P3 §3.4 契约）：
# 人工信号 + 设备真实活动（门磁开合、红外检测到有人）；红外"无人"不构成活动迹象。
# 排除 absent（负向信号）与 other（含告警同步事件与备注，保守不算信号）；
# source="alert"（告警同步产生的事件）另行排除——修复"同步告警事件压制晨检"（OP-1）
SIGNAL_EVENT_TYPES = frozenset({
    "visit", "manual_confirm", "door_open", "door_close", "motion_start",
})

# 设备类型（backend/config/nbiot_devices.json 的 device_type）
DOOR_DEVICE_TYPE = 2
MOTION_DEVICE_TYPE = 12

# 设备离线判定：超过该时长仍不在线 → 暂停该设备的活跃类预警（白老师 2026-10-29：设备坏了要主动"断电"）
DEVICE_OFFLINE_HOURS = max(1, settings.DEVICE_OFFLINE_HOURS)
# 进程内离线起始时间（sn → 离线起点）；重启后由下一轮 device_offline_check 重建
_offline_since: dict[str, datetime] = {}

# 关怀规则阈值与生效时段均存于 alert_rules（管理后台可改），
# 内置默认值见 services/alert_rules.py 的 DEFAULTS 与 RULE_DEFAULTS。
_rule_cache: dict = {}


async def _rule_entry(db, community_id, rule_type: str, care_level: str) -> dict | None:
    """取某社区某规则的等级配置（一轮任务内缓存，避免重复查库）。"""
    key = (community_id, rule_type)
    if key not in _rule_cache:
        _rule_cache[key] = await rules_service.load_rule_config(db, community_id, rule_type)
    return _rule_cache[key].get(care_level)


def _window(params: dict, default: tuple[int, int]) -> tuple[int, int]:
    """解析 check_hours=[起, 止)，非法时回退默认时段。"""
    value = params.get("check_hours")
    if isinstance(value, list) and len(value) == 2:
        try:
            return int(value[0]), int(value[1])
        except (TypeError, ValueError):
            pass
    return default


def _hours_param(params: dict, key: str, default: int) -> int:
    try:
        value = int(params.get(key, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _hour_of_day(params: dict, key: str, default: int) -> int:
    """钟点参数（0–23，0 表示零点）——不能复用 _hours_param，它会把 0 当非法值回退。"""
    try:
        value = int(params.get(key, default))
    except (TypeError, ValueError):
        return default
    return value if 0 <= value <= 23 else default


# ── Job 1: 多维度规则引擎（社区侧） ──

async def run_alert_rules():
    _name_cache.clear()
    async with async_session() as db:
        communities = (await db.execute(select(Community.id))).scalars().all()
        now = datetime.now()

        for cid in communities:
            rules = (await db.execute(
                select(AlertRule).where(
                    AlertRule.community_id == cid,
                    AlertRule.enabled == True,
                )
            )).scalars().all()

            if not rules:
                continue

            for rule in rules:
                elders = (await db.execute(
                    select(CommunityElder)
                    .where(
                        CommunityElder.community_id == cid,
                        CommunityElder.care_level == rule.care_level,
                    )
                )).scalars().all()

                for elder in elders:
                    triggered = False
                    message = ""

                    if rule.rule_type == "unread_timeout":
                        triggered, message = await _check_unread(db, elder, rule.threshold_hours, now)
                    elif rule.rule_type == "canteen_absence":
                        triggered, message = await _check_canteen(db, elder, cid, rule.threshold_hours, now)
                    elif rule.rule_type == "no_signal":
                        triggered, message = await _check_no_signal(db, elder, cid, rule.threshold_hours, now)

                    if not triggered:
                        continue

                    existing = await db.execute(
                        select(Alert).where(
                            Alert.elder_id == elder.elder_id,
                            Alert.trigger_rule == rule.rule_type,
                            Alert.is_resolved == False,
                            Alert.created_at >= now - timedelta(hours=24),
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    severity = {"A": "urgent", "B": "warning", "C": "info"}.get(rule.care_level, "info")
                    alert = Alert(
                        elder_id=elder.elder_id,
                        community_id=cid,
                        # 本引擎只跑 unread_timeout / canteen_absence / no_signal（均 ≤16 字符）；
                        # 新增长名规则类型时 alert_type 要映射短名，否则撞 varchar(16)
                        alert_type=rule.rule_type,
                        alert_level=severity,
                        message=message,
                        trigger_rule=rule.rule_type,
                        assigned_worker_id=elder.assigned_worker_id,
                        response_deadline=now + timedelta(minutes=30),
                    )
                    db.add(alert)
                    await db.flush()

                    try:
                        from app.services.notification import notify_worker_alert
                        await notify_worker_alert(db, alert.id)
                    except Exception:
                        logger.exception("发送网格员告警通知失败")

        await db.commit()
    logger.info("社区侧规则引擎检测完成")


async def _check_unread(db, elder, threshold_hours, now) -> tuple[bool, str]:
    cutoff = now - timedelta(hours=threshold_hours)
    # 查找截止时间后发给该老人的牵挂
    moments = (await db.execute(
        select(CareMoment).where(
            CareMoment.elder_id == elder.elder_id,
            CareMoment.created_at >= cutoff,
        )
    )).scalars().all()

    if not moments:
        return False, ""

    # 批量查询这些牵挂的查看记录，避免逐条查询 N+1
    moment_ids = [m.id for m in moments]
    viewed = (await db.execute(
        select(ViewEvent.moment_id)
        .where(
            ViewEvent.moment_id.in_(moment_ids),
            ViewEvent.viewer_id == elder.elder_id,
        )
        .distinct()
    )).scalars().all()

    if viewed:
        return False, ""

    elder_name = await _get_elder_name(db, elder.elder_id)
    return True, f"{elder_name} 超过{threshold_hours}小时未查看牵挂内容"


async def _check_canteen(db, elder, community_id, threshold_hours, now) -> tuple[bool, str]:
    cutoff = now - timedelta(hours=threshold_hours)
    records = (await db.execute(
        select(CanteenRecord).where(
            CanteenRecord.community_id == community_id,
            CanteenRecord.parse_status == "success",
            CanteenRecord.created_at >= cutoff,
        ).order_by(desc(CanteenRecord.created_at))
    )).scalars().all()

    if not records:
        return False, ""

    elder_id_str = str(elder.elder_id)
    absent_count = 0
    for rec in records:
        attendees = (rec.parsed_data or {}).get("attendees", [])
        for att in attendees:
            if att.get("elder_id") == elder_id_str and att.get("present") is False:
                absent_count += 1

    meals_threshold = max(1, threshold_hours // 6)
    if absent_count < meals_threshold:
        return False, ""

    elder_name = await _get_elder_name(db, elder.elder_id)
    return True, f"{elder_name} 连续{absent_count}餐未到食堂就餐"


async def _check_no_signal(db, elder, community_id, threshold_hours, now) -> tuple[bool, str]:
    cutoff = now - timedelta(hours=threshold_hours)

    # 查看记录
    view = (await db.execute(
        select(ViewEvent.viewed_at).where(
            ViewEvent.viewer_id == elder.elder_id,
            ViewEvent.viewed_at >= cutoff,
        ).limit(1)
    )).scalar_one_or_none()
    if view:
        return False, ""

    # 食堂出勤
    canteen = (await db.execute(
        select(CanteenRecord).where(
            CanteenRecord.community_id == community_id,
            CanteenRecord.parse_status == "success",
            CanteenRecord.created_at >= cutoff,
        )
    )).scalars().all()

    elder_id_str = str(elder.elder_id)
    for rec in canteen:
        for att in (rec.parsed_data or {}).get("attendees", []):
            if att.get("elder_id") == elder_id_str and att.get("present") is True:
                return False, ""

    # 社区事件：仅真实活动信号（白名单类型且非告警同步产生，OP-1）
    event = (await db.execute(
        select(CommunityEvent.id).where(
            CommunityEvent.elder_id == elder.elder_id,
            CommunityEvent.created_at >= cutoff,
            CommunityEvent.event_type.in_(SIGNAL_EVENT_TYPES),
            CommunityEvent.source != "alert",
        ).limit(1)
    )).scalar_one_or_none()
    if event:
        return False, ""

    elder_name = await _get_elder_name(db, elder.elder_id)
    return True, f"{elder_name} 超过{threshold_hours}小时无任何活动信号"


async def _get_elder_name(db, elder_user_id) -> str:
    if elder_user_id in _name_cache:
        return _name_cache[elder_user_id]
    result = await db.execute(select(User.nickname).where(User.id == elder_user_id))
    name = result.scalar_one_or_none()
    name = name or "未知老人"
    _name_cache[elder_user_id] = name
    return name


# ── Job 2: 家属侧未读告警（§3.8 修复口径：跨天盲区 + 查看即活跃 + 24h 滚动去重 + 冷启动过滤） ──

async def _iter_unread_alert_candidates(db, cold_start_hours: int) -> list:
    """未读告警候选集判定链（P3 §3.8 步骤 1-5）。

    正式调度（check_unread_alerts）与 scripts/dry_run_family_check.py --readonly
    预估统计共用本实现，防双份漂移；只做查询判定，不做 db.add/commit、
    不发通知——readonly 调用方仅对返回值计数。

    返回 [(relation, earliest_unread_moment, hours_since), ...]：
    - 步骤 1：最早未读牵挂 E1——NOT EXISTS 查看子查询，不限今日
      （跨天盲区根因：原实现限定 created_at >= 今日零点）
    - 步骤 2：冷启动过滤——cold_start_hours > 0 且 E1 早于 now-N小时 则跳过
    - 步骤 3：查看即活跃——老人在 E1 产生之后有过查看行为则跳过
    - 步骤 4：阈值——hours_since < relation.alert_threshold 跳过
    - 步骤 5：24h 滚动去重——近 24h 已有未解决 unread 告警则跳过
    """
    now = datetime.now()
    result = await db.execute(
        select(CareRelation).where(
            CareRelation.status == "active",
            or_(
                CareRelation.alert_paused_until.is_(None),
                CareRelation.alert_paused_until < now,
            ),
        )
    )
    relations = result.scalars().all()

    candidates = []
    for rel in relations:
        # 步骤 1：最早未读牵挂（全部历史，不限今日——OP-6）
        earliest = (await db.execute(
            select(CareMoment).where(
                CareMoment.sender_id == rel.family_user_id,
                CareMoment.elder_id == rel.elder_user_id,
                ~select(ViewEvent.id).where(
                    ViewEvent.moment_id == CareMoment.id,
                    ViewEvent.viewer_id == rel.elder_user_id,
                ).exists(),
            ).order_by(CareMoment.created_at.asc()).limit(1)
        )).scalar_one_or_none()
        if earliest is None:
            continue

        # 步骤 2：冷启动过滤（默认 0 不启用，R3 冷启动上限）
        if cold_start_hours > 0 and earliest.created_at < now - timedelta(hours=cold_start_hours):
            continue

        # 步骤 3：查看即活跃——老人在最早未读产生之后有过查看行为
        last_view = (await db.execute(
            select(func.max(ViewEvent.viewed_at))
            .join(CareMoment, ViewEvent.moment_id == CareMoment.id)
            .where(
                CareMoment.sender_id == rel.family_user_id,
                CareMoment.elder_id == rel.elder_user_id,
                ViewEvent.viewer_id == rel.elder_user_id,
            )
        )).scalar_one_or_none()
        if last_view is not None and last_view >= earliest.created_at:
            continue

        # 步骤 4：阈值
        hours_since = (now - earliest.created_at).total_seconds() / 3600
        if hours_since < rel.alert_threshold:
            continue

        # 步骤 5：24h 滚动去重（原"今日零点起"改滚动窗口，OP-6）
        existing = await db.execute(
            select(Alert.id).where(
                Alert.care_relation_id == rel.id,
                Alert.alert_type == "unread",
                Alert.is_resolved == False,
                Alert.created_at >= now - timedelta(hours=24),
            ).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            continue

        candidates.append((rel, earliest, hours_since))
    return candidates


async def check_unread_alerts():
    _name_cache.clear()
    async with async_session() as db:
        # 判定链与 --readonly 预估共用 _iter_unread_alert_candidates（P3 §3.8 工程化落点）
        candidates = await _iter_unread_alert_candidates(db, settings.ALERT_COLD_START_UNREAD_HOURS)

        for rel, earliest_moment, hours_since in candidates:
            # 步骤 6：级别（≥48h urgent / ≥24h warning / 其余 info）
            level = "info"
            if hours_since >= 48:
                level = "urgent"
            elif hours_since >= 24:
                level = "warning"

            # 步骤 7：INSERT 不传 created_at——走模型 Python default（naive 本地，AC-7.8）
            message = f"已发送的牵挂内容超过{int(hours_since)}小时未被查看，建议联系确认"
            alert = Alert(
                care_relation_id=rel.id,
                alert_type="unread",
                alert_level=level,
                message=message,
                trigger_rule="unread_timeout",
            )
            db.add(alert)
            await db.flush()

            # 步骤 8：通知（try/except 保留；ALERT_NOTIFY_ENABLED=false 时函数内部静默）
            try:
                from app.services.notification import notify_family_unread
                elder_name = await _get_elder_name(db, rel.elder_user_id)
                await notify_family_unread(db, rel.id, elder_name, int(hours_since))
            except Exception:
                logger.exception("发送未读通知失败")

        await db.commit()
    logger.info("家属侧告警检测完成")


# ── Job 3: 同步家属告警到社区事件 ──

async def sync_all_communities():
    from app.services.community_event import sync_family_alerts_to_community

    async with async_session() as db:
        result = await db.execute(select(Community.id))
        community_ids = result.scalars().all()
        for cid in community_ids:
            try:
                await sync_family_alerts_to_community(db, cid)
            except Exception:
                logger.exception(f"同步社区 {cid} 告警失败")
        await db.commit()
    logger.info("社区告警同步完成")


# ── Job 4: 升级超期未响应告警 ──

async def check_escalations():
    async with async_session() as db:
        now = datetime.now()
        result = await db.execute(
            select(Alert).where(
                Alert.is_resolved == False,
                Alert.response_deadline.isnot(None),
                Alert.response_deadline < now,
                Alert.escalation_level < 2,
            )
        )
        alerts = result.scalars().all()

        for alert in alerts:
            alert.escalation_level += 1
            if alert.escalation_level == 1:
                alert.response_deadline = now + timedelta(hours=1)
            logger.info(f"告警 {alert.id} 升级至 level {alert.escalation_level}")

        await db.commit()
    logger.info(f"升级检查完成，处理 {len(alerts)} 条")


# ── Job 5: 批量重算风险分数（Iter3 实现，此处占位） ──

async def recalculate_risk_scores():
    from app.services.risk_scoring import recalculate_all

    async with async_session() as db:
        communities = (await db.execute(select(Community.id))).scalars().all()
        total = 0
        for cid in communities:
            count = await recalculate_all(db, cid)
            total += count
        await db.commit()
    logger.info(f"风险评分重算完成，共计算 {total} 位老人")


# ── Job 6: 晨间静默检查（每天 8:00）──

async def morning_silence_check():
    """A/B 类老人如果昨天下午到现在无任何信号，产生晨间预警"""
    _name_cache.clear()
    async with async_session() as db:
        now = datetime.now()
        communities = (await db.execute(select(Community.id))).scalars().all()
        total_alerts = 0

        for cid in communities:
            elders = (await db.execute(
                select(CommunityElder).where(
                    CommunityElder.community_id == cid,
                    CommunityElder.care_level.in_(["A", "B"]),
                )
            )).scalars().all()

            for elder in elders:
                threshold_hours = 18 if elder.care_level == "A" else 24
                cutoff = now - timedelta(hours=threshold_hours)

                # 检查 3 个来源是否有活动信号
                view = (await db.execute(
                    select(ViewEvent.viewed_at).where(
                        ViewEvent.viewer_id == elder.elder_id,
                        ViewEvent.viewed_at >= cutoff,
                    ).limit(1)
                )).scalar_one_or_none()
                if view:
                    continue

                # 社区事件：仅真实活动信号（白名单类型且非告警同步产生，
                # 修复"同步告警事件压制晨检"，OP-1）
                event = (await db.execute(
                    select(CommunityEvent.id).where(
                        CommunityEvent.elder_id == elder.elder_id,
                        CommunityEvent.created_at >= cutoff,
                        CommunityEvent.event_type.in_(SIGNAL_EVENT_TYPES),
                        CommunityEvent.source != "alert",
                    ).limit(1)
                )).scalar_one_or_none()
                if event:
                    continue

                elder_id_str = str(elder.elder_id)
                canteen_found = False
                canteen_recs = (await db.execute(
                    select(CanteenRecord).where(
                        CanteenRecord.community_id == cid,
                        CanteenRecord.parse_status == "success",
                        CanteenRecord.created_at >= cutoff,
                    )
                )).scalars().all()
                for rec in canteen_recs:
                    for att in (rec.parsed_data or {}).get("attendees", []):
                        if att.get("elder_id") == elder_id_str and att.get("present") is True:
                            canteen_found = True
                            break
                    if canteen_found:
                        break
                if canteen_found:
                    continue

                # 检查是否已有未解决的同类关怀告警
                existing = await db.execute(
                    select(Alert).where(
                        Alert.elder_id == elder.elder_id,
                        Alert.trigger_rule.in_(("morning_silence", "stillness", "no_activity_trace")),
                        Alert.is_resolved == False,
                        Alert.created_at >= now - timedelta(hours=24),
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                elder_name = await _get_elder_name(db, elder.elder_id)
                severity = "urgent" if elder.care_level == "A" else "warning"
                alert = Alert(
                    elder_id=elder.elder_id,
                    community_id=cid,
                    alert_type="morning_silence",
                    alert_level=severity,
                    message=f"{elder_name} 超过{threshold_hours}小时无活动信号（晨间检查）",
                    trigger_rule="morning_silence",
                    assigned_worker_id=elder.assigned_worker_id,
                    response_deadline=now + timedelta(minutes=30),
                )
                db.add(alert)
                total_alerts += 1

        await db.commit()
    logger.info(f"晨间静默检查完成，产生 {total_alerts} 条预警")


# ── Job 7: 红外短时静止预警（默认每小时，阈值与生效时段可配）──

async def _elder_records_by_device_type(db, device_type: int) -> list[tuple[CommunityElder, str]]:
    """按设备类型取已绑定档案，返回 (档案, 设备 SN)：SN 用于判断设备是否在线。"""
    devices, _ = load_registry()
    record_to_sn: dict[uuid.UUID, str] = {}
    for sn, item in devices.items():
        if int(item.get("device_type") or 0) != device_type:
            continue
        try:
            record_id = uuid.UUID(str(item.get("elder_record_id") or "").strip())
        except ValueError:
            continue
        record_to_sn.setdefault(record_id, str(sn))
    if not record_to_sn:
        return []
    result = await db.execute(select(CommunityElder).where(CommunityElder.id.in_(record_to_sn)))
    return [(record, record_to_sn[record.id]) for record in result.scalars().all()]


def _is_device_offline(sn: str) -> bool:
    """设备离线超阈值 → 暂停该设备的活跃类预警（不等同于老人没活动）。"""
    since = _offline_since.get(sn)
    return since is not None and datetime.now() - since >= timedelta(hours=DEVICE_OFFLINE_HOURS)


async def _canteen_last_seen(db, elder_id) -> datetime | None:
    """食堂就餐也算活动信号（白老师 2026-10-29：只看硬件活跃，但走访/就餐不应再报没动静）。"""
    community_ids = (await db.execute(
        select(CommunityElder.community_id).where(CommunityElder.elder_id == elder_id)
    )).scalars().all()
    if not community_ids:
        return None
    rows = (await db.execute(
        select(CanteenRecord.parsed_data, CanteenRecord.created_at)
        .where(
            CanteenRecord.community_id.in_(community_ids),
            CanteenRecord.parse_status == "success",
            CanteenRecord.created_at >= datetime.now() - timedelta(days=14),
        )
        .order_by(desc(CanteenRecord.created_at))
        .limit(300)
    )).all()
    for parsed, created_at in rows:
        for att in (parsed or {}).get("attendees", []):
            if str(att.get("elder_id")) == str(elder_id) and att.get("present") is True:
                return created_at
    return None


async def _last_activity_at(db, elder_id) -> datetime | None:
    """老人最近一次活动：查看小程序、设备真实活动（门磁开合、红外有人）、走访/人工确认、食堂就餐。"""
    viewed = (await db.execute(
        select(func.max(ViewEvent.viewed_at)).where(ViewEvent.viewer_id == elder_id)
    )).scalar_one_or_none()
    # 白名单已含 visit / manual_confirm；source=alert 是告警同步产生的事件，不算活动
    event = (await db.execute(
        select(func.max(CommunityEvent.created_at)).where(
            CommunityEvent.elder_id == elder_id,
            CommunityEvent.event_type.in_(SIGNAL_EVENT_TYPES),
            CommunityEvent.source != "alert",
        )
    )).scalar_one_or_none()
    canteen = await _canteen_last_seen(db, elder_id)
    candidates = [t for t in (viewed, event, canteen) if t is not None]
    return max(candidates) if candidates else None


async def _notify_device_care(db, alert_id, label: str) -> None:
    """设备关怀类预警默认只在平台展示（白老师 2026-10-29：预警是平台展示口径，与电话告警解耦）。

    需要临时开启微信提醒时把 ALERT_NOTIFY_DEVICE_CARE_ENABLED 设为 true；
    电话告警将走独立通道，不挂在这套规则上。
    """
    if not settings.ALERT_NOTIFY_DEVICE_CARE_ENABLED:
        return
    try:
        from app.services.notification import notify_worker_alert
        await notify_worker_alert(db, alert_id)
    except Exception:
        logger.exception("发送%s通知失败", label)


async def _door_verify_alert(db, record, hours: int, now: datetime) -> int:
    """门磁装好满一个周期仍没有任何开关门记录 → 提醒核实设备（同一老人只提一次）。

    白老师 2026-10-29 认可：避免“设备没装好/电池没电”被当成老人正常不出门。
    """
    existing = await db.execute(
        select(Alert.id).where(
            Alert.elder_id == record.elder_id,
            Alert.trigger_rule == "door_verify",
        ).limit(1)
    )
    if existing.scalar_one_or_none():
        return 0
    elder_name = await _get_elder_name(db, record.elder_id)
    db.add(Alert(
        elder_id=record.elder_id,
        community_id=record.community_id,
        alert_type="device_check",
        alert_level="info",
        message=(
            f"{elder_name} 家的门磁已装好超过{int(hours)}小时仍没有任何开关门记录，"
            "请核实门磁是否安装到位、电池是否正常"
        ),
        trigger_rule="door_verify",
        assigned_worker_id=record.assigned_worker_id,
        response_deadline=now + timedelta(minutes=30),
    ))
    await db.flush()
    return 1


async def stillness_check():
    """红外短时静止：超过阈值（默认 1 小时）没检测到活动即提醒。

    阈值、生效时段、提醒间隔都读 alert_rules（默认 7:00–22:00、6 小时内不重复）；
    已达到“长时间无生活轨迹”时长的老人由 no_activity_trace 处理，不重复提醒。
    """
    now = datetime.now()
    _name_cache.clear()
    _rule_cache.clear()
    total_alerts = 0
    async with async_session() as db:
        records = await _elder_records_by_device_type(db, MOTION_DEVICE_TYPE)
        for record, sn in records:
            # 设备离线超阈值 → 暂停该设备的活跃提醒，避免把“设备坏了”报成“老人没活动”
            if _is_device_offline(sn):
                continue
            cfg = await _rule_entry(db, record.community_id, "stillness", record.care_level)
            if cfg is None or not cfg["enabled"]:
                continue
            start, end = _window(cfg["params"], (7, 22))
            if not (start <= now.hour < end):
                continue

            last_active = await _last_activity_at(db, record.elder_id)
            baseline = max(last_active, record.created_at) if last_active else record.created_at
            elapsed = (now - baseline).total_seconds() / 3600
            if elapsed < cfg["hours"]:
                continue

            trace_cfg = await _rule_entry(
                db, record.community_id, "no_activity_trace", record.care_level
            )
            if trace_cfg and trace_cfg["enabled"] and elapsed >= trace_cfg["hours"]:
                continue

            dedupe = timedelta(hours=_hours_param(cfg["params"], "dedupe_hours", 6))
            existing = await db.execute(
                select(Alert.id).where(
                    Alert.elder_id == record.elder_id,
                    Alert.trigger_rule.in_(("stillness", "morning_silence")),
                    Alert.is_resolved == False,  # noqa: E712
                    Alert.created_at >= now - dedupe,
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                continue

            elder_name = await _get_elder_name(db, record.elder_id)
            severity = {"A": "urgent", "B": "warning", "C": "info"}.get(record.care_level, "info")
            alert = Alert(
                elder_id=record.elder_id,
                community_id=record.community_id,
                alert_type="stillness",
                alert_level=severity,
                message=f"{elder_name} 已超过{int(elapsed)}小时没有活动迹象，可能存在跌倒风险，建议尽快电话或上门确认",
                trigger_rule="stillness",
                assigned_worker_id=record.assigned_worker_id,
                response_deadline=now + timedelta(minutes=30),
            )
            db.add(alert)
            await db.flush()

            await _notify_device_care(db, alert.id, "静止预警")
            total_alerts += 1

        await db.commit()
    logger.info(f"短时静止检查完成，产生 {total_alerts} 条提醒")


# ── Job 8: 长时间无生活轨迹（默认每 2 小时，全天生效）──

async def no_activity_trace_check():
    """长时间无生活轨迹：默认 12 小时内没有任何活动迹象即提醒，全天生效。"""
    now = datetime.now()
    _name_cache.clear()
    _rule_cache.clear()
    total_alerts = 0
    async with async_session() as db:
        records = await _elder_records_by_device_type(db, MOTION_DEVICE_TYPE)
        for record, sn in records:
            if _is_device_offline(sn):
                continue
            cfg = await _rule_entry(
                db, record.community_id, "no_activity_trace", record.care_level
            )
            if cfg is None or not cfg["enabled"]:
                continue
            start, end = _window(cfg["params"], (0, 24))
            if not (start <= now.hour < end):
                continue

            last_active = await _last_activity_at(db, record.elder_id)
            baseline = max(last_active, record.created_at) if last_active else record.created_at
            elapsed = (now - baseline).total_seconds() / 3600
            if elapsed < cfg["hours"]:
                continue

            dedupe = timedelta(hours=_hours_param(cfg["params"], "dedupe_hours", 12))
            existing = await db.execute(
                select(Alert.id).where(
                    Alert.elder_id == record.elder_id,
                    Alert.trigger_rule == "no_activity_trace",
                    Alert.is_resolved == False,  # noqa: E712
                    Alert.created_at >= now - dedupe,
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                continue

            elder_name = await _get_elder_name(db, record.elder_id)
            severity = {"A": "urgent", "B": "warning", "C": "warning"}.get(record.care_level, "warning")
            alert = Alert(
                elder_id=record.elder_id,
                community_id=record.community_id,
                # alert_type 列宽 varchar(16)，长规则名放 trigger_rule（varchar32）
                alert_type="no_activity",
                alert_level=severity,
                message=f"{elder_name} 已超过{int(elapsed)}小时无生活轨迹，建议电话或上门确认",
                trigger_rule="no_activity_trace",
                assigned_worker_id=record.assigned_worker_id,
                response_deadline=now + timedelta(minutes=30),
            )
            db.add(alert)
            await db.flush()

            await _notify_device_care(db, alert.id, "无生活轨迹提醒")
            total_alerts += 1

        await db.commit()
    logger.info(f"无生活轨迹检查完成，产生 {total_alerts} 条提醒")


# ── Job 9: 门磁长时间未触发（默认每天 8:00 检查前 24 小时）──

async def no_outing_check():
    """门磁长时间未触发：默认 8:00–8:00 窗口内没有任何开门动作即提醒。

    从未触发过门磁的老人不判定（无法区分“不出门”与“设备刚启用”）。
    """
    now = datetime.now()
    _name_cache.clear()
    _rule_cache.clear()
    total_alerts = 0
    scheduled = False
    async with async_session() as db:
        records = await _elder_records_by_device_type(db, DOOR_DEVICE_TYPE)
        for record, sn in records:
            if _is_device_offline(sn):
                continue
            cfg = await _rule_entry(db, record.community_id, "no_outing", record.care_level)
            if cfg is None or not cfg["enabled"]:
                continue
            if now.hour != _hour_of_day(cfg["params"], "check_hour", 8):
                continue
            scheduled = True

            last_trigger = (await db.execute(
                select(func.max(CommunityEvent.created_at)).where(
                    CommunityEvent.elder_id == record.elder_id,
                    CommunityEvent.event_type.in_(("door_open", "door_close")),
                )
            )).scalar_one_or_none()
            if last_trigger is None:
                # 装好满一个周期仍无任何开关门记录 → 先提醒核实设备（白老师 2026-10-29 认可）
                if (now - record.created_at).total_seconds() / 3600 >= cfg["hours"]:
                    total_alerts += await _door_verify_alert(db, record, cfg["hours"], now)
                continue

            elapsed = (now - last_trigger).total_seconds() / 3600
            if elapsed < cfg["hours"]:
                continue

            dedupe = timedelta(hours=_hours_param(cfg["params"], "dedupe_hours", 24))
            existing = await db.execute(
                select(Alert.id).where(
                    Alert.elder_id == record.elder_id,
                    Alert.trigger_rule == "no_outing",
                    Alert.is_resolved == False,  # noqa: E712
                    Alert.created_at >= now - dedupe,
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                continue

            elder_name = await _get_elder_name(db, record.elder_id)
            severity = "warning" if record.care_level == "A" else "info"
            alert = Alert(
                elder_id=record.elder_id,
                community_id=record.community_id,
                alert_type="no_outing",
                alert_level=severity,
                message=f"{elder_name} 已超过{int(elapsed)}小时没有开门外出记录，建议联系问候",
                trigger_rule="no_outing",
                assigned_worker_id=record.assigned_worker_id,
                response_deadline=now + timedelta(minutes=30),
            )
            db.add(alert)
            await db.flush()

            await _notify_device_care(db, alert.id, "长期未外出提醒")
            total_alerts += 1

        await db.commit()
    if scheduled:
        logger.info(f"长期未外出检查完成，产生 {total_alerts} 条提醒")


# ── Job 10: 设备离线检查（默认每 30 分钟）──

async def _record_for_device(db, item) -> CommunityElder | None:
    try:
        record_id = uuid.UUID(str(item.get("elder_record_id") or "").strip())
    except ValueError:
        return None
    return await db.get(CommunityElder, record_id)


async def _raise_device_offline(db, item, offline_hours: float, now: datetime) -> int:
    """离线超阈值 → 提醒网格员核实设备（同一老人未解决前只提一次）。"""
    record = await _record_for_device(db, item)
    if record is None:
        return 0
    existing = await db.execute(
        select(Alert.id).where(
            Alert.elder_id == record.elder_id,
            Alert.trigger_rule == "device_offline",
            Alert.is_resolved == False,  # noqa: E712
        ).limit(1)
    )
    if existing.scalar_one_or_none():
        return 0
    label = "门磁" if int(item.get("device_type") or 0) == DOOR_DEVICE_TYPE else "红外探测器"
    elder_name = await _get_elder_name(db, record.elder_id)
    db.add(Alert(
        elder_id=record.elder_id,
        community_id=record.community_id,
        alert_type="device_offline",
        alert_level="warning",
        message=(
            f"{elder_name} 家的{label}已离线超过{int(offline_hours)}小时，"
            "已暂停该设备的活跃提醒以避免误报，请核实设备供电与网络"
        ),
        trigger_rule="device_offline",
        assigned_worker_id=record.assigned_worker_id,
        response_deadline=now + timedelta(minutes=30),
    ))
    await db.flush()
    return 1


async def _resolve_device_offline(db, item) -> None:
    """设备恢复在线 → 自动解除未解决的离线提醒，规则随即恢复判定。"""
    record = await _record_for_device(db, item)
    if record is None:
        return
    await db.execute(
        update(Alert)
        .where(
            Alert.elder_id == record.elder_id,
            Alert.trigger_rule == "device_offline",
            Alert.is_resolved == False,  # noqa: E712
        )
        .values(is_resolved=True, resolved_at=datetime.now(), response_note="设备已恢复在线，自动解除")
    )


async def device_offline_check():
    """设备离线超阈值 → 给该设备的活跃提醒“断电”，并提醒网格员检查设备。

    白老师 2026-10-29：设备坏了不能继续按“老人没活动”报警。
    平台接口不可用（available=False）时不判定，避免平台故障误停全部规则。
    """
    now = datetime.now()
    devices, _ = load_registry()
    targets = {
        sn: item for sn, item in devices.items()
        if int(item.get("device_type") or 0) in (DOOR_DEVICE_TYPE, MOTION_DEVICE_TYPE)
    }
    if not targets:
        return
    status_map = await phchn_open_api.fetch_devices_status(list(targets), use_cache=False)
    created = 0
    async with async_session() as db:
        for sn, status in status_map.items():
            if not status.get("available"):
                continue  # 平台不可用：保守放行，不误停规则
            if status.get("platform_status") == 1:
                if _offline_since.pop(sn, None) is not None:
                    logger.info("设备恢复在线：%s", sn)
                    await _resolve_device_offline(db, targets[sn])
                continue
            since = _offline_since.setdefault(sn, now)
            offline_hours = (now - since).total_seconds() / 3600
            if offline_hours < DEVICE_OFFLINE_HOURS:
                continue
            created += await _raise_device_offline(db, targets[sn], offline_hours, now)
        await db.commit()
    logger.info(f"设备离线检查完成，产生 {created} 条提醒")


# ── Scheduler 启动/关闭 ──


def start_scheduler():
    scheduler.add_job(run_alert_rules, "interval", minutes=5, id="community_alert_rules")
    scheduler.add_job(check_unread_alerts, "interval", minutes=5, id="family_alert_checker")
    scheduler.add_job(sync_all_communities, "interval", minutes=30, id="alert_sync")
    scheduler.add_job(check_escalations, "interval", minutes=15, id="escalation_checker")
    scheduler.add_job(recalculate_risk_scores, "interval", hours=1, id="risk_scorer")
    scheduler.add_job(morning_silence_check, CronTrigger(hour=8, minute=0), id="morning_silence")
    # 三条设备关怀规则的阈值与时段均可在管理后台「告警规则」页调整
    scheduler.add_job(stillness_check, "interval", hours=1, id="stillness_checker")
    scheduler.add_job(no_activity_trace_check, "interval", hours=2, id="no_activity_trace_checker")
    scheduler.add_job(no_outing_check, "interval", hours=1, id="no_outing_checker")
    # 设备离线超阈值即暂停该设备的活跃提醒（白老师 2026-10-29：设备坏了要给规则断电）
    scheduler.add_job(device_offline_check, "interval", minutes=30, id="device_offline_checker")
    scheduler.start()
    logger.info(
        "定时任务已启动：community_rules(5m), family_alerts(5m), sync(30m), escalation(15m), "
        "risk(1h), morning_silence(8:00), stillness(1h), no_activity_trace(2h), "
        "no_outing(每日 8:00), device_offline(30m)"
    )


def shutdown_scheduler():
    scheduler.shutdown()
