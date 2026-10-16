from app.config import settings
from app.services import object_storage


def test_avatar_upload_uses_oss_when_configured(monkeypatch):
    class FakeBucket:
        def put_object(self, key, content, headers):
            assert key.startswith("uploads/avatar/")
            assert key.endswith(".png")
            assert content == b"image-data"
            assert headers == {"Content-Type": "image/png"}

    monkeypatch.setattr(settings, "OSS_ACCESS_KEY_ID", "id")
    monkeypatch.setattr(settings, "OSS_ACCESS_KEY_SECRET", "secret")
    monkeypatch.setattr(settings, "OSS_ENDPOINT", "https://oss-cn-hangzhou.aliyuncs.com")
    monkeypatch.setattr(settings, "OSS_BUCKET_NAME", "ezlove-assets-hz")
    monkeypatch.setattr(settings, "OSS_PUBLIC_BASE_URL", "https://ezlove-assets.ysgy.org.cn")
    monkeypatch.setattr(object_storage, "_bucket", lambda: FakeBucket())

    url = object_storage.store_upload(b"image-data", "png", "image/png", "avatar")
    assert url.startswith("https://ezlove-assets.ysgy.org.cn/uploads/avatar/")


def test_avatar_upload_requires_oss_in_production(monkeypatch):
    monkeypatch.setattr(settings, "OSS_ACCESS_KEY_ID", "")
    monkeypatch.setattr(settings, "DEBUG", False)

    try:
        object_storage.store_upload(b"image-data", "png", "image/png", "avatar")
    except object_storage.ObjectStorageError:
        pass
    else:
        raise AssertionError("生产环境缺少 OSS 配置时不能把头像存到临时容器")
