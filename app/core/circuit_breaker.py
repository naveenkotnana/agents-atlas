"""app/core/circuit_breaker.py
Finite-State Circuit Breaker Pattern.

Protects Atlas from cascading failures when downstream dependencies
(Ollama local LLM runner, external vector databases, or MCP servers)
experience latency spikes, deadlocks, or outages.

States:
  - CLOSED:    Healthy; calls pass through to downstream.
  - OPEN:      Tripped; fast-fails instantly in <1ms without network calls.
  - HALF_OPEN: Probe; allows a single test call to verify dependency recovery.
"""
import time
import asyncio
from typing import Callable, Any
from enum import Enum
from fastapi import status
from app.core.exceptions import AtlasBaseException
from app.core.logging import logger


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(AtlasBaseException):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""
    def __init__(self, service_name: str, cooldown_remaining: float):
        super().__init__(
            message=(
                f"Downstream service '{service_name}' is temporarily unavailable "
                f"(circuit breaker is OPEN). Retry in {round(cooldown_remaining, 1)}s."
            ),
            error_code="CIRCUIT_BREAKER_OPEN",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class CircuitBreaker:
    """
    Thread-safe asynchronous circuit breaker.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_cooldown_seconds: float = 15.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_cooldown_seconds = recovery_cooldown_seconds

        self.state: CircuitState = CircuitState.CLOSED
        self.consecutive_failures: int = 0
        self.last_state_change: float = time.monotonic()
        self._lock = asyncio.Lock()

    async def execute(self, coroutine_func: Callable[[], Any]) -> Any:
        """
        Executes the coroutine through the circuit breaker safety shield.
        """
        now = time.monotonic()

        async with self._lock:
            # 1. Check if OPEN circuit has cooled down enough to transition to HALF_OPEN
            if self.state == CircuitState.OPEN:
                elapsed = now - self.last_state_change
                if elapsed >= self.recovery_cooldown_seconds:
                    logger.info(
                        f"CircuitBreaker[{self.name}] cooldown expired. Transitioning OPEN → HALF_OPEN."
                    )
                    self.state = CircuitState.HALF_OPEN
                    self.last_state_change = now
                else:
                    cooldown_remaining = self.recovery_cooldown_seconds - elapsed
                    raise CircuitBreakerOpenException(self.name, cooldown_remaining)

        # 2. Execute downstream call
        try:
            result = await coroutine_func()
            await self._on_success()
            return result
        except Exception as exc:
            # Do not count client-side logic errors against downstream health
            if not isinstance(exc, AtlasBaseException) or exc.status_code >= 500:
                await self._on_failure(exc)
            raise exc

    async def _on_success(self):
        """Resets the breaker to CLOSED state on a successful call."""
        async with self._lock:
            if self.state != CircuitState.CLOSED:
                logger.info(
                    f"CircuitBreaker[{self.name}] service recovered. Transitioning {self.state} → CLOSED."
                )
            self.state = CircuitState.CLOSED
            self.consecutive_failures = 0

    async def _on_failure(self, exc: Exception):
        """Records a failure and trips the breaker to OPEN if threshold is breached."""
        async with self._lock:
            self.consecutive_failures += 1
            now = time.monotonic()
            logger.warning(
                f"CircuitBreaker[{self.name}] recorded failure ({self.consecutive_failures}/{self.failure_threshold}): {exc!r}"
            )

            if self.consecutive_failures >= self.failure_threshold:
                if self.state != CircuitState.OPEN:
                    logger.critical(
                        f"CircuitBreaker[{self.name}] threshold reached. Tripping {self.state} → OPEN!"
                    )
                self.state = CircuitState.OPEN
                self.last_state_change = now


# Global circuit breakers for downstream services
ollama_circuit_breaker = CircuitBreaker("Ollama_LLM_Runner", failure_threshold=3, recovery_cooldown_seconds=10.0)
database_circuit_breaker = CircuitBreaker("PostgreSQL_VectorDB", failure_threshold=5, recovery_cooldown_seconds=15.0)
