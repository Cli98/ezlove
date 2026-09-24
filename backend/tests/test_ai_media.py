"""AC-4 AI 媒体域 402 回归用例（P3 §5 映射表；文案契约 P2 W-09 逐字断言）。

P-4 修复前 generate-video 合法路径 NameError → 500；修复后积分不足 → 402。
restore-photo / animate-photo 为基线正确路径回归（防 402 退化为 500）。

注：登录接口已接入每日奖励（+10 积分），本模块用例需“零积分”前提，
登录后经 _zero_out_points 显式归零，保持 W-09 逐字文案（当前可用 0）契约。
"""
import pytest
from sqlalchemy import update

from app.models.user_points import UserPointAccount
from tests.helpers import auth_headers, create_user

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _zero_out_points(db, user_id):
    """将用户积分清零（抵消登录每日奖励，保持用例零积分前提）。"""
    await db.execute(
        update(UserPointAccount)
        .where(UserPointAccount.user_id == user_id)
        .values(available_points=0, total_points=0)
    )
    await db.commit()


async def test_generate_video_zero_points_402(client, db):
    """W-09：积分 0 用户调 generate-video → 402 逐字文案（非 500，P-4 修复验证）。"""
    user = await create_user(db, "user-ai1", role="family")
    headers = await auth_headers(client, "user-ai1")
    await _zero_out_points(db, user.id)
    resp = await client.post(
        "/api/v1/ai/media/generate-video",
        json={"image_url": "https://example.com/photo.jpg"},
        headers=headers,
    )
    assert resp.status_code == 402  # 修复前该路径 NameError → 500
    assert resp.json()["detail"] == "积分不足，需要 50，当前可用 0"


async def test_restore_animate_402_regression(client, db):
    """W-09 同款文案：restore-photo / animate-photo 积分不足仍 402（回归）。"""
    user = await create_user(db, "user-ai2", role="family")
    headers = await auth_headers(client, "user-ai2")
    await _zero_out_points(db, user.id)

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
