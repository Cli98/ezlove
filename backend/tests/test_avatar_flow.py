import pytest

from tests.helpers import auth_headers, create_alert, create_relation, create_user


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_family_sees_saved_elder_avatar_in_relations_and_alerts(client, db):
    family = await create_user(db, "avatar-family", role="family")
    elder = await create_user(db, "avatar-elder", role="elder", nickname="妈妈")
    relation = await create_relation(db, family.id, elder.id)
    await create_alert(db, care_relation_id=relation.id, elder_id=elder.id)

    elder_headers = await auth_headers(client, elder.openid)
    avatar_url = "/static/avatars/elder-female-1.png"
    update = await client.put(
        "/api/v1/users/me", json={"avatar_url": avatar_url}, headers=elder_headers,
    )
    assert update.status_code == 200
    assert update.json()["avatar_url"] == avatar_url

    family_headers = await auth_headers(client, family.openid)
    relations = await client.get("/api/v1/relations", headers=family_headers)
    assert relations.status_code == 200
    assert relations.json()[0]["elder_avatar_url"] == avatar_url

    alerts = await client.get("/api/v1/alerts", headers=family_headers)
    assert alerts.status_code == 200
    assert alerts.json()["items"][0]["elder_name"] == "妈妈"
    assert alerts.json()["items"][0]["elder_avatar_url"] == avatar_url

    stranger = await create_user(db, "avatar-stranger", role="family")
    other_alerts = await client.get(
        "/api/v1/alerts", headers=await auth_headers(client, stranger.openid),
    )
    assert other_alerts.json()["items"] == []
