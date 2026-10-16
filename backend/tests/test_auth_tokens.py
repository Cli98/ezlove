from uuid import uuid4

from jose import jwt

from app.config import settings
from app.services.auth import create_refresh_token


def test_refresh_token_reserved_claims_cannot_be_overridden():
    user_id = uuid4()
    token = create_refresh_token(
        user_id,
        extra_claims={"sub": "wrong-user", "type": "worker", "community_id": "community-1"},
    )

    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert payload["community_id"] == "community-1"
