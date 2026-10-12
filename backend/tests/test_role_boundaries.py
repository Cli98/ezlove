import pytest

from tests.helpers import auth_headers, create_alert, create_moment, create_relation, create_user


@pytest.mark.asyncio
async def test_moment_lists_are_scoped_by_role(client, db):
    family_a = await create_user(db, "family-list-a", role="family", nickname="女儿")
    family_b = await create_user(db, "family-list-b", role="family", nickname="儿子")
    elder = await create_user(db, "elder-list", role="elder", nickname="王奶奶")
    await create_relation(db, family_a.id, elder.id)
    await create_relation(db, family_b.id, elder.id)
    moment_a = await create_moment(db, family_a.id, elder.id)
    moment_b = await create_moment(db, family_b.id, elder.id)

    family_response = await client.get(
        "/api/v1/moments", headers=await auth_headers(client, family_a.openid)
    )
    elder_response = await client.get(
        "/api/v1/moments", headers=await auth_headers(client, elder.openid)
    )

    assert family_response.status_code == 200
    assert {item["id"] for item in family_response.json()["items"]} == {str(moment_a.id)}
    assert elder_response.status_code == 200
    assert {item["id"] for item in elder_response.json()["items"]} == {
        str(moment_a.id), str(moment_b.id)
    }
    assert {item["sender_name"] for item in elder_response.json()["items"]} == {"女儿", "儿子"}
    assert {item["elder_name"] for item in elder_response.json()["items"]} == {"王奶奶"}


@pytest.mark.asyncio
async def test_elder_cannot_read_or_resolve_family_alerts(client, db):
    family = await create_user(db, "family-role-boundary", role="family")
    elder = await create_user(db, "elder-role-boundary", role="elder")
    relation = await create_relation(db, family.id, elder.id)
    alert = await create_alert(db, care_relation_id=relation.id)

    elder_headers = await auth_headers(client, elder.openid)
    list_response = await client.get("/api/v1/alerts", headers=elder_headers)
    resolve_response = await client.put(f"/api/v1/alerts/{alert.id}/resolve", headers=elder_headers)

    assert list_response.status_code == 403
    assert resolve_response.status_code == 403
    await db.refresh(alert)
    assert alert.is_resolved is False


@pytest.mark.asyncio
async def test_check_in_is_elder_only(client, db):
    family = await create_user(db, "family-check-in-boundary", role="family")
    elder = await create_user(db, "elder-check-in-boundary", role="elder")

    family_response = await client.post(
        "/api/v1/users/check-in", headers=await auth_headers(client, family.openid)
    )
    elder_response = await client.post(
        "/api/v1/users/check-in", headers=await auth_headers(client, elder.openid)
    )

    assert family_response.status_code == 403
    assert elder_response.status_code == 200
