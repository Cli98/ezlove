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

    data = {
        "thing1": {"value": f"{elder_name}的牵挂"},
        "number2": {"value": str(hours)},
        "thing3": {"value": "您发送的牵挂还未被查看，请留意"},
    }
    await send_subscribe_message(openid, template_id, data, page="pages/alerts/index")


async def notify_worker_alert(
    db: AsyncSession,
    alert_id: uuid.UUID,
):
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

    data = {
        "thing1": {"value": alert.message[:20] if alert.message else "新告警"},
        "thing2": {"value": {"urgent": "紧急", "warning": "警告", "info": "信息"}.get(alert.alert_level, "信息")},
        "thing3": {"value": "请及时处理"},
    }
    await send_subscribe_message(openid, template_id, data)
