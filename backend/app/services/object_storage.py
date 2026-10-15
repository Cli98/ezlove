import uuid
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from app.config import settings


UPLOAD_DIR = Path(__file__).resolve().parents[2] / "static" / "uploads"


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
    filename = f"{uuid.uuid4().hex}.{extension}"
    if not oss_enabled():
        if not settings.DEBUG:
            raise ObjectStorageError("生产环境未配置 OSS")
        target = UPLOAD_DIR / category / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return f"/static/uploads/{category}/{filename}"

    key = f"uploads/{category}/{filename}"
    try:
        _bucket().put_object(key, content, headers={"Content-Type": content_type})
    except Exception as exc:
        raise ObjectStorageError("OSS 上传失败") from exc
    return f"{settings.OSS_PUBLIC_BASE_URL.rstrip('/')}/{quote(key, safe='/')}"
