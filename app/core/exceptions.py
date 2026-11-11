"""app/core/exceptions.py
Enterprise Exception Hierarchy and Global Exception Handlers.

Every error that Atlas returns to a client follows the same JSON structure:
{
    "error": {
        "code": "MACHINE_READABLE_ERROR_CODE",
        "message": "Human-readable explanation.",
        "request_id": "uuid-from-middleware",
        "timestamp": "ISO 8601",
        "details": []      # only populated for validation errors
    }
}

This ensures API consumers can write ONE error-handling path, regardless of
whether the failure was a validation issue, a business rule, or a crash.
"""
from datetime import datetime, timezone
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import logger


# ---------------------------------------------------------------------------
# 1. Base Exception Class
# ---------------------------------------------------------------------------
class AtlasBaseException(Exception):
    """
    Root exception for all known Atlas domain errors.

    Subclass this for specific failure categories (auth, retrieval, etc.).
    Every subclass carries:
      - message:     Human-readable text returned to the client.
      - error_code:  Machine-readable code for programmatic handling.
      - status_code: HTTP status code to return.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "ATLAS_INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


# ---------------------------------------------------------------------------
# 2. Helper: Build a Uniform Error JSON Response
# ---------------------------------------------------------------------------
def _build_error_response(
    status_code: int,
    error_code: str,
    message: str,
    request: Request,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """
    Constructs the standardized error envelope.

    We pull request_id from request.state, which the
    RequestCorrelationMiddleware sets on every inbound request.
    If the middleware has not run (e.g., error during middleware init),
    we fall back to "unknown".
    """
    request_id = getattr(request.state, "request_id", "unknown")

    payload = {
        "error": {
            "code": error_code,
            "message": message,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or [],
        }
    }
    return JSONResponse(status_code=status_code, content=payload)


# ---------------------------------------------------------------------------
# 3. Global Exception Handlers (registered on the FastAPI app instance)
# ---------------------------------------------------------------------------

async def atlas_exception_handler(request: Request, exc: AtlasBaseException) -> JSONResponse:
    """
    Catches any AtlasBaseException (or subclass) that escapes a route handler.

    This is for KNOWN business-logic errors: unauthorized priority, entity
    not found, service unavailable, etc.
    """
    logger.warning(
        f"Business exception on {request.method} {request.url.path}: "
        f"[{exc.error_code}] {exc.message}"
    )
    return _build_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        request=request,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Catches Pydantic validation failures (wrong types, missing fields,
    constraint violations, extra fields).

    We reformat Pydantic's native error list into our standard shape
    so the client sees the same envelope structure.
    """
    formatted_errors = [
        {
            "field": " → ".join(str(loc) for loc in err["loc"]),
            "issue": err["msg"],
        }
        for err in exc.errors()
    ]
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: "
        f"{len(formatted_errors)} field(s) failed"
    )
    return _build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
        error_code="VALIDATION_FAILED",
        message="Request payload failed schema validation.",
        request=request,
        details=formatted_errors,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Last-resort handler for UNEXPECTED errors (bugs, infrastructure failures).

    Critical rule: NEVER expose the raw Python exception message or traceback
    to the client. Log it internally with the request_id, and return only
    the request_id so the user can quote it when reporting the issue.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.critical(
        f"Unhandled exception [request_id={request_id}] "
        f"on {request.method} {request.url.path}: {exc!r}",
        exc_info=True,
    )
    return _build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
        message=f"An unexpected internal error occurred. Reference: {request_id}",
        request=request,
    )
