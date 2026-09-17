import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger("ezlove.wechat")

_access_token_cache = {"token": None, "expires_at": 0}


async def code_to_openid(code: str) -> str | None:
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.WECHAT_APP_ID,
        "secret": settings.WECHAT_APP_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    return data.get("openid")


async def get_access_token() -> str | None:
    if not settings.WECHAT_APP_ID or not settings.WECHAT_APP_SECRET:
        logger.debug("微信 APP_ID/APP_SECRET 未配置，跳过获取 access_token")
        return None

    now = time.time()
    if _access_token_cache["token"] and now < _access_token_cache["expires_at"]:
        return _access_token_cache["token"]

    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": settings.WECHAT_APP_ID,
        "secret": settings.WECHAT_APP_SECRET,
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            data = resp.json()
        token = data.get("access_token")
        if not token:
            logger.warning("获取 access_token 失败: %s", data)
            return None
        expires_in = data.get("expires_in", 7200)
        _access_token_cache["token"] = token
        _access_token_cache["expires_at"] = now + expires_in - 300
        return token
    except Exception:
        logger.exception("获取 access_token 异常")
        return None


async def send_subscribe_message(
    openid: str,
    template_id: str,
    data: dict,
    page: str = "",
) -> bool:
    if not template_id:
        logger.debug("模板 ID 未配置，跳过发送订阅消息")
        return False

    token = await get_access_token()
    if not token:
        return False

    url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={token}"
    payload = {
        "touser": openid,
        "template_id": template_id,
        "data": data,
    }
    if page:
        payload["page"] = page

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            result = resp.json()
        if result.get("errcode", 0) != 0:
            logger.warning("发送订阅消息失败: %s", result)
            return False
        return True
    except Exception:
        logger.exception("发送订阅消息异常")
        return False
