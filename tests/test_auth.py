"""tests/test_auth.py
Comprehensive integration tests for Milestone 2:
Authentication, JWT Validation, Role-Based Access Control (RBAC), and Departmental Boundaries.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import create_access_token


@pytest.fixture
def transport():
    return ASGITransport(app=app)


# =====================================================================
# Test 1: Successful Login & JWT Issuance
# =====================================================================
@pytest.mark.asyncio
async def test_login_success(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "marcus.vance", "password": "AtlasSecure2026!"}
        )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] == "USR-ADMIN-01"
    assert data["role"] == "admin"
    assert data["department"] == "Executive"


# =====================================================================
# Test 2: Failed Login — Invalid Password
# =====================================================================
@pytest.mark.asyncio
async def test_login_invalid_password(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "marcus.vance", "password": "WrongPassword123!"}
        )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


# =====================================================================
# Test 3: Failed Login — Non-Existent User
# =====================================================================
@pytest.mark.asyncio
async def test_login_unknown_user(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "unknown.ghost", "password": "AnyPassword123!"}
        )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


# =====================================================================
# Test 4: Missing Bearer Token on Protected Endpoint
# =====================================================================
@pytest.mark.asyncio
async def test_protected_route_missing_token(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_REQUIRED"


# =====================================================================
# Test 5: Forged / Tampered JWT
# =====================================================================
@pytest.mark.asyncio
async def test_protected_route_tampered_token(transport):
    forged_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMifQ.invalidsignaturehere"
    headers = {"Authorization": f"Bearer {forged_token}"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_TOKEN"


# =====================================================================
# Test 6: Valid Token Authentication on /me
# =====================================================================
@pytest.mark.asyncio
async def test_profile_with_valid_token(transport):
    token, _ = create_access_token(
        user_id="USR-EXEC-01",
        username="elena.rostova",
        role="executive",
        department="Finance",
        access_level="management"
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "USR-EXEC-01"
    assert data["role"] == "executive"
    assert data["department"] == "Finance"


# =====================================================================
# Test 7: RBAC — Executive Role Access to Confidential Briefing
# =====================================================================
@pytest.mark.asyncio
async def test_rbac_executive_briefing_granted(transport):
    token, _ = create_access_token(
        user_id="USR-EXEC-01",
        username="elena.rostova",
        role="executive",
        department="Finance"
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/executive-briefing", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confidential_briefing_granted"


# =====================================================================
# Test 8: RBAC — Employee Role Denied Access (403 Forbidden)
# =====================================================================
@pytest.mark.asyncio
async def test_rbac_executive_briefing_denied_for_employee(transport):
    token, _ = create_access_token(
        user_id="USR-EMP-01",
        username="general.employee",
        role="employee",
        department="Product"
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/executive-briefing", headers=headers)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"


# =====================================================================
# Test 9: Department Isolation — Engineering Granted Access
# =====================================================================
@pytest.mark.asyncio
async def test_department_engineering_granted(transport):
    token, _ = create_access_token(
        user_id="USR-ENG-01",
        username="engineer.lead",
        role="manager",
        department="Engineering"
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/engineering-vault", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "engineering_vault_unlocked"


# =====================================================================
# Test 10: Department Isolation — Product Department Denied Access
# =====================================================================
@pytest.mark.asyncio
async def test_department_product_denied(transport):
    token, _ = create_access_token(
        user_id="USR-EMP-01",
        username="general.employee",
        role="employee",
        department="Product"
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/engineering-vault", headers=headers)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "DEPARTMENT_ACCESS_RESTRICTED"


# =====================================================================
# Test 11: Admin Superuser Bypass on Department Isolation
# =====================================================================
@pytest.mark.asyncio
async def test_admin_bypasses_department_isolation(transport):
    # Admin is in 'Executive' department, but can access 'Engineering' vault
    token, _ = create_access_token(
        user_id="USR-ADMIN-01",
        username="marcus.vance",
        role="admin",
        department="Executive"
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/engineering-vault", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "engineering_vault_unlocked"
