"""硬件事件推送回调（phchn IoT 云平台 → 易挂念）。

平台要求接收方固定返回 HTTP 200，因此除鉴权失败外的业务异常均在服务层消化，
对外统一返回 {"code": 0}；数据库等瞬时故障直接抛 500，交由平台重试（幂等已保证）。
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.nbiot import handle_push

logger = logging.getLogger("ezlove.nbiot")

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/nbiot")
async def nbiot_webhook(
    request: Request,
    token: str | None = Query(default=None),
    x_nbiot_token: str | None = Header(default=None, alias="X-NBIOT-Token"),
    db: AsyncSession = Depends(get_db),
):
    # 平台一般只支持配置 URL，密钥优先放 query；未配置密钥时跳过校验（首轮联调）
    if settings.NBIOT_WEBHOOK_SECRET:
        provided = token or x_nbiot_token
        if provided != settings.NBIOT_WEBHOOK_SECRET:
            client = request.client.host if request.client else "-"
            logger.warning("NB-IoT 推送鉴权失败：client=%s", client)
            raise HTTPException(status_code=401, detail="invalid token")

    try:
        payload = await request.json()
    except Exception:
        client = request.client.host if request.client else "-"
        logger.warning("NB-IoT 推送报文不是合法 JSON：client=%s", client)
        return {"code": 0, "msg": "ignored"}

    if not isinstance(payload, dict):
        logger.warning("NB-IoT 推送报文结构异常：type=%s", type(payload).__name__)
        return {"code": 0, "msg": "ignored"}

    result = await handle_push(db, payload)
    await db.commit()
    return {"code": 0, "msg": "ok", **result}
