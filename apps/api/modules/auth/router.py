from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_user
from core.schemas import TerahResponse

from .schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResendOTPRequest,
    SetupPINRequest,
    VerifyOTPRequest,
    VerifyPINRequest,
)
from .service import AuthService

router = APIRouter()


# ── Public endpoints (no JWT required) ───────────────────────────────────────

@router.post("/register", response_model=TerahResponse)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TerahResponse:
    return await AuthService(db).register(payload)


@router.post("/login", response_model=TerahResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TerahResponse:
    return await AuthService(db).login(payload)


@router.post("/verify-otp", response_model=TerahResponse)
async def verify_otp(
    payload: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
) -> TerahResponse:
    return await AuthService(db).verify_otp(payload)


@router.post("/resend-otp", response_model=TerahResponse)
async def resend_otp(
    payload: ResendOTPRequest,
    db: AsyncSession = Depends(get_db),
) -> TerahResponse:
    return await AuthService(db).resend_otp(payload)


@router.post("/refresh", response_model=TerahResponse)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TerahResponse:
    return await AuthService(db).refresh_token(payload)


# ── Authenticated endpoints ───────────────────────────────────────────────────

@router.post("/logout", response_model=TerahResponse)
async def logout(
    payload: RefreshRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TerahResponse:
    return await AuthService(db).logout(user, payload.refresh_token)


@router.post("/change-password", response_model=TerahResponse)
async def change_password(
    payload: ChangePasswordRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TerahResponse:
    return await AuthService(db).change_password(payload, user)


@router.post("/setup-pin", response_model=TerahResponse)
async def setup_pin(
    payload: SetupPINRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TerahResponse:
    """FR-006: Set or reset the mobile PIN (4–6 digits, hashed with bcrypt)."""
    return await AuthService(db).setup_pin(user, payload)


@router.post("/verify-pin", response_model=TerahResponse)
async def verify_pin(
    payload: VerifyPINRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TerahResponse:
    """FR-036: Verify PIN and receive a single-use pin_token (valid 60 s) for transfer confirmation."""
    return await AuthService(db).verify_pin(user, payload)


@router.get("/me", response_model=TerahResponse)
async def get_me(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TerahResponse:
    """Return the authenticated user's profile (name, phone, email)."""
    return await AuthService(db).get_me(user)
