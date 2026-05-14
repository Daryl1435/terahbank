# Business logic for auth module.
# Calls AuthRepository for DB access.
# Writes to audit_logs before returning on every auth event.
# OTPs: secrets.randbelow(1000000), stored in Redis otp:{user_id}:{type}, 5-min TTL, deleted on first use.
# Passwords: bcrypt rounds=12. Never SHA or MD5.

import secrets
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit_log
from core.config import settings
from core.redis import (
    get_redis_client,
    otp_key,
    refresh_token_key,
    session_lock_key,
)
from core.schemas import TerahResponse
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp,
    hash_password,
    verify_password,
)

from .repository import AuthRepository
from .schemas import (
    AuthTokenResponseData,
    ChangePasswordRequest,
    LoginInitResponseData,
    LoginRequest,
    RefreshRequest,
    RefreshResponseData,
    RegisterRequest,
    RegisterResponseData,
    ResendOTPRequest,
    VerifyOTPRequest,
)

_MAX_LOGIN_ATTEMPTS = 5


def _login_fail_key(user_id: str) -> str:
    return f"login_fail:{user_id}"


def _otp_resend_counter_key(user_id: str, purpose: str) -> str:
    return f"otp_resend:{user_id}:{purpose}"


def _device_key(user_id: str, fp_hash: str) -> str:
    return f"device:{user_id}:{fp_hash}"


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._repo = AuthRepository(db)

    @property
    def _redis(self):
        return get_redis_client()

    # ── Register (FR-001) ─────────────────────────────────────────────────────

    async def register(self, payload: RegisterRequest) -> TerahResponse:
        if await self._repo.get_by_email(payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "EMAIL_TAKEN", "message": "An account with this email already exists."},
            )
        if await self._repo.get_by_phone(payload.phone_number):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "PHONE_TAKEN", "message": "An account with this phone number already exists."},
            )

        user = await self._repo.create(
            full_name=payload.full_name,
            phone_number=payload.phone_number,
            email=payload.email,
            password_hash=hash_password(payload.password),
            city=payload.city,
            address=payload.address,
            preferred_language=payload.preferred_language,
        )

        otp = generate_otp()
        await self._redis.setex(
            otp_key(str(user.id), "verify"),
            settings.OTP_EXPIRE_MINUTES * 60,
            otp,
        )

        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="ACCOUNT_OPENED",
            entity_type="user",
            entity_id=user.id,
        )

        from modules.notifications.service import dispatch_otp_sms
        await dispatch_otp_sms(user.phone_number, otp)

        return TerahResponse(
            success=True,
            data=RegisterResponseData(user_id=str(user.id)).model_dump(),
            message="Registration successful. Please verify your phone number.",
        )

    # ── Verify OTP (FR-002 / FR-005) ─────────────────────────────────────────

    async def verify_otp(self, payload: VerifyOTPRequest) -> TerahResponse:
        redis_key = otp_key(payload.user_id, payload.purpose)
        stored_otp = await self._redis.get(redis_key)

        if stored_otp is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "OTP_EXPIRED", "message": "OTP has expired or was already used."},
            )
        if stored_otp != payload.otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "OTP_INVALID", "message": "Invalid OTP."},
            )

        # Single-use: delete immediately on match
        await self._redis.delete(redis_key)
        await self._redis.delete(_otp_resend_counter_key(payload.user_id, payload.purpose))

        user = await self._repo.get_by_id(UUID(payload.user_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found."},
            )

        if payload.purpose == "verify":
            # FR-002: mark phone verified; account stays pending KYC
            await write_audit_log(
                self.db,
                actor_id=user.id,
                action="OTP_VERIFIED",
                entity_type="user",
                entity_id=user.id,
            )
            return TerahResponse(
                success=True,
                data={"verified": True},
                message="Phone number verified successfully.",
            )

        # purpose == "login" (FR-005): issue access + refresh tokens
        jti_access = secrets.token_urlsafe(32)
        jti_refresh = secrets.token_urlsafe(32)

        access_token = create_access_token(user.id, jti_access)
        refresh_token_str = create_refresh_token(user.id, jti_refresh)

        await self._redis.setex(
            refresh_token_key(str(user.id), jti_refresh),
            settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            "1",
        )

        # FR-007: device fingerprint — detect new devices
        is_new_device = False
        if payload.device_fingerprint:
            fp_hash = payload.device_fingerprint  # client sends hashed fingerprint
            dkey = _device_key(str(user.id), fp_hash)
            if not await self._redis.exists(dkey):
                is_new_device = True
                await self._redis.set(dkey, "1")  # no TTL — device registrations are permanent
                await write_audit_log(
                    self.db,
                    actor_id=user.id,
                    action="DEVICE_REGISTERED",
                    entity_type="user",
                    entity_id=user.id,
                    metadata={"fingerprint_hash": fp_hash},
                )

        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="LOGIN_SUCCESS",
            entity_type="user",
            entity_id=user.id,
        )

        return TerahResponse(
            success=True,
            data=AuthTokenResponseData(
                access_token=access_token,
                refresh_token=refresh_token_str,
                expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user_id=str(user.id),
                full_name=user.full_name,
                kyc_status=user.kyc_status,
                is_new_device=is_new_device,
            ).model_dump(),
        )

    # ── Login (FR-004) ────────────────────────────────────────────────────────

    async def login(self, payload: LoginRequest) -> TerahResponse:
        # Lookup by email or phone
        if "@" in payload.identifier:
            user = await self._repo.get_by_email(payload.identifier)
        else:
            user = await self._repo.get_by_phone(payload.identifier)

        # Check lockout before password work (prevents timing oracle)
        if user and await self._redis.exists(session_lock_key(str(user.id))):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "ACCOUNT_LOCKED", "message": "Too many failed attempts. Try again in 30 minutes."},
            )

        # Constant-time validation — always run verify_password even if user is None
        # (dummy hash prevents timing enumeration)
        _DUMMY_HASH = "$2b$12$KIXvLmnbhLqvtv1sBVFJCOjW8z8p3ZDEiJkT6dSfzxXQ7DpWU0LKa"
        password_valid = verify_password(
            payload.password,
            user.password_hash if user else _DUMMY_HASH,
        ) and user is not None

        if not password_valid:
            if user:
                fail_key = _login_fail_key(str(user.id))
                fail_count = await self._redis.incr(fail_key)
                if fail_count == 1:
                    await self._redis.expire(fail_key, settings.OTP_SESSION_LOCK_MINUTES * 60)

                if fail_count >= _MAX_LOGIN_ATTEMPTS:
                    await self._redis.setex(
                        session_lock_key(str(user.id)),
                        settings.OTP_SESSION_LOCK_MINUTES * 60,
                        "1",
                    )
                    await self._redis.delete(fail_key)
                    await write_audit_log(
                        self.db,
                        actor_id=user.id,
                        action="LOGIN_FAILED",
                        entity_type="user",
                        entity_id=user.id,
                        metadata={"reason": "ACCOUNT_LOCKED"},
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={"code": "ACCOUNT_LOCKED", "message": "Too many failed attempts. Try again in 30 minutes."},
                    )

                await write_audit_log(
                    self.db,
                    actor_id=user.id,
                    action="LOGIN_FAILED",
                    entity_type="user",
                    entity_id=user.id,
                    metadata={"reason": "WRONG_PASSWORD", "attempt": fail_count},
                )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "Invalid credentials."},
            )

        # Clear failure counter on success
        await self._redis.delete(_login_fail_key(str(user.id)))

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

        # FR-005: 2FA — generate login OTP, do NOT issue tokens yet
        otp = generate_otp()
        await self._redis.setex(
            otp_key(str(user.id), "login"),
            settings.OTP_EXPIRE_MINUTES * 60,
            otp,
        )

        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="OTP_REQUESTED",
            entity_type="user",
            entity_id=user.id,
            metadata={"purpose": "login"},
        )

        from modules.notifications.service import dispatch_otp_sms
        await dispatch_otp_sms(user.phone_number, otp)

        return TerahResponse(
            success=True,
            data=LoginInitResponseData(user_id=str(user.id)).model_dump(),
            message="OTP sent to your registered phone number.",
        )

    # ── Refresh Token (FR-008) ────────────────────────────────────────────────

    async def refresh_token(self, payload: RefreshRequest) -> TerahResponse:
        try:
            token_data = decode_token(payload.refresh_token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Refresh token is invalid or expired."},
            )

        if token_data.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "WRONG_TOKEN_TYPE", "message": "Refresh token required."},
            )

        user_id: str | None = token_data.get("sub")
        jti: str | None = token_data.get("jti")

        if not user_id or not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Malformed token."},
            )

        if not await self._redis.exists(refresh_token_key(user_id, jti)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "TOKEN_REVOKED", "message": "Refresh token has been revoked."},
            )

        user = await self._repo.get_by_id(UUID(user_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "USER_NOT_FOUND", "message": "User not found."},
            )

        new_jti = secrets.token_urlsafe(32)
        access_token = create_access_token(user.id, new_jti)

        return TerahResponse(
            success=True,
            data=RefreshResponseData(
                access_token=access_token,
                expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            ).model_dump(),
        )

    # ── Logout ────────────────────────────────────────────────────────────────

    async def logout(self, user, refresh_token_str: str) -> TerahResponse:
        try:
            token_data = decode_token(refresh_token_str)
            jti = token_data.get("jti")
            if jti:
                await self._redis.delete(refresh_token_key(str(user.id), jti))
        except JWTError:
            pass  # Expired token — still complete the logout

        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="LOGOUT",
            entity_type="user",
            entity_id=user.id,
        )

        return TerahResponse(success=True, message="Logged out successfully.")

    # ── Resend OTP ────────────────────────────────────────────────────────────

    async def resend_otp(self, payload: ResendOTPRequest) -> TerahResponse:
        user = await self._repo.get_by_id(UUID(payload.user_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found."},
            )

        resend_key = _otp_resend_counter_key(payload.user_id, payload.purpose)
        resend_count = await self._redis.incr(resend_key)
        if resend_count == 1:
            await self._redis.expire(resend_key, settings.OTP_EXPIRE_MINUTES * 60)

        if resend_count > settings.OTP_MAX_RESEND_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "OTP_RESEND_LIMIT", "message": "Maximum resend attempts reached. Please try again later."},
            )

        otp = generate_otp()
        await self._redis.setex(
            otp_key(payload.user_id, payload.purpose),
            settings.OTP_EXPIRE_MINUTES * 60,
            otp,
        )

        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="OTP_REQUESTED",
            entity_type="user",
            entity_id=user.id,
            metadata={"purpose": payload.purpose, "resend_count": resend_count},
        )

        from modules.notifications.service import dispatch_otp_sms
        await dispatch_otp_sms(user.phone_number, otp)

        return TerahResponse(success=True, message="OTP resent successfully.")

    # ── Change Password ───────────────────────────────────────────────────────

    async def change_password(self, payload: ChangePasswordRequest, user) -> TerahResponse:
        if not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "WRONG_PASSWORD", "message": "Current password is incorrect."},
            )

        await self._repo.update_fields(user, password_hash=hash_password(payload.new_password))

        # Revoke all active refresh tokens for this user
        pattern = f"refresh:{user.id}:*"
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self._redis.delete(*keys)
            if cursor == 0:
                break

        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="PASSWORD_CHANGED",
            entity_type="user",
            entity_id=user.id,
        )

        return TerahResponse(success=True, message="Password changed successfully.")

    # ── FR-006/036: Setup PIN ─────────────────────────────────────────────────

    async def setup_pin(self, user, payload) -> TerahResponse:
        """
        FR-006: Store (or reset) the user's 4–6 digit mobile PIN.
        PIN is hashed with bcrypt cost=12 — same as passwords.
        """
        from .schemas import SetupPINRequest
        await self._repo.update_fields(user, pin_hash=hash_password(payload.pin))

        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="PIN_SETUP",
            entity_type="user",
            entity_id=user.id,
        )

        return TerahResponse(success=True, message="PIN set successfully.")

    # ── FR-036: Verify PIN → one-time token ───────────────────────────────────

    async def verify_pin(self, user, payload) -> TerahResponse:
        """
        FR-036: Verify PIN against stored hash. On success, issue a single-use
        pin_token (UUID) stored in Redis for 60 s. The token is consumed by the
        transfer endpoint and cannot be reused.
        """
        import uuid as _uuid
        from core.redis import pin_token_key
        from .schemas import PINTokenResponseData

        _PIN_TOKEN_TTL = 60  # seconds

        if user.pin_hash is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "PIN_NOT_SET", "message": "No PIN configured. Please set a PIN first."},
            )

        if not verify_password(payload.pin, user.pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_PIN", "message": "Incorrect PIN."},
            )

        token = str(_uuid.uuid4())
        await self._redis.setex(pin_token_key(token), _PIN_TOKEN_TTL, str(user.id))

        return TerahResponse(
            success=True,
            data=PINTokenResponseData(pin_token=token).model_dump(),
            message="PIN verified.",
        )
