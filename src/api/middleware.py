"""Middleware for the MLX Whisper Server."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from ..core.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add logging."""
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())

        # Get request ID from headers or generate new one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Add to logging context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id
        )

        # Log request received
        logger.info(
            "Request received",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            request_id=request_id
        )

        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log response
            logger.info(
                "Request completed",
                status_code=response.status_code,
                process_time_ms=int(process_time * 1000),
                request_id=request_id
            )

            # Add headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as e:
            process_time = time.time() - start_time

            # Log error
            logger.error(
                "Request failed",
                error=str(e),
                process_time_ms=int(process_time * 1000),
                exc_info=True,
                request_id=request_id
            )

            raise


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS middleware for cross-origin requests."""

    def __init__(
        self,
        app,
        allow_origins: list[str] | None = None,
        allow_credentials: bool = True,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
    ):
        """Initialize CORS middleware.

        Args:
            app: FastAPI app
            allow_origins: List of allowed origins
            allow_credentials: Whether to allow credentials
            allow_methods: List of allowed methods
            allow_headers: List of allowed headers
        """
        super().__init__(app)

        self.allow_origins = allow_origins or ["*"]
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-Correlation-ID"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with CORS headers."""
        response = await call_next(request)

        # Add CORS headers
        origin = request.headers.get("origin")

        # Check if origin is allowed
        if self.allow_origins == ["*"] or origin in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin or "*"

        response.headers["Access-Control-Allow-Credentials"] = str(self.allow_credentials).lower()
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)

        # Handle preflight requests
        if request.method == "OPTIONS":
            response.status_code = 200
            return response

        return response


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce request size limits."""

    def __init__(self, app, max_request_size: int = 25 * 1024 * 1024):  # 25MB
        """Initialize request size middleware.

        Args:
            app: FastAPI app
            max_request_size: Maximum request size in bytes
        """
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check request size before processing."""
        # Note: This is a simplified implementation
        # In practice, you would need to check the Content-Length header
        # or stream the request body to check size

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_request_size:
                    logger.warning(
                        "Request too large",
                        content_length=length,
                        max_size=self.max_request_size
                    )
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "message": f"Request too large: {length} bytes (max: {self.max_request_size} bytes)",
                                "type": "request_too_large",
                                "code": "413"
                            }
                        }
                    )
            except ValueError:
                pass

        return await call_next(request)
