from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer
import logging

logger = logging.getLogger(__name__)

auth_scheme = HTTPBearer(auto_error=False)

def require_worker_auth(request: Request, token=Security(auth_scheme)):
    """
    Stub WorkerAuthenticator.
    In a real implementation, this would validate mTLS, a signed JWT,
    or a Service Identity token from the worker infrastructure.
    For now, it accepts all requests but logs that the check occurred.
    """
    logger.debug("Worker authentication check passed (STUB).")
    return {"worker_authenticated": True}
