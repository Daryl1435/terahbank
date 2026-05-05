import re
from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator


# ─── Shared password complexity validator ─────────────────────────────────────

def _validate_password_complexity(v: str) -> str:
    """FR-003: min 10 chars, 1 uppercase, 1 digit, 1 special char."""
    if len(v) < 10:
        raise ValueError("Password must be at least 10 characters")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Must contain at least one uppercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?:{}|<>]", v):
        raise ValueError("Must contain at least one special character")
    return v


# ─── Request schemas ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """FR-001: User registration."""
    full_name: str
    phone_number: str
    email: EmailStr
    password: str
    city: str | None = None
    address: str | None = None
    preferred_language: Literal["fr", "en"] = "fr"

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)

    @field_validator("phone_number")
    @classmethod
    def phone_e164(cls, v: str) -> str:
        if not re.match(r"^\+\d{7,15}$", v):
            raise ValueError("Phone must be E.164 format e.g. +237600000000")
        return v


class LoginRequest(BaseModel):
    """FR-004: Login via phone number or email + password."""
    identifier: str   # phone number or email address
    password: str


class VerifyOTPRequest(BaseModel):
    """FR-002 / FR-005: Verify OTP for registration or 2FA login."""
    user_id: str
    otp: str
    purpose: Literal["verify", "login"] = "verify"
    # FR-007: Device fingerprint sent by mobile client
    device_fingerprint: str | None = None


class ResendOTPRequest(BaseModel):
    """Resend OTP — max 3 attempts per OTP window (OTP_MAX_RESEND_ATTEMPTS)."""
    user_id: str
    purpose: Literal["verify", "login"] = "verify"


class RefreshRequest(BaseModel):
    """Rotate access token using a valid refresh token."""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Authenticated password change — requires current password."""
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


# ─── Response data payloads ───────────────────────────────────────────────────

class RegisterResponseData(BaseModel):
    user_id: str
    otp_required: bool = True


class LoginInitResponseData(BaseModel):
    """Returned from POST /auth/login — user must now complete 2FA."""
    user_id: str
    otp_required: bool = True


class AuthTokenResponseData(BaseModel):
    """Returned after successful OTP verification for login."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int   # access token lifetime in seconds
    user_id: str
    full_name: str
    kyc_status: str
    is_new_device: bool = False


class RefreshResponseData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ─── PIN schemas (FR-006/036) ─────────────────────────────────────────────────

class SetupPINRequest(BaseModel):
    """Set or reset the user's mobile PIN. Requires authenticated session."""
    pin: str

    @field_validator("pin")
    @classmethod
    def pin_digits(cls, v: str) -> str:
        if not v.isdigit() or not (4 <= len(v) <= 6):
            raise ValueError("PIN must be 4–6 digits")
        return v


class VerifyPINRequest(BaseModel):
    """Verify PIN and receive a one-time pin_token valid for 60 s."""
    pin: str


class PINTokenResponseData(BaseModel):
    """Returned after successful PIN verification."""
    pin_token: str   # UUID — pass as pin_token in TransferRequest
    expires_in: int = 60  # seconds
