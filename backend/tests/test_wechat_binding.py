"""社区端微信绑定用例（GET/POST /community/elders/{id}/wechat-binding）。

管理后台绑定是"老人零操作"通道：老人在小程序登录过，工作人员在档案页选账号绑定。
"""
import pytest
from datetime import datetime, timedelta

from tests.helpers import (
    create_community,
    create_community_elder,
    create_moment,
    create_user,
    create_view_event,
    create_worker,
    worker_headers,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _setup(db):
    """构造社区 + 工作人员 + 挂在导入账号上的老人档案。"""
    community = await create_community(db)
    worker = await create_worker(db, community.id)
    import_user = await create_user(db, "import_18368854249", role="elder", nickname="姚增德")
    import_user.phone = "18368854249"
    await db.commit()
    record = await create_community_elder(db, community.id, import_user.id, care_level="B")
    return community, worker, record, import_user


async def test_binding_status_lists_candidates(client, db):
    """未绑定时返回 bound=False，候选只含未关联档案的真实微信账号。"""
    _, worker, record, _ = await _setup(db)
    candidate = await create_user(db, "wx-elder-candidate", role="elder", nickname="老人微信")
    candidate.avatar_url = "https://example.com/avatar.png"
    candidate.phone = "13800008000"
    await db.commit()
    other_community = await create_community(db, "其它社区")
    taken_user = await create_user(db, "import_other", role="elder", nickname="其他老人")
    await create_community_elder(db, other_community.id, taken_user.id)

    resp = await client.get(
        f"/api/v1/community/elders/{record.id}/wechat-binding",
        headers=worker_headers(worker),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["bound"] is False
    ids = [item["id"] for item in body["candidates"]]
    assert str(candidate.id) in ids
    assert str(taken_user.id) not in ids

    # 现场认人靠头像/昵称/手机号，缺任意一项都会退回“微信用户”
    item = next(c for c in body["candidates"] if c["id"] == str(candidate.id))
    assert item["avatar_url"] == "https://example.com/avatar.png"
    assert item["phone_masked"] == "138****8000"


async def test_bind_wechat_success(client, db):
    """选中真实微信账号后档案迁移，状态变为已绑定且角色补为 elder。"""
    _, worker, record, import_user = await _setup(db)
    target = await create_user(db, "wx-elder-real", nickname="真实老人")
    old_user_id = import_user.id

    resp = await client.post(
        f"/api/v1/community/elders/{record.id}/wechat-binding",
        json={"user_id": str(target.id)},
        headers=worker_headers(worker),
    )
    assert resp.status_code == 200, resp.text

    await db.refresh(record)
    await db.refresh(target)
    assert record.elder_id == target.id
    assert record.elder_id != old_user_id
    assert target.role == "elder"

    status = await client.get(
        f"/api/v1/community/elders/{record.id}/wechat-binding",
        headers=worker_headers(worker),
    )
    assert status.json()["bound"] is True


async def test_bind_wechat_already_bound(client, db):
    """档案已关联真实微信 → 409，避免覆盖。"""
    _, worker, record, _ = await _setup(db)
    first = await create_user(db, "wx-elder-first", nickname="先绑定的微信")
    headers = worker_headers(worker)
    ok = await client.post(
        f"/api/v1/community/elders/{record.id}/wechat-binding",
        json={"user_id": str(first.id)},
        headers=headers,
    )
    assert ok.status_code == 200

    second = await create_user(db, "wx-elder-second", nickname="后绑定的微信")
    resp = await client.post(
        f"/api/v1/community/elders/{record.id}/wechat-binding",
        json={"user_id": str(second.id)},
        headers=headers,
    )
    assert resp.status_code == 409


async def test_bind_wechat_reject_import_account(client, db):
    """导入虚拟账号不能作为绑定目标 → 400。"""
    _, worker, record, _ = await _setup(db)
    fake = await create_user(db, "import_13800000000", role="elder", nickname="导入账号")

    resp = await client.post(
        f"/api/v1/community/elders/{record.id}/wechat-binding",
        json={"user_id": str(fake.id)},
        headers=worker_headers(worker),
    )
    assert resp.status_code == 400


async def test_bind_wechat_conflict_other_record(client, db):
    """目标微信已关联其它档案 → 409。"""
    community, worker, record, _ = await _setup(db)
    target = await create_user(db, "wx-elder-taken", role="elder", nickname="已有关联的老人")
    await create_community_elder(db, community.id, target.id)

    resp = await client.post(
        f"/api/v1/community/elders/{record.id}/wechat-binding",
        json={"user_id": str(target.id)},
        headers=worker_headers(worker),
    )
    assert resp.status_code == 409


async def test_candidates_ranked_by_recent_view(client, db):
    """候选返回最近查看时间与次数并按最近查看倒序：现场让老人打开一次即可认人。"""
    _, worker, record, import_user = await _setup(db)
    old_viewer = await create_user(db, "wx-viewed-old", nickname="早看过")
    fresh_viewer = await create_user(db, "wx-viewed-fresh", nickname="刚看过")
    never_viewer = await create_user(db, "wx-viewed-never", nickname="没看过")
    moment = await create_moment(db, import_user.id, import_user.id)
    now = datetime.now()
    await create_view_event(db, moment.id, old_viewer.id, viewed_at=now - timedelta(minutes=40))
    await create_view_event(db, moment.id, fresh_viewer.id, viewed_at=now - timedelta(seconds=20))
    await create_view_event(db, moment.id, fresh_viewer.id, viewed_at=now - timedelta(seconds=10))

    resp = await client.get(
        f"/api/v1/community/elders/{record.id}/wechat-binding",
        headers=worker_headers(worker),
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["candidates"]
    assert [item["nickname"] for item in items] == ["刚看过", "早看过", "没看过"]

    fresh_item = next(item for item in items if item["id"] == str(fresh_viewer.id))
    assert fresh_item["view_count"] == 2
    assert fresh_item["last_viewed_at"] is not None
    assert fresh_item["last_view_text"] == "测试牵挂内容"

    never_item = next(item for item in items if item["id"] == str(never_viewer.id))
    assert never_item["last_viewed_at"] is None
    assert never_item["last_view_text"] is None
    assert never_item["view_count"] == 0


async def test_anonymous_candidate_identifiable_by_viewed_moment(client, db):
    """匿名微信没有昵称/头像/手机号时，必须给出“最近看过哪条牵挂”供现场核对。"""
    _, worker, record, import_user = await _setup(db)
    anonymous = await create_user(db, "wx-anonymous-viewer")
    moment = await create_moment(db, import_user.id, import_user.id)
    await create_view_event(db, moment.id, anonymous.id)

    resp = await client.get(
        f"/api/v1/community/elders/{record.id}/wechat-binding",
        headers=worker_headers(worker),
    )
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json()["candidates"] if i["id"] == str(anonymous.id))
    assert item["nickname"] is None
    assert item["avatar_url"] is None
    assert item["phone_masked"] is None
    assert item["last_view_text"] == "测试牵挂内容"


async def test_bind_wechat_cross_community_rejected(client, db):
    """其它社区工作人员不能读写本社区档案 → 404。"""
    _, _, record, _ = await _setup(db)
    other_community = await create_community(db, "其它社区")
    other_worker = await create_worker(db, other_community.id)
    target = await create_user(db, "wx-elder-cross", nickname="跨社区微信")

    get_resp = await client.get(
        f"/api/v1/community/elders/{record.id}/wechat-binding",
        headers=worker_headers(other_worker),
    )
    assert get_resp.status_code == 404

    post_resp = await client.post(
        f"/api/v1/community/elders/{record.id}/wechat-binding",
        json={"user_id": str(target.id)},
        headers=worker_headers(other_worker),
    )
    assert post_resp.status_code == 404