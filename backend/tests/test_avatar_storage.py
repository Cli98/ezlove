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


def test_avatar_upload_falls_back_to_local_static_without_oss(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "OSS_ACCESS_KEY_ID", "")
    monkeypatch.setattr(settings, "OSS_ACCESS_KEY_SECRET", "")
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "STATIC_PUBLIC_BASE", "https://yiguanian.ysgy.org.cn/ezlove-api")
    monkeypatch.setattr(object_storage, "UPLOAD_DIR", tmp_path)

    url = object_storage.store_upload(b"image-data", "png", "image/png", "avatar")

    assert url.startswith("https://yiguanian.ysgy.org.cn/ezlove-api/static/uploads/avatar/")
    saved = list((tmp_path / "avatar").glob("*.png"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"image-data"


def test_avatar_upload_falls_back_when_oss_put_fails(monkeypatch, tmp_path):
    class BrokenBucket:
        def put_object(self, *args, **kwargs):
            raise RuntimeError("AccessDenied")

    monkeypatch.setattr(settings, "OSS_ACCESS_KEY_ID", "id")
    monkeypatch.setattr(settings, "OSS_ACCESS_KEY_SECRET", "secret")
    monkeypatch.setattr(settings, "OSS_ENDPOINT", "https://oss-cn-hangzhou.aliyuncs.com")
    monkeypatch.setattr(settings, "OSS_BUCKET_NAME", "ezlove-assets-hz")
    monkeypatch.setattr(settings, "OSS_PUBLIC_BASE_URL", "https://ezlove-assets.ysgy.org.cn")
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "STATIC_PUBLIC_BASE", "https://yiguanian.ysgy.org.cn/ezlove-api")
    monkeypatch.setattr(object_storage, "_bucket", lambda: BrokenBucket())
    monkeypatch.setattr(object_storage, "UPLOAD_DIR", tmp_path)

    url = object_storage.store_upload(b"image-data", "png", "image/png", "avatar")

    assert url.startswith("https://yiguanian.ysgy.org.cn/ezlove-api/static/uploads/avatar/")
    assert len(list((tmp_path / "avatar").glob("*.png"))) == 1
