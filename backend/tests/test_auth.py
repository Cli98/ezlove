import unittest
import uuid

from jose import jwt

from app.config import settings
from app.services.auth import create_refresh_token


class AuthTokenTest(unittest.TestCase):
    def test_worker_claims_cannot_override_refresh_type(self):
        token = create_refresh_token(uuid.uuid4(), {"type": "worker"})
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        self.assertEqual(payload["type"], "refresh")


if __name__ == "__main__":
    unittest.main()
