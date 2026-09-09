"""Shared authenticated TestClient helper for agent API tests.

The `/api/v1/agent/*` endpoints require a valid Bearer JWT (P0 hardening).
Legacy test suites still exercise the API through a module-level
`client = TestClient(app)`; this helper lets them keep that shape while
signing a mock token per client.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from apps.backend.config import settings


def create_mock_jwt(
    user_id: str,
    *,
    organization_id: str | None = None,
    membership_id: str | None = None,
) -> str:
    """Build a JWT signed with the backend's auth secret for `user_id`."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "exp": now + timedelta(minutes=15),
        "iat": now,
        "jti": str(uuid4()),
    }
    if membership_id:
        payload["membership_id"] = membership_id
    if organization_id:
        payload["organization_id"] = organization_id
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class AuthenticatedTestClient(TestClient):
    """TestClient that injects an Authorization header on every request."""

    def __init__(
        self,
        app,
        *,
        user_id: str | None = None,
        organization_id: str | None = None,
        membership_id: str | None = None,
    ) -> None:
        super().__init__(app)
        self._token = create_mock_jwt(
            user_id or str(uuid4()),
            organization_id=organization_id,
            membership_id=membership_id,
        )

    def request(self, method: str, url: str, **kwargs):
        headers = kwargs.setdefault("headers", {})
        headers.setdefault("authorization", f"Bearer {self._token}")
        return super().request(method, url, **kwargs)
