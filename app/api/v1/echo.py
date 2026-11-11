"""app/api/v1/echo.py
Echo Check endpoint — demonstrates Pydantic validation, business-rule
enforcement, custom exception handling, and request-ID propagation.

Request Flow:
  1. Client sends POST /api/v1/echo-check with JSON body.
  2. RequestCorrelationMiddleware assigns X-Request-ID.
  3. Pydantic validates the body against EchoCheckRequest.
     - If invalid → validation_exception_handler returns 422.
  4. This handler runs business logic checks.
     - If priority 5 + non-Executive → AtlasBaseException returns 403.
  5. On success → returns EchoCheckResponse with 200.
"""
from fastapi import APIRouter, Request

from app.core.exceptions import AtlasBaseException
from app.schemas.echo import EchoCheckRequest, EchoCheckResponse

router = APIRouter(tags=["Echo Check (Milestone 1)"])


@router.post(
    "/echo-check",
    response_model=EchoCheckResponse,
    status_code=200,
    summary="Validate and echo a query payload",
    description=(
        "Accepts a query with department and priority, validates the payload "
        "against schema constraints and business rules, and returns the "
        "accepted query with its correlation request ID."
    ),
)
async def echo_check(payload: EchoCheckRequest, request: Request):
    """
    Business rule:
      Priority 5 queries are restricted to the Executive department.
      This is NOT a schema constraint — it is a domain-level authorization
      rule. Therefore it returns 403 (Forbidden), not 422 (Validation Error).

    The request_id is read from request.state, which was set by
    RequestCorrelationMiddleware. We use getattr with a fallback in case
    the middleware did not run (defensive programming).
    """

    # --- Business Rule: Priority 5 is Executive-only ---
    if payload.priority == 5 and payload.department != "Executive":
        raise AtlasBaseException(
            message="Priority 5 queries are restricted to Executive department.",
            error_code="UNAUTHORIZED_PRIORITY_LEVEL",
            status_code=403,
        )

    # --- Extract request ID (set by middleware) ---
    request_id = getattr(request.state, "request_id", "unknown")

    return EchoCheckResponse(
        query=payload.query,
        status="accepted",
        request_id=request_id,
    )
