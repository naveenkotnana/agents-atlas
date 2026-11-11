"""app/schemas/reliability.py
Pydantic schemas for Reliability telemetry and idempotency checks.
"""
from typing import Any
from pydantic import BaseModel, Field


class IdempotentTaskRequest(BaseModel):
    """Mutating task requiring idempotency guarantee."""
    action: str = Field(..., description="Action name, e.g. 'embed_document_batch'")
    payload: dict[str, Any] = Field(default_factory=dict)


class CircuitBreakerStatusResponse(BaseModel):
    """Telemetry report of active downstream circuit breakers."""
    service_name: str
    state: str
    consecutive_failures: int
    failure_threshold: int
    cooldown_seconds: float
