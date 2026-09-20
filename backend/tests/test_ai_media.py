"""AC-4 AI 媒体域 402 回归用例（P3 §5 映射表；文案契约 P2 W-09 逐字断言）。

P-4 修复前 generate-video 合法路径 NameError → 500；修复后积分不足 → 402。
restore-photo / animate-photo 为基线正确路径回归（防 402 退化为 500）。
"""
import pytest

from tests.helpers import auth_headers, create_user

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_generate_video_zero_points_402(client, db):
    """W-09：积分 0 用户调 generate-video → 402 逐字文案（非 500，P-4 修复验证）。"""
    await create_user(db, "user-ai1", role="family")
    resp = await client.post(
        "/api/v1/ai/media/generate-video",
        json={"image_url": "https://example.com/photo.jpg"},
        headers=await auth_headers(client, "user-ai1"),
    )
    assert resp.status_code == 402  # 修复前该路径 NameError → 500
    assert resp.json()["detail"] == "积分不足，需要 50，当前可用 0"


async def test_restore_animate_402_regression(client, db):
    """W-09 同款文案：restore-photo / animate-photo 积分不足仍 402（回归）。"""
    await create_user(db, "user-ai2", role="family")
    headers = await auth_headers(client, "user-ai2")

    resp_restore = await client.post(
        "/api/v1/ai/media/restore-photo",
        json={"image_url": "https://example.com/old.jpg"},
        headers=headers,
    )
    assert resp_restore.status_code == 402
    assert resp_restore.json()["detail"] == "积分不足，需要 30，当前可用 0"

    resp_animate = await client.post(
        "/api/v1/ai/media/animate-photo",
        json={"image_url": "https://example.com/new.jpg", "duration_seconds": 5},
        headers=headers,
    )
    assert resp_animate.status_code == 402
    assert resp_animate.json()["detail"] == "积分不足，需要 40，当前可用 0"
