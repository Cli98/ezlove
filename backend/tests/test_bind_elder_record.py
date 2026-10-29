"""老人微信绑定社区档案用例（POST /users/bind-elder-record）。"""
from uuid import UUID

import pytest

from tests.helpers import (
    auth_headers,
    create_community,
    create_community_elder,
    create_user,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_import_record(db, phone: str = "18368854249", nickname: str = "姚增德"):
    """构造一条挂在导入虚拟账号上的社区档案。"""
    community = await create_community(db)
    import_user = await create_user(db, f"import_{phone}", role="elder", nickname=nickname)
    import_user.phone = phone
    await db.commit()
    record = await create_community_elder(db, community.id, import_user.id, care_level="B")
    return community, import_user, record


async def test_bind_elder_record_success(client, db):
    """手机号匹配导入档案 → 档案迁到当前微信账号，角色与手机号补齐。"""
    _, import_user, record = await _make_import_record(db)
    old_user_id = str(import_user.id)
    headers = await auth_headers(client, "wx-real-elder")

    resp = await client.post(
        "/api/v1/users/bind-elder-record",
        json={"phone": "18368854249"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["record_id"] == str(record.id)
    assert body["elder_name"] == "姚增德"
    assert body["community_name"] == "测试社区"

    await db.refresh(record)
    me = (await client.get("/api/v1/users/me", headers=headers)).json()
    assert str(record.elder_id) == me["id"]
    assert me["role"] == "elder"
    assert me["phone"] == "18368854249"
    assert str(record.elder_id) != old_user_id


async def test_bind_elder_record_repeat_conflict(client, db):
    """同一微信重复绑定 → 409。"""
    await _make_import_record(db)
    headers = await auth_headers(client, "wx-real-elder-repeat")
    first = await client.post(
        "/api/v1/users/bind-elder-record", json={"phone": "18368854249"}, headers=headers,
    )
    assert first.status_code == 200
    second = await client.post(
        "/api/v1/users/bind-elder-record", json={"phone": "18368854249"}, headers=headers,
    )
    assert second.status_code == 409


async def test_bind_elder_record_unknown_phone(client, db):
    """手机号无档案 → 404，不泄露档案是否存在。"""
    await _make_import_record(db)
    headers = await auth_headers(client, "wx-real-elder-unknown")
    resp = await client.post(
        "/api/v1/users/bind-elder-record",
        json={"phone": "13800000000"},
        headers=headers,
    )
    assert resp.status_code == 404


async def test_bind_elder_record_taken_by_other_wx(client, db):
    """档案已挂在真实微信账号上 → 409，防止抢占。"""
    community = await create_community(db)
    other = await create_user(db, "wx-other-elder", role="elder", nickname="已绑定老人")
    other.phone = "13900000001"
    await db.commit()
    await create_community_elder(db, community.id, other.id, care_level="B")

    headers = await auth_headers(client, "wx-real-elder-taken")
    resp = await client.post(
        "/api/v1/users/bind-elder-record",
        json={"phone": "13900000001"},
        headers=headers,
    )
    assert resp.status_code == 409


async def test_bind_elder_record_family_role_rejected(client, db):
    """子女身份不允许绑定社区档案。"""
    await _make_import_record(db)
    headers = await auth_headers(client, "wx-family-user")
    switched = await client.put("/api/v1/users/me", json={"role": "family"}, headers=headers)
    assert switched.status_code == 200

    resp = await client.post(
        "/api/v1/users/bind-elder-record",
        json={"phone": "18368854249"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_bind_elder_record_invalid_phone(client, db):
    """手机号格式不合法 → 422。"""
    headers = await auth_headers(client, "wx-bad-phone")
    resp = await client.post(
        "/api/v1/users/bind-elder-record",
        json={"phone": "123"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_bind_elder_record_by_wx_phone_code(client, db, monkeypatch):
    """微信授权手机号 → 后端换取手机号后自动匹配导入档案。"""
    from app.api.v1 import users as users_module

    _, _, record = await _make_import_record(db)
    headers = await auth_headers(client, "wx-phone-elder")

    async def fake_phone(code: str):
        assert code == "phone-code-ok"
        return "18368854249"

    monkeypatch.setattr(users_module.wechat, "get_phone_number", fake_phone)
    resp = await client.post(
        "/api/v1/users/bind-elder-record/wx-phone",
        json={"code": "phone-code-ok"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["record_id"] == str(record.id)

    me = (await client.get("/api/v1/users/me", headers=headers)).json()
    assert me["role"] == "elder"
    assert me["phone"] == "18368854249"


async def test_bind_elder_record_by_wx_phone_failure(client, db, monkeypatch):
    """微信未返回手机号（未开通组件/授权失效）→ 400，提示降级手动输入。"""
    from app.api.v1 import users as users_module

    await _make_import_record(db)
    headers = await auth_headers(client, "wx-phone-fail")

    async def fake_phone(code: str):
        return None

    monkeypatch.setattr(users_module.wechat, "get_phone_number", fake_phone)
    resp = await client.post(
        "/api/v1/users/bind-elder-record/wx-phone",
        json={"code": "bad-code"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "手动输入" in resp.json()["detail"]


async def test_wx_phone_supplements_phone_after_admin_binding(client, db, monkeypatch):
    """后台代绑档案的微信再授权手机号 → 只补写手机号，不再报「已绑定」。"""
    from app.api.v1 import users as users_module

    community = await create_community(db)
    elder = await create_user(db, "wx-elder-bound-by-admin", role="elder", nickname="姚增德")
    await db.commit()
    record = await create_community_elder(db, community.id, elder.id, care_level="B")
    headers = await auth_headers(client, "wx-elder-bound-by-admin")

    async def fake_phone(code: str):
        return "18368854249"

    monkeypatch.setattr(users_module.wechat, "get_phone_number", fake_phone)
    resp = await client.post(
        "/api/v1/users/bind-elder-record/wx-phone",
        json={"code": "phone-code-ok"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["already_bound"] is True
    assert body["record_id"] == str(record.id)
    assert body["phone_masked"] == "183****4249"

    me = (await client.get("/api/v1/users/me", headers=headers)).json()
    assert me["phone"] == "18368854249"

    await db.refresh(record)
    assert str(record.elder_id) == me["id"]


async def test_community_record_state_for_mini_program(client, db):
    """小程序社区档案页：未绑定→bound=false；后台代绑后→bound=true 且带社区名。"""
    headers = await auth_headers(client, "wx-record-state")
    before = (await client.get("/api/v1/users/community-record", headers=headers)).json()
    assert before["bound"] is False
    assert before["record_id"] is None

    community = await create_community(db)
    me = (await client.get("/api/v1/users/me", headers=headers)).json()
    record = await create_community_elder(db, community.id, UUID(me["id"]), care_level="B")
    after = (await client.get("/api/v1/users/community-record", headers=headers)).json()
    assert after["bound"] is True
    assert after["record_id"] == str(record.id)
    assert after["community_name"] == "测试社区"