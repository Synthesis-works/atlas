import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from apps.backend.core.telemetry import (
    set_correlation_id, get_correlation_id, reset_correlation_id,
    set_trace_id, get_trace_id, reset_trace_id,
    set_span_id, get_span_id, reset_span_id,
    generate_uuidv7
)

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject correlation_id, trace_id, and span_id into contextvars.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        
        # Resolve Correlation ID
        incoming_correlation_id = request.headers.get("x-correlation-id")
        correlation_id = incoming_correlation_id if incoming_correlation_id else generate_uuidv7()
        
        # Resolve Trace ID
        incoming_trace_id = request.headers.get("x-trace-id")
        trace_id = incoming_trace_id if incoming_trace_id else correlation_id
        
        # Span ID is unique to this request span
        span_id = generate_uuidv7()
        
        cor_token = set_correlation_id(correlation_id)
        trc_token = set_trace_id(trace_id)
        spn_token = set_span_id(span_id)
        
        request.state.correlation_id = correlation_id
        request.state.trace_id = trace_id
        
        try:
            # Start response cycle
            response = await call_next(request)
            
            # Attach to outgoing headers
            response.headers["x-correlation-id"] = correlation_id
            response.headers["x-trace-id"] = trace_id
            
            return response
        finally:
            reset_correlation_id(cor_token)
            reset_trace_id(trc_token)
            reset_span_id(spn_token)
