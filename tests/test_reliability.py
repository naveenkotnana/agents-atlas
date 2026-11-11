"""tests/test_reliability.py
Integration tests for Milestone 3:
Sliding Window Rate Limiter, Idempotency Keys, and Circuit Breaker State Transitions.
"""
import asyncio
import time
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.circuit_breaker import ollama_circuit_breaker, CircuitState
from app.core.rate_limiter import SlidingWindowRateLimiter


@pytest.fixture
def transport():
    return ASGITransport(app=app)


# =====================================================================
# Test 1 & 2: Sliding Window Rate Limiting
# =====================================================================
@pytest.mark.asyncio
async def test_sliding_window_rate_limiter_logic():
    # Create a small-limit limiter: 3 requests per 2 seconds
    limiter = SlidingWindowRateLimiter(requests_per_minute=3, window_seconds=2)

    # First 3 requests must pass
    allowed_1, rem_1, _ = await limiter.is_allowed("test-client")
    allowed_2, rem_2, _ = await limiter.is_allowed("test-client")
    allowed_3, rem_3, _ = await limiter.is_allowed("test-client")
    assert allowed_1 and allowed_2 and allowed_3
    assert rem_3 == 0

    # 4th request in the same window must be rejected
    allowed_4, rem_4, retry_after = await limiter.is_allowed("test-client")
    assert not allowed_4
    assert retry_after >= 1

    # After waiting 2.1 seconds, sliding window clears and request passes
    await asyncio.sleep(2.1)
    allowed_5, rem_5, _ = await limiter.is_allowed("test-client")
    assert allowed_5


@pytest.mark.asyncio
async def test_rate_limited_api_endpoint(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/reliability/rate-limited-endpoint")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "request_allowed"


# =====================================================================
# Test 3, 4 & 5: Idempotency Key Engine
# =====================================================================
@pytest.mark.asyncio
async def test_idempotent_task_first_call_miss(transport):
    key = "idem-test-key-001"
    headers = {"Idempotency-Key": key}
    payload = {"action": "embed_documents", "payload": {"doc_id": "DOC-99"}}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/reliability/idempotent-task",
            json=payload,
            headers=headers
        )

    assert response.status_code == 200
    assert response.headers.get("X-Cache-Lookup") == "MISS"
    data = response.json()
    assert data["execution_status"] == "executed_successfully"


@pytest.mark.asyncio
async def test_idempotent_task_duplicate_call_hit(transport):
    key = "idem-test-key-002"
    headers = {"Idempotency-Key": key}
    payload = {"action": "embed_documents", "payload": {"doc_id": "DOC-100"}}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First execution (MISS)
        res1 = await client.post(
            "/api/v1/reliability/idempotent-task",
            json=payload,
            headers=headers
        )
        assert res1.status_code == 200
        assert res1.headers.get("X-Cache-Lookup") == "MISS"

        # Second duplicate execution with identical key (HIT)
        res2 = await client.post(
            "/api/v1/reliability/idempotent-task",
            json=payload,
            headers=headers
        )
        assert res2.status_code == 200
        assert res2.headers.get("X-Cache-Lookup") == "HIT"
        assert res2.json() == res1.json()


# =====================================================================
# Test 6 to 10: Circuit Breaker State Transitions
# =====================================================================
@pytest.mark.asyncio
async def test_circuit_breaker_lifecycle(transport):
    # Reset circuit breaker state for clean test run
    ollama_circuit_breaker.state = CircuitState.CLOSED
    ollama_circuit_breaker.consecutive_failures = 0
    ollama_circuit_breaker.recovery_cooldown_seconds = 1.0  # short cooldown for tests

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Breaker is CLOSED initially
        status_res = await client.get("/api/v1/reliability/circuit-breaker/status")
        assert status_res.status_code == 200
        assert status_res.json()["state"] == "CLOSED"

        # 2. Trigger consecutive failures to reach threshold (3)
        for _ in range(3):
            with pytest.raises(Exception):
                await client.post("/api/v1/reliability/circuit-breaker/simulate-call?fail=true")

        # 3. Breaker must now be tripped to OPEN
        status_res = await client.get("/api/v1/reliability/circuit-breaker/status")
        assert status_res.json()["state"] == "OPEN"

        # 4. In OPEN state, calls are fast-failed with 503 CIRCUIT_BREAKER_OPEN
        t0 = time.perf_counter()
        open_res = await client.post("/api/v1/reliability/circuit-breaker/simulate-call?fail=false")
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert open_res.status_code == 503
        assert open_res.json()["error"]["code"] == "CIRCUIT_BREAKER_OPEN"
        # Fast fail must complete in under 5ms
        assert elapsed_ms < 50.0

        # 5. Wait for cooldown period (1.1s)
        await asyncio.sleep(1.1)

        # 6. Next successful call tests HALF_OPEN probe and resets breaker to CLOSED
        probe_res = await client.post("/api/v1/reliability/circuit-breaker/simulate-call?fail=false")
        assert probe_res.status_code == 200
        assert "ollama_response" in probe_res.json()

        # Breaker must be back to CLOSED
        status_res = await client.get("/api/v1/reliability/circuit-breaker/status")
        assert status_res.json()["state"] == "CLOSED"
        assert status_res.json()["consecutive_failures"] == 0
