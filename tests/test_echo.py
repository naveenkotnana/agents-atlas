"""tests/test_echo.py
Comprehensive tests for the Echo Check endpoint.

Covers:
  1. Valid requests (happy path)
  2. Business rule enforcement (priority 5 + non-Executive)
  3. Pydantic schema validation (invalid department, out-of-range priority,
     query too short, query too long, unexpected fields)

Each test documents WHAT it tests and WHY that scenario matters.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def transport():
    """ASGI transport that runs requests through the full FastAPI stack."""
    return ASGITransport(app=app)


# =====================================================================
# Test 1: Valid request — Engineering, priority 3
# =====================================================================
@pytest.mark.asyncio
async def test_valid_engineering_request(transport):
    """
    Happy path: well-formed payload with a standard department and priority.
    Expected: 200 OK with status "accepted" and a request_id.
    """
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/echo-check",
            json={
                "query": "Explain hybrid retrieval",
                "department": "Engineering",
                "priority": 3,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Explain hybrid retrieval"
    assert data["status"] == "accepted"
    assert "request_id" in data
    assert len(data["request_id"]) > 0

    # Verify the middleware injected X-Request-ID into response headers
    assert "x-request-id" in response.headers
    assert "x-process-time-ms" in response.headers


# =====================================================================
# Test 2: Valid request — Executive, priority 5
# =====================================================================
@pytest.mark.asyncio
async def test_valid_executive_priority_5(transport):
    """
    Executive department IS allowed priority 5.
    Expected: 200 OK.
    """
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/echo-check",
            json={
                "query": "Approve Q4 budget allocation",
                "department": "Executive",
                "priority": 5,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["query"] == "Approve Q4 budget allocation"


# =====================================================================
# Test 3: Business rule — Sales + priority 5 → 403
# =====================================================================
@pytest.mark.asyncio
async def test_unauthorized_priority_level(transport):
    """
    Priority 5 is restricted to Executive department.
    Sales + priority 5 must be rejected with 403 and the correct error code.
    """
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/echo-check",
            json={
                "query": "Urgent sales pipeline review",
                "department": "Sales",
                "priority": 5,
            },
        )

    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED_PRIORITY_LEVEL"
    assert "Priority 5" in data["error"]["message"]
    assert "request_id" in data["error"]


# =====================================================================
# Test 4: Invalid department — "Marketing" is not in the allowlist
# =====================================================================
@pytest.mark.asyncio
async def test_invalid_department(transport):
    """
    "Marketing" is not one of the four allowed departments.
    Pydantic Literal validation rejects it with 422.
    """
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/echo-check",
            json={
                "query": "Review campaign ROI",
                "department": "Marketing",
                "priority": 2,
            },
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_FAILED"
    assert any("department" in d["field"] for d in data["error"]["details"])


# =====================================================================
# Test 5: Invalid priority — 6 exceeds the maximum of 5
# =====================================================================
@pytest.mark.asyncio
async def test_invalid_priority_too_high(transport):
    """
    Priority must be between 1 and 5. 6 is out of range → 422.
    """
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/echo-check",
            json={
                "query": "Check server status",
                "department": "Engineering",
                "priority": 6,
            },
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_FAILED"
    assert any("priority" in d["field"] for d in data["error"]["details"])


# =====================================================================
# Test 6: Query too short — less than 3 characters
# =====================================================================
@pytest.mark.asyncio
async def test_query_too_short(transport):
    """
    Query minimum length is 3 characters. "Hi" (2 chars) → 422.
    """
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/echo-check",
            json={
                "query": "Hi",
                "department": "Legal",
                "priority": 1,
            },
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_FAILED"
    assert any("query" in d["field"] for d in data["error"]["details"])


# =====================================================================
# Test 7: Query too long — exceeds 200 characters
# =====================================================================
@pytest.mark.asyncio
async def test_query_too_long(transport):
    """
    Query maximum length is 200 characters. A 201-char string → 422.
    """
    long_query = "A" * 201
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/echo-check",
            json={
                "query": long_query,
                "department": "Engineering",
                "priority": 2,
            },
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_FAILED"
    assert any("query" in d["field"] for d in data["error"]["details"])


# =====================================================================
# Test 8: Unexpected field — extra fields must be rejected
# =====================================================================
@pytest.mark.asyncio
async def test_unexpected_extra_field(transport):
    """
    model_config extra="forbid" means unknown fields cause a 422.
    This prevents clients from injecting arbitrary data like {"admin": true}.
    """
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/echo-check",
            json={
                "query": "Normal query",
                "department": "Engineering",
                "priority": 2,
                "admin": True,  # <-- unexpected field
            },
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_FAILED"
    assert any("admin" in d["field"] for d in data["error"]["details"])
