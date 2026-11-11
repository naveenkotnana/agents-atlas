"""app/api/v1/auth.py
Authentication endpoints: Login, Token Verification, and Role Guard demonstrations.
"""
from fastapi import APIRouter, Depends, status

from app.core.exceptions import AtlasBaseException
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_role,
    require_department
)
from app.schemas.auth import LoginRequest, TokenResponse, UserPrincipal

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control (Milestone 2)"])

# ---------------------------------------------------------------------------
# Seed Enterprise Users (From data/novacore/atlas_users_rbac.csv)
# ---------------------------------------------------------------------------
DEMO_PASSWORD = "AtlasSecure2026!"
DEMO_PASSWORD_HASH = hash_password(DEMO_PASSWORD)

MOCK_USER_STORE: dict[str, dict] = {
    "marcus.vance": {
        "user_id": "USR-ADMIN-01",
        "employee_id": "EMP-00001",
        "username": "marcus.vance",
        "role": "admin",
        "access_level": "admin",
        "department": "Executive",
        "hashed_password": DEMO_PASSWORD_HASH
    },
    "elena.rostova": {
        "user_id": "USR-EXEC-01",
        "employee_id": "EMP-00002",
        "username": "elena.rostova",
        "role": "executive",
        "access_level": "management",
        "department": "Finance",
        "hashed_password": DEMO_PASSWORD_HASH
    },
    "engineer.lead": {
        "user_id": "USR-ENG-01",
        "employee_id": "EMP-00045",
        "username": "engineer.lead",
        "role": "manager",
        "access_level": "manager",
        "department": "Engineering",
        "hashed_password": DEMO_PASSWORD_HASH
    },
    "general.employee": {
        "user_id": "USR-EMP-01",
        "employee_id": "EMP-00100",
        "username": "general.employee",
        "role": "employee",
        "access_level": "employee",
        "department": "Product",
        "hashed_password": DEMO_PASSWORD_HASH
    }
}


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive an enterprise JWT"
)
async def login(credentials: LoginRequest):
    """
    Authenticates an enterprise user using username and password.
    Returns a signed JWT bearer token containing role and department claims.
    """
    user_record = MOCK_USER_STORE.get(credentials.username)
    if not user_record or not verify_password(credentials.password, user_record["hashed_password"]):
        raise AtlasBaseException(
            message="Invalid username or password.",
            error_code="INVALID_CREDENTIALS",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    token, expires_in = create_access_token(
        user_id=user_record["user_id"],
        username=user_record["username"],
        role=user_record["role"],
        department=user_record["department"],
        access_level=user_record["access_level"]
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=expires_in,
        user_id=user_record["user_id"],
        role=user_record["role"],
        department=user_record["department"]
    )


@router.get(
    "/me",
    response_model=UserPrincipal,
    summary="Get verified identity claims from current JWT"
)
async def get_current_user_profile(
    current_user: UserPrincipal = Depends(get_current_user)
):
    """Protected endpoint: Returns the caller's verified UserPrincipal claims."""
    return current_user


@router.get(
    "/executive-briefing",
    summary="Executive & Admin only confidential briefing"
)
async def get_executive_briefing(
    current_user: UserPrincipal = Depends(require_role(["admin", "executive"]))
):
    """
    RBAC Protected: Accessible strictly to 'admin' and 'executive' roles.
    Returns 403 Forbidden for managers and general employees.
    """
    return {
        "status": "confidential_briefing_granted",
        "authorized_user": current_user.username,
        "role": current_user.role,
        "executive_memo": "Projected 2026 AI Infrastructure ROI is 340%. M&A due diligence active."
    }


@router.get(
    "/engineering-vault",
    summary="Engineering department isolated resource"
)
async def get_engineering_vault(
    current_user: UserPrincipal = Depends(require_department(["Engineering"]))
):
    """
    Department Isolated: Accessible only to members of the Engineering department
    (or system admins). Returns 403 Forbidden for members of Sales, Finance, etc.
    """
    return {
        "status": "engineering_vault_unlocked",
        "user": current_user.username,
        "department": current_user.department,
        "internal_host": "k8s-cluster-primary.internal.atlas"
    }
