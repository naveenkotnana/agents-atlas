"""app/api/v1/reliability.py
Endpoints demonstrating Rate Limiting, Idempotency, and Circuit Breaking.
"""
from fastapi import APIRouter, Request, Header, status
from fastapi.responses import JSONResponse

from app.core.rate_limiter import standard_rate_limiter, heavy_query_rate_limiter
from app.core.idempotency import idempotency_manager
from app.core.circuit_breaker import ollama_circuit_breaker
from app.core.exceptions import AtlasBaseException
from app.schemas.reliability import IdempotentTaskRequest, CircuitBreakerStatusResponse

router = APIRouter(prefix="/reliability", tags=["API Reliability (Milestone 3)"])


@router.get("/rate-limited-endpoint")
async def rate_limited_endpoint(request: Request):
    """
    Demonstrates Sliding Window Rate Limiting.
    Allows 60 requests per minute per IP.
    """
    await standard_rate_limiter.check_rate_limit(request)
    return {
        "status": "request_allowed",
        "rate_limit_limit": request.state.rate_limit_limit,
        "rate_limit_remaining": request.state.rate_limit_remaining
    }


@router.post("/idempotent-task")
async def execute_idempotent_task(
    payload: IdempotentTaskRequest,
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key")
):
    """
    Demonstrates Idempotent Mutating Execution.
    If 'Idempotency-Key' is supplied:
      - First call: executes and caches the response.
      - Concurrent duplicate: returns 409 Conflict.
      - Subsequent identical calls: returns cached result with X-Cache-Lookup: HIT.
    """
    if idempotency_key:
        lock_status, record = await idempotency_manager.get_or_lock(idempotency_key)

        if lock_status == "COMPLETED" and record:
            return JSONResponse(
                status_code=record.status_code,
                content=record.response_body,
                headers={"X-Cache-Lookup": "HIT", "Idempotency-Key": idempotency_key}
            )

        if lock_status == "IN_PROGRESS":
            raise AtlasBaseException(
                message=f"Request with Idempotency-Key '{idempotency_key}' is currently being processed.",
                error_code="IDEMPOTENCY_CONFLICT",
                status_code=status.HTTP_409_CONFLICT
            )

    # Execute simulated heavy task
    result_data = {
        "action": payload.action,
        "execution_status": "executed_successfully",
        "processed_items": len(payload.payload)
    }

    if idempotency_key:
        await idempotency_manager.complete(idempotency_key, 200, result_data)

    return JSONResponse(
        status_code=200,
        content=result_data,
        headers={"X-Cache-Lookup": "MISS"}
    )


@router.get("/circuit-breaker/status", response_model=CircuitBreakerStatusResponse)
async def get_circuit_breaker_status():
    """Returns live telemetry of the Ollama downstream circuit breaker."""
    return CircuitBreakerStatusResponse(
        service_name=ollama_circuit_breaker.name,
        state=ollama_circuit_breaker.state.value,
        consecutive_failures=ollama_circuit_breaker.consecutive_failures,
        failure_threshold=ollama_circuit_breaker.failure_threshold,
        cooldown_seconds=ollama_circuit_breaker.recovery_cooldown_seconds
    )


@router.post("/circuit-breaker/simulate-call")
async def simulate_downstream_call(fail: bool = False):
    """
    Simulates calling a downstream service (e.g. Ollama LLM) through
    the circuit breaker safety shield.
    """
    async def downstream_action():
        if fail:
            raise ConnectionError("Ollama daemon unreachable on port 11434")
        return {"ollama_response": "Decision synthesized successfully."}

    result = await ollama_circuit_breaker.execute(downstream_action)
    return result
