"""AC-1 moments 域安全用例（P3 §5 映射表；文案契约 P2 W-01~W-05 逐字断言）。"""
import uuid

import pytest
from sqlalchemy import select, func

from app.models.care_moment import CareMoment
from app.models.view_event import ViewEvent

from tests.helpers import (
    auth_headers, create_moment, create_relation, create_user,
    create_view_event,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _view_events_count(db) -> int:
    return (await db.execute(select(func.count(ViewEvent.id)))).scalar() or 0


async def _moments_count(db) -> int:
    return (await db.execute(select(func.count(CareMoment.id)))).scalar() or 0


# ── AC-1.1 发送：家属专属 ──

async def test_send_no_relation_403(client, db):
    """W-01：无 active 关系的用户发送 → 403 逐字文案。"""
    stranger = await create_user(db, "stranger-1", role="family")
    elder = await create_user(db, "elder-1", role="elder")
    headers = await auth_headers(client, "stranger-1")
    resp = await client.post(
        "/api/v1/moments",
        json={"elder_id": str(elder.id), "text_content": "你好"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "请先与老人完成绑定，再发送牵挂"
    assert stranger.id  # noqa: B018 - 仅为可读性


async def test_send_elder_side_403(client, db):
    """W-02：角色错向（调用者是某 active 关系的老人方）发送 → 403 逐字文案，无新行。"""
    family = await create_user(db, "family-1", role="family")
    elder = await create_user(db, "elder-2", role="elder")
    await create_relation(db, family.id, elder.id)
    before = await _moments_count(db)
    headers = await auth_headers(client, "elder-2")
    resp = await client.post(
        "/api/v1/moments",
        json={"elder_id": str(elder.id), "text_content": "老人发的内容"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "仅家人可发送牵挂"
    assert await _moments_count(db) == before  # care_moments 无新行


async def test_send_active_family_200(client, db):
    """合法 active 关系家属发送 → 200 + care_moments 落库（回归路径）。"""
    family = await create_user(db, "family-2", role="family")
    elder = await create_user(db, "elder-3", role="elder")
    await create_relation(db, family.id, elder.id)
    headers = await auth_headers(client, "family-2")
    resp = await client.post(
        "/api/v1/moments",
        json={"elder_id": str(elder.id), "text_content": "合法内容"},
        headers=headers,
    )
    assert resp.status_code == 200
    moment_id = resp.json()["id"]
    moment = (await db.execute(select(CareMoment).where(CareMoment.id == uuid.UUID(moment_id)))).scalar_one()
    assert moment.sender_id == family.id
    assert moment.elder_id == elder.id


# ── AC-1.2 查看：双角色 + 参与方口径（拍板 9） ──

async def test_view_third_party_403(client, db):
    """W-03：moment 存在但 viewer 非参与方 → 403「无权操作」。"""
    family = await create_user(db, "family-3", role="family")
    elder = await create_user(db, "elder-4", role="elder")
    third = await create_user(db, "third-1", role="family")
    await create_relation(db, family.id, elder.id)
    moment = await create_moment(db, family.id, elder.id)
    headers = await auth_headers(client, "third-1")
    resp = await client.post(f"/api/v1/moments/{moment.id}/view", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "无权操作"


async def test_view_missing_404(client, db):
    """不存在的 moment → 404「内容不存在」（先于关系校验，防探测）。"""
    user = await create_user(db, "anyone-1", role="family")
    headers = await auth_headers(client, "anyone-1")
    resp = await client.post(f"/api/v1/moments/{uuid.uuid4()}/view", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "内容不存在"


async def test_view_bound_other_family_403(client, db):
    """拍板 9：多家属绑定同一老人，家属 B（非 sender、与老人有合法 active 关系）
    查看家属 A 发送的 moment → 403「无权操作」（判定口径=moment 参与方 sender/elder）。"""
    family_a = await create_user(db, "family-a", role="family")
    family_b = await create_user(db, "family-b", role="family")
    elder = await create_user(db, "elder-5", role="elder")
    await create_relation(db, family_a.id, elder.id)
    await create_relation(db, family_b.id, elder.id)
    moment = await create_moment(db, family_a.id, elder.id)
    headers = await auth_headers(client, "family-b")
    resp = await client.post(f"/api/v1/moments/{moment.id}/view", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "无权操作"


# ── AC-1.3 / AC-1.4 查看副作用 ──

async def test_family_view_no_record(client, db):
    """家属回看自己发送的 → 200 但 view_events 不落记录（OP-4）。"""
    family = await create_user(db, "family-4", role="family")
    elder = await create_user(db, "elder-6", role="elder")
    await create_relation(db, family.id, elder.id)
    moment = await create_moment(db, family.id, elder.id)
    before = await _view_events_count(db)
    headers = await auth_headers(client, "family-4")
    resp = await client.post(f"/api/v1/moments/{moment.id}/view", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert await _view_events_count(db) == before  # 计数不变


async def test_elder_view_creates_record(client, db):
    """老人查看 → 200 且新增 1 行 viewer_id=老人。"""
    family = await create_user(db, "family-5", role="family")
    elder = await create_user(db, "elder-7", role="elder")
    await create_relation(db, family.id, elder.id)
    moment = await create_moment(db, family.id, elder.id)
    before = await _view_events_count(db)
    headers = await auth_headers(client, "elder-7")
    resp = await client.post(f"/api/v1/moments/{moment.id}/view", headers=headers)
    assert resp.status_code == 200
    assert await _view_events_count(db) == before + 1
    event = (await db.execute(select(ViewEvent).where(ViewEvent.moment_id == moment.id))).scalar_one()
    assert event.viewer_id == elder.id


# ── AC-1.5 回应：老人专属 ──

async def test_response_elder_200(client, db):
    """老人本人回应 → 200 + responses 落库。"""
    from app.models.response import Response
    family = await create_user(db, "family-6", role="family")
    elder = await create_user(db, "elder-8", role="elder")
    await create_relation(db, family.id, elder.id)
    moment = await create_moment(db, family.id, elder.id)
    headers = await auth_headers(client, "elder-8")
    resp = await client.post(
        f"/api/v1/moments/{moment.id}/response",
        json={"response_type": "like", "content": "❤"},
        headers=headers,
    )
    assert resp.status_code == 200
    rows = (await db.execute(select(Response).where(Response.moment_id == moment.id))).scalars().all()
    assert len(rows) == 1
    assert rows[0].responder_id == elder.id


async def test_response_family_403(client, db):
    """W-04：家属（发送者）回应 → 403「无权操作」。"""
    family = await create_user(db, "family-7", role="family")
    elder = await create_user(db, "elder-9", role="elder")
    await create_relation(db, family.id, elder.id)
    moment = await create_moment(db, family.id, elder.id)
    headers = await auth_headers(client, "family-7")
    resp = await client.post(
        f"/api/v1/moments/{moment.id}/response",
        json={"response_type": "like", "content": "❤"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "无权操作"


async def test_response_third_party_403(client, db):
    """W-04：第三方回应 → 403「无权操作」（与家属同文案，匿名化防关系信息泄露）。"""
    family = await create_user(db, "family-8", role="family")
    elder = await create_user(db, "elder-10", role="elder")
    third = await create_user(db, "third-2", role="family")
    await create_relation(db, family.id, elder.id)
    moment = await create_moment(db, family.id, elder.id)
    headers = await auth_headers(client, "third-2")
    resp = await client.post(
        f"/api/v1/moments/{moment.id}/response",
        json={"response_type": "like", "content": "❤"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "无权操作"


async def test_response_missing_404(client, db):
    """C-D10：不存在的 moment 回应 → 404「内容不存在」。"""
    user = await create_user(db, "anyone-2", role="elder")
    headers = await auth_headers(client, "anyone-2")
    resp = await client.post(
        f"/api/v1/moments/{uuid.uuid4()}/response",
        json={"response_type": "like", "content": "❤"},
        headers=headers,
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "内容不存在"


# ── AC-1.6 已读口径（viewer == elder）──

async def test_family_only_view_not_read(client, db):
    """构造 viewer=sender 的历史查看行后，列表/详情 is_read=false（OP-9 判定口径）。"""
    family = await create_user(db, "family-9", role="family")
    elder = await create_user(db, "elder-11", role="elder")
    await create_relation(db, family.id, elder.id)
    moment = await create_moment(db, family.id, elder.id)
    await create_view_event(db, moment.id, family.id)  # 家属的历史"污染"查看行

    list_resp = await client.get(
        "/api/v1/moments", headers=await auth_headers(client, "family-9")
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["is_read"] is False

    detail_resp = await client.get(
        f"/api/v1/moments/{moment.id}", headers=await auth_headers(client, "family-9")
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["is_read"] is False


# ── P6 M-1 回归：同 (family, elder) 对多行 active 不 500 ──

async def test_multi_active_relations_no_500(client, db):
    """M-1：双邀请+双绑定可产生同 (family, elder) 对两条 active 关系，
    get_active_relation 命中多行曾抛 MultipleResultsFound → 500；
    limit(1) 修复后家属发送牵挂与 elders status（同一暴露面）均 200。"""
    family = await create_user(db, "family-11", role="family")
    elder = await create_user(db, "elder-13", role="elder")
    # 构造同对两条 active（等价于两次 invite + 老人分别 bind 的脏数据形态）
    await create_relation(db, family.id, elder.id)
    await create_relation(db, family.id, elder.id)

    headers = await auth_headers(client, "family-11")
    resp = await client.post(
        "/api/v1/moments",
        json={"elder_id": str(elder.id), "text_content": "多行 active 下的发送"},
        headers=headers,
    )
    assert resp.status_code == 200
    moment_id = resp.json()["id"]
    moment = (await db.execute(select(CareMoment).where(CareMoment.id == uuid.UUID(moment_id)))).scalar_one()
    assert moment.sender_id == family.id
    assert moment.elder_id == elder.id

    # 同一暴露面：elders status 也走 get_active_relation 越权校验入口
    status_resp = await client.get(f"/api/v1/elders/{elder.id}/status", headers=headers)
    assert status_resp.status_code == 200
    assert "today_read" in status_resp.json()


# ── AC-1.7 防探测：不存在资源的响应码与调用者身份无关 ──

async def test_missing_moment_404_uniform(client, db):
    """无关用户与合法家属对同一不存在 id 调 view 与 response → 均 404，响应码一致。"""
    stranger = await create_user(db, "stranger-2", role="family")
    family = await create_user(db, "family-10", role="family")
    elder = await create_user(db, "elder-12", role="elder")
    await create_relation(db, family.id, elder.id)
    missing_id = uuid.uuid4()

    stranger_headers = await auth_headers(client, "stranger-2")
    family_headers = await auth_headers(client, "family-10")

    for action in ("view", "response"):
        payload = {} if action == "view" else {"response_type": "like", "content": "❤"}
        resp_s = await client.post(
            f"/api/v1/moments/{missing_id}/{action}", json=payload, headers=stranger_headers
        )
        resp_f = await client.post(
            f"/api/v1/moments/{missing_id}/{action}", json=payload, headers=family_headers
        )
        assert resp_s.status_code == 404
        assert resp_f.status_code == 404
        assert resp_s.json() == resp_f.json()
        assert resp_s.json()["detail"] == "内容不存在"
