import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, or_, func, desc

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

logger = logging.getLogger("ezlove.alert_checker")
scheduler = AsyncIOScheduler()

# 老人姓名缓存，避免同一轮检测中重复查询 User 表
_name_cache: dict = {}

# 构成"老人有活动迹象"的社区事件类型白名单（P3 §3.4 契约）：
# 排除 absent（负向信号）与 other（含告警同步事件与备注，保守不算信号）；
# source="alert"（告警同步产生的事件）另行排除——修复"同步告警事件压制晨检"（OP-1）
SIGNAL_EVENT_TYPES = frozenset({"visit", "manual_confirm"})


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

                # 检查是否已有未解决的晨间告警
                existing = await db.execute(
                    select(Alert).where(
                        Alert.elder_id == elder.elder_id,
                        Alert.trigger_rule == "morning_silence",
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


# ── Scheduler 启动/关闭 ──

def start_scheduler():
    scheduler.add_job(run_alert_rules, "interval", minutes=5, id="community_alert_rules")
    scheduler.add_job(check_unread_alerts, "interval", minutes=5, id="family_alert_checker")
    scheduler.add_job(sync_all_communities, "interval", minutes=30, id="alert_sync")
    scheduler.add_job(check_escalations, "interval", minutes=15, id="escalation_checker")
    scheduler.add_job(recalculate_risk_scores, "interval", hours=1, id="risk_scorer")
    scheduler.add_job(morning_silence_check, CronTrigger(hour=8, minute=0), id="morning_silence")
    scheduler.start()
    logger.info("定时任务已启动：community_rules(5m), family_alerts(5m), sync(30m), escalation(15m), risk(1h), morning_silence(8:00)")


def shutdown_scheduler():
    scheduler.shutdown()
