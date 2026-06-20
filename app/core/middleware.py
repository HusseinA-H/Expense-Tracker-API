import time
import uuid
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger("app.middleware")

class LoggingAndRequestIdMiddleware:
    """Pure ASGI Middleware for X-Request-ID injection and structured request/response logging."""
    
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        
        # Parse headers from scope (headers keys in ASGI scope are lowercase bytes)
        headers = dict(scope.get("headers", []))
        
        request_id_bytes = headers.get(b"x-request-id")
        request_id = request_id_bytes.decode("utf-8") if request_id_bytes else f"req_{uuid.uuid4().hex[:12]}"

        # Get user agent
        user_agent_bytes = headers.get(b"user-agent")
        user_agent = user_agent_bytes.decode("utf-8") if user_agent_bytes else None

        # Get client IP address (check X-Forwarded-For first for reverse proxy setup)
        x_forwarded_for = headers.get(b"x-forwarded-for")
        if x_forwarded_for:
            ip_address = x_forwarded_for.decode("utf-8").split(",")[0].strip()
        else:
            client = scope.get("client")
            ip_address = client[0] if client else None

        # Bind request_id, ip_address, and user_agent to structlog context variables
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        path = scope.get("path", "")
        method = scope.get("method", "")
        query_string = scope.get("query_string", b"").decode("utf-8")
        
        logger.info(
            "Request started",
            method=method,
            path=path,
            query_params=query_string
        )
        
        status_code = [200]  # mutable list to capture response status in closure

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message.get("status", 200)
                headers_list = message.get("headers", [])
                headers_list.append((b"x-request-id", request_id.encode("utf-8")))
                message["headers"] = headers_list
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(
                "Request failed",
                method=method,
                path=path,
                duration_sec=round(duration, 4),
                error=str(e)
            )
            raise e
            
        duration = time.perf_counter() - start_time
        
        logger.info(
            "Request finished",
            method=method,
            path=path,
            status_code=status_code[0],
            duration_sec=round(duration, 4)
        )
