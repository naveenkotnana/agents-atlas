"""app/core/middleware.py
Request Correlation & Timing Middleware.

Responsibilities:
  1. Assign a unique request_id to every inbound HTTP request.
  2. Validate client-supplied X-Request-ID (format + length check).
  3. Measure wall-clock processing time for the full request lifecycle.
  4. Inject X-Request-ID and X-Process-Time-MS into every outgoing response.
  5. Log structured ingress/egress lines for every request.
"""
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import logger


# Regex that accepts UUIDv4 or any alphanumeric-dash-underscore string up to 64 chars.
# This prevents clients from injecting log-forging payloads via X-Request-ID.
_VALID_REQUEST_ID = re.compile(r"^[a-zA-Z0-9\-_]{1,64}$")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that:
      - Extracts or generates a request ID.
      - Validates client-supplied IDs against a safe pattern.
      - Stores the ID in request.state for use by route handlers
        and exception handlers.
      - Measures and injects processing time.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # --- 1. Extract or generate request ID ---
        client_id = request.headers.get("X-Request-ID", "")
        if client_id and _VALID_REQUEST_ID.match(client_id):
            req_id = client_id
        else:
            req_id = str(uuid.uuid4())

        # Store on request.state so handlers and exception handlers can read it
        request.state.request_id = req_id

        # --- 2. Start timing ---
        start = time.perf_counter()

        logger.info(
            f"[{req_id}] → {request.method} {request.url.path}"
        )

        # --- 3. Execute the route handler (and everything downstream) ---
        try:
            response = await call_next(request)
        except Exception as exc:
            # If an unhandled error blows up before reaching our exception
            # handlers, we still log the timing and re-raise.
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                f"[{req_id}] ✗ {request.method} {request.url.path} "
                f"crashed after {elapsed_ms}ms: {exc!r}"
            )
            raise

        # --- 4. Inject response headers ---
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Process-Time-MS"] = str(elapsed_ms)

        logger.info(
            f"[{req_id}] ← {request.method} {request.url.path} "
            f"status={response.status_code} in {elapsed_ms}ms"
        )

        return response
