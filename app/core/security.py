"""app/core/security.py
Cryptographic primitives, JWT token management, and RBAC FastAPI dependencies.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Sequence
import bcrypt
import jwt
from fastapi import Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.core.exceptions import AtlasBaseException
from app.schemas.auth import UserPrincipal, EnterpriseRole

# Reusable HTTP Bearer security scheme for OpenAPI documentation
bearer_scheme = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60


# ---------------------------------------------------------------------------
# 1. Password Hashing (Bcrypt)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with a randomized 128-bit salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a password against its bcrypt hash in constant time."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 2. JWT Minting & Decoding (PyJWT)
# ---------------------------------------------------------------------------

def create_access_token(
    user_id: str,
    username: str,
    role: str,
    department: str,
    access_level: str = "employee",
    expires_delta: timedelta | None = None
) -> tuple[str, int]:
    """
    Mints a signed JWT containing standard RFC 7519 claims.
    Returns (token_string, expires_in_seconds).
    """
    delta = expires_delta or timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    expire = now + delta

    payload: dict[str, Any] = {
        "sub": user_id,
        "username": username,
        "role": role,
        "department": department,
        "access_level": access_level,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": "atlas-platform"
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, int(delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodes and cryptographically validates a JWT token.
    Raises AtlasBaseException with HTTP 401 if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            issuer="atlas-platform",
            options={"require": ["sub", "exp", "iat", "role"]}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AtlasBaseException(
            message="Authentication token has expired. Please log in again.",
            error_code="TOKEN_EXPIRED",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    except jwt.PyJWTError as e:
        raise AtlasBaseException(
            message=f"Invalid authentication token: {str(e)}",
            error_code="INVALID_TOKEN",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


# ---------------------------------------------------------------------------
# 3. FastAPI Security Dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
) -> UserPrincipal:
    """
    Dependency that extracts the Bearer token, verifies its signature,
    and returns an authenticated UserPrincipal.
    """
    if credentials is None or not credentials.credentials:
        raise AtlasBaseException(
            message="Missing Authorization Bearer token header.",
            error_code="AUTHENTICATION_REQUIRED",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    claims = decode_access_token(credentials.credentials)

    return UserPrincipal(
        user_id=claims["sub"],
        username=claims["username"],
        role=claims["role"],
        department=claims["department"],
        access_level=claims.get("access_level", "employee"),
        is_active=True
    )


def require_role(allowed_roles: Sequence[EnterpriseRole]):
    """
    Role-Based Access Control (RBAC) dependency factory.
    Enforces that the authenticated user possesses one of the allowed roles.
    """
    async def role_checker(
        current_user: UserPrincipal = Depends(get_current_user)
    ) -> UserPrincipal:
        if current_user.role not in allowed_roles:
            raise AtlasBaseException(
                message=(
                    f"Access denied. User role '{current_user.role}' lacks required permissions. "
                    f"Allowed roles: {list(allowed_roles)}"
                ),
                error_code="INSUFFICIENT_ROLE_PERMISSIONS",
                status_code=status.HTTP_403_FORBIDDEN
            )
        return current_user

    return role_checker


def require_department(allowed_departments: Sequence[str]):
    """
    Department-level boundary dependency factory.
    Enforces tenant/department data isolation.
    """
    async def dept_checker(
        current_user: UserPrincipal = Depends(get_current_user)
    ) -> UserPrincipal:
        # Admins bypass departmental isolation
        if current_user.role == "admin":
            return current_user

        if current_user.department not in allowed_departments:
            raise AtlasBaseException(
                message=(
                    f"Access denied. Department '{current_user.department}' is not authorized "
                    f"for this resource."
                ),
                error_code="DEPARTMENT_ACCESS_RESTRICTED",
                status_code=status.HTTP_403_FORBIDDEN
            )
        return current_user

    return dept_checker
