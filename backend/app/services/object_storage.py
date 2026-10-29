import logging
import uuid
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from app.config import settings


UPLOAD_DIR = Path(__file__).resolve().parents[2] / "static" / "uploads"

logger = logging.getLogger("ezlove.storage")


class ObjectStorageError(RuntimeError):
    pass


def oss_enabled() -> bool:
    return all((
        settings.OSS_ACCESS_KEY_ID,
        settings.OSS_ACCESS_KEY_SECRET,
        settings.OSS_ENDPOINT,
        settings.OSS_BUCKET_NAME,
        settings.OSS_PUBLIC_BASE_URL,
    ))


@lru_cache(maxsize=1)
def _bucket():
    import oss2

    auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
    return oss2.Bucket(auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET_NAME)


def store_upload(content: bytes, extension: str, content_type: str, category: str) -> str:
    # OSS 未配置时不再阻断上传：直接落到后端静态目录（backend_static 卷，重建容器不丢）
    if not oss_enabled():
        logger.warning("未配置 OSS，%s 改存后端静态目录", category)
        return _store_local(content, extension, category)

    filename = f"{uuid.uuid4().hex}.{extension}"
    key = f"uploads/{category}/{filename}"
    try:
        _bucket().put_object(key, content, headers={"Content-Type": content_type})
    except Exception:
        # 密钥失效 / 桶权限 / 网络异常都不该让用户保存不了头像，降级到本地静态目录
        logger.exception("OSS 上传失败，%s 改存后端静态目录", category)
        return _store_local(content, extension, category)
    return f"{settings.OSS_PUBLIC_BASE_URL.rstrip('/')}/{quote(key, safe='/')}"


def _store_local(content: bytes, extension: str, category: str) -> str:
    filename = f"{uuid.uuid4().hex}.{extension}"
    target = UPLOAD_DIR / category / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    path = f"/static/uploads/{category}/{filename}"
    if settings.DEBUG:
        return path
    # 线上前后端不同源，返回可公网访问的绝对地址（nginx /ezlove-api → 后端 /api）
    return f"{settings.STATIC_PUBLIC_BASE.rstrip('/')}{path}"
