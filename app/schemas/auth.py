"""app/schemas/auth.py
Pydantic v2 schemas for Authentication, Token Exchange, and User Principals.
"""
from typing import Literal
from pydantic import BaseModel, Field


# Standard roles aligned with Atlas enterprise dataset (data/novacore/atlas_users_rbac.csv)
EnterpriseRole = Literal[
    "admin",
    "executive",
    "security_admin",
    "manager",
    "finance_user",
    "hr_user",
    "employee"
]

EnterpriseDepartment = Literal[
    "Executive",
    "Finance",
    "Security",
    "Human Resources",
    "Engineering",
    "Product",
    "Marketing",
    "Sales",
    "Legal",
    "Customer Success",
    "Operations",
    "IT"
]


class LoginRequest(BaseModel):
    """Payload submitted to POST /api/v1/auth/login."""
    username: str = Field(..., min_length=3, max_length=50, examples=["marcus.vance"])
    password: str = Field(..., min_length=6, max_length=128, examples=["AtlasSecure2026!"])

    model_config = {"extra": "forbid"}


class TokenResponse(BaseModel):
    """Standard RFC 6749 OAuth2 Token Response."""
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in_seconds: int
    user_id: str
    role: EnterpriseRole
    department: EnterpriseDepartment


class UserPrincipal(BaseModel):
    """
    Authenticated User Identity injected into protected endpoints.
    Represents the verified claims carried by a valid JWT.
    """
    user_id: str = Field(..., description="Unique enterprise user identifier, e.g. USR-ADMIN-01")
    username: str
    role: EnterpriseRole
    access_level: str
    department: EnterpriseDepartment
    is_active: bool = True
