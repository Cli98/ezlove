import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.care_relation import CareRelation
from app.models.user import User
from app.models.alert import Alert
from app.models.community import CommunityWorker
from app.utils.wechat import send_subscribe_message

logger = logging.getLogger("ezlove.notification")


async def notify_family_unread(
    db: AsyncSession,
    care_relation_id: uuid.UUID,
    elder_name: str,
    hours: int,
):
    # dry-run 静默开关：关闭时只落表不发通知（P3 §3.5）
    if not settings.ALERT_NOTIFY_ENABLED:
        logger.info("ALERT_NOTIFY_ENABLED=false，跳过未读通知发送")
        return

    template_id = settings.WECHAT_UNREAD_TEMPLATE_ID
    if not template_id:
        logger.debug("WECHAT_UNREAD_TEMPLATE_ID 未配置，跳过未读通知")
        return

    result = await db.execute(
        select(User.openid)
        .join(CareRelation, CareRelation.family_user_id == User.id)
        .where(CareRelation.id == care_relation_id)
    )
    openid = result.scalar_one_or_none()
    if not openid:
        return

    # 模板「互助服务进度通知」：thing2 服务名称 / thing4 温馨提示
    data = {
        "thing2": {"value": f"{elder_name}的牵挂"},
        "thing4": {"value": f"已{hours}小时未查看，点开看看吧"},
    }
    await send_subscribe_message(openid, template_id, data, page="pages/alerts/index")


async def notify_worker_alert(
    db: AsyncSession,
    alert_id: uuid.UUID,
):
    # dry-run 静默开关：关闭时只落表不发通知（P3 §3.5，覆盖社区侧防误触）
    if not settings.ALERT_NOTIFY_ENABLED:
        logger.info("ALERT_NOTIFY_ENABLED=false，跳过告警通知发送")
        return

    template_id = settings.WECHAT_ALERT_TEMPLATE_ID
    if not template_id:
        logger.debug("WECHAT_ALERT_TEMPLATE_ID 未配置，跳过告警通知")
        return

    alert = await db.get(Alert, alert_id)
    if not alert or not alert.assigned_worker_id:
        return

    result = await db.execute(
        select(User.openid)
        .join(CommunityWorker, CommunityWorker.user_id == User.id)
        .where(CommunityWorker.id == alert.assigned_worker_id)
    )
    openid = result.scalar_one_or_none()
    if not openid:
        return

    # 模板「报告生成通知」：thing1 报告主题 / thing2 风险等级 / thing4 温馨提示
    data = {
        "thing1": {"value": alert.message[:20] if alert.message else "新提醒"},
        "thing2": {"value": {"urgent": "高风险", "warning": "中风险", "info": "低风险"}.get(alert.alert_level, "低风险")},
        "thing4": {"value": "请尽快核实处理"},
    }
    await send_subscribe_message(openid, template_id, data, page="pages/alerts/index")
