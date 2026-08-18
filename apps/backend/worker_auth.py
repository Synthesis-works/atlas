import hmac
import logging

from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.backend.config import settings

logger = logging.getLogger(__name__)

auth_scheme = HTTPBearer(auto_error=False)


def require_worker_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(auth_scheme),
) -> dict[str, bool]:
    """
    Authenticate requests to the internal worker API using a shared bearer
    token (WORKER_AUTH_TOKEN). Requests are rejected when the token is not
    configured or does not match.
    """
    expected = settings.worker_auth_token
    if not expected:
        logger.error("Worker auth is not configured (WORKER_AUTH_TOKEN unset); denying request.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker authentication is not configured",
        )

    provided = credentials.credentials if credentials else None
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid worker credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("Worker authentication passed.")
    return {"worker_authenticated": True}
