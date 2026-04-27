from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .security import decode_token

_bearer = HTTPBearer(auto_error=False)

_ADMIN_ROLES = {"super_admin", "operations_staff", "read_only_analyst"}

# ─── get_current_user ─────────────────────────────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    Validates the Bearer JWT and returns the authenticated User row.
    Raises 401 if the token is missing, expired, or invalid.
    Raises 403 if the account is suspended or closed.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token is invalid or expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "WRONG_TOKEN_TYPE", "message": "Access token required."},
        )

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token subject missing."},
        )

    # Lazy import to avoid circular deps
    from modules.auth.repository import AuthRepository

    user = await AuthRepository(db).get_by_id(UUID(user_id_str))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User no longer exists."},
        )

    if user.account_status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_SUSPENDED", "message": "Your account has been suspended."},
        )
    if user.account_status == "closed":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_CLOSED", "message": "This account is closed."},
        )

    return user


# ─── KYC gate ─────────────────────────────────────────────────────────────────


async def require_kyc_approved(user=Depends(get_current_user)):
    """Returns 403 with KYC_REQUIRED if user.kyc_status != 'approved'."""
    if user.kyc_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "KYC_REQUIRED",
                "message": "Please complete identity verification to use this feature.",
            },
        )
    return user


# ─── Admin role guards ────────────────────────────────────────────────────────


async def _get_admin_from_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    Validates an admin Bearer JWT (type=admin_access) and returns the AdminUser row.
    Raises 401 if missing/invalid, 403 if inactive.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token is invalid or expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "admin_access":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin access token required."},
        )

    admin_id_str: str | None = payload.get("sub")
    if not admin_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token subject missing."},
        )

    from modules.admin.repository import AdminRepository

    admin = await AdminRepository(db).get_admin_by_id(UUID(admin_id_str))
    if admin is None or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin account not found or inactive."},
        )

    return admin


async def require_admin_role(admin=Depends(_get_admin_from_token)):
    """Returns 403 if user is not any valid admin role (operations_staff, super_admin, read_only_analyst)."""
    if admin.role not in _ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin access required."},
        )
    return admin


async def require_super_admin(admin=Depends(_get_admin_from_token)):
    """Returns 403 if user is not super_admin."""
    if admin.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Super admin access required."},
        )
    return admin
