import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject request_id and correlation_id into the request state and structlog context.
    - request_id: Unique for every incoming request.
    - correlation_id: Inherited from headers if passed, otherwise equals request_id.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id", request_id)
        
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        
        # Bind to structured logger context
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id
        )
        
        response = await call_next(request)
        
        # Optionally attach them to response headers
        response.headers["x-request-id"] = request_id
        response.headers["x-correlation-id"] = correlation_id
        
        # Unbind or clear context vars
        structlog.contextvars.clear_contextvars()
        
        return response
