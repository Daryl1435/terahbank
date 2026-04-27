"""Auth unit tests — OTP, password validation, session rules, lockout, device fingerprint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from core.security import generate_otp, hash_password, verify_password


class TestOTP:
    def test_otp_is_6_digits(self):
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_otp_is_random(self):
        otps = {generate_otp() for _ in range(100)}
        assert len(otps) > 1


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("ValidPass1!")
        assert hashed != "ValidPass1!"

    def test_verify_correct_password(self):
        hashed = hash_password("ValidPass1!")
        assert verify_password("ValidPass1!", hashed) is True

    def test_reject_wrong_password(self):
        hashed = hash_password("ValidPass1!")
        assert verify_password("WrongPass1!", hashed) is False


class TestPasswordComplexity:
    def test_min_10_chars(self):
        from modules.auth.schemas import RegisterRequest
        with pytest.raises(Exception):
            RegisterRequest(full_name="A", phone_number="+237600000001",
                            email="a@b.com", password="Short1!")

    def test_requires_uppercase(self):
        from modules.auth.schemas import RegisterRequest
        with pytest.raises(Exception):
            RegisterRequest(full_name="A", phone_number="+237600000001",
                            email="a@b.com", password="alllower123!")

    def test_requires_number(self):
        from modules.auth.schemas import RegisterRequest
        with pytest.raises(Exception):
            RegisterRequest(full_name="A", phone_number="+237600000001",
                            email="a@b.com", password="NoNumbers!!")

    def test_valid_password_accepted(self):
        from modules.auth.schemas import RegisterRequest
        r = RegisterRequest(full_name="Amina Njoya", phone_number="+237600000001",
                            email="amina@test.com", password="ValidPass1!")
        assert r.password == "ValidPass1!"


# ── Service-level unit tests (mocked DB + Redis) ───────────────────────────────

def _make_service(mock_db=None, mock_redis=None, mock_repo=None):
    """Build an AuthService with all external deps mocked."""
    from modules.auth.service import AuthService

    db = mock_db or AsyncMock()
    svc = AuthService(db)

    if mock_repo is not None:
        svc._repo = mock_repo

    if mock_redis is not None:
        # Patch the property so _redis returns our mock
        with patch.object(type(svc), "_redis", new_callable=lambda: property(lambda self: mock_redis)):
            pass
        svc.__dict__["_redis_mock"] = mock_redis

    return svc, db


def _make_user(
    user_id="00000000-0000-0000-0000-000000000001",
    password="ValidPass1!",
    account_status="active",
    kyc_status="pending",
):
    """Return a minimal mock User object."""
    user = MagicMock()
    user.id = user_id
    user.password_hash = hash_password(password)
    user.account_status = account_status
    user.kyc_status = kyc_status
    return user


@pytest.mark.asyncio
class TestLoginLockout:
    """FR: 5 consecutive wrong-password attempts lock the account for 30 minutes."""

    async def _run_login(self, svc, redis_mock, user, password):
        from modules.auth.schemas import LoginRequest
        from modules.auth.service import _MAX_LOGIN_ATTEMPTS

        with patch("modules.auth.service.get_redis_client", return_value=redis_mock), \
             patch("modules.auth.service.write_audit_log", new_callable=AsyncMock):
            payload = LoginRequest(identifier="user@example.com", password=password)
            svc._repo.get_by_email = AsyncMock(return_value=user)
            svc._repo.get_by_phone = AsyncMock(return_value=None)
            return await svc.login(payload)

    async def test_lockout_after_5_failures(self):
        from modules.auth.service import AuthService
        from modules.auth.schemas import LoginRequest

        redis_mock = AsyncMock()
        redis_mock.exists = AsyncMock(return_value=False)   # no existing lock
        redis_mock.incr = AsyncMock(side_effect=[1, 2, 3, 4, 5])
        redis_mock.expire = AsyncMock()
        redis_mock.setex = AsyncMock()
        redis_mock.delete = AsyncMock()

        user = _make_user()
        db = AsyncMock()
        svc = AuthService(db)
        svc._repo = AsyncMock()
        svc._repo.get_by_email = AsyncMock(return_value=user)

        with patch("modules.auth.service.get_redis_client", return_value=redis_mock), \
             patch("modules.auth.service.write_audit_log", new_callable=AsyncMock):
            for attempt in range(1, 5):
                payload = LoginRequest(identifier="user@example.com", password="WrongPass1!")
                with pytest.raises(HTTPException) as exc:
                    await svc.login(payload)
                assert exc.value.status_code == 401
                assert exc.value.detail["code"] == "INVALID_CREDENTIALS"

            # 5th attempt triggers lockout
            payload = LoginRequest(identifier="user@example.com", password="WrongPass1!")
            with pytest.raises(HTTPException) as exc:
                await svc.login(payload)
            assert exc.value.status_code == 429
            assert exc.value.detail["code"] == "ACCOUNT_LOCKED"
            # Verify lockout key was set
            redis_mock.setex.assert_called()

    async def test_locked_account_rejects_immediately(self):
        from modules.auth.service import AuthService
        from modules.auth.schemas import LoginRequest

        redis_mock = AsyncMock()
        redis_mock.exists = AsyncMock(return_value=True)  # lock already set

        user = _make_user()
        db = AsyncMock()
        svc = AuthService(db)
        svc._repo = AsyncMock()
        svc._repo.get_by_email = AsyncMock(return_value=user)

        with patch("modules.auth.service.get_redis_client", return_value=redis_mock), \
             patch("modules.auth.service.write_audit_log", new_callable=AsyncMock):
            payload = LoginRequest(identifier="user@example.com", password="ValidPass1!")
            with pytest.raises(HTTPException) as exc:
                await svc.login(payload)
            assert exc.value.status_code == 429
            assert exc.value.detail["code"] == "ACCOUNT_LOCKED"


@pytest.mark.asyncio
class TestOTPExpiry:
    """OTP must expire after 5 minutes — service raises OTP_EXPIRED if Redis key missing."""

    async def test_expired_otp_raises(self):
        from modules.auth.service import AuthService
        from modules.auth.schemas import VerifyOTPRequest

        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)  # key gone — TTL elapsed

        db = AsyncMock()
        svc = AuthService(db)

        with patch("modules.auth.service.get_redis_client", return_value=redis_mock):
            payload = VerifyOTPRequest(
                user_id="00000000-0000-0000-0000-000000000001",
                otp="123456",
                purpose="verify",
            )
            with pytest.raises(HTTPException) as exc:
                await svc.verify_otp(payload)
            assert exc.value.detail["code"] == "OTP_EXPIRED"

    async def test_wrong_otp_raises(self):
        from modules.auth.service import AuthService
        from modules.auth.schemas import VerifyOTPRequest

        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value="654321")  # different OTP stored

        db = AsyncMock()
        svc = AuthService(db)

        with patch("modules.auth.service.get_redis_client", return_value=redis_mock):
            payload = VerifyOTPRequest(
                user_id="00000000-0000-0000-0000-000000000001",
                otp="123456",
                purpose="verify",
            )
            with pytest.raises(HTTPException) as exc:
                await svc.verify_otp(payload)
            assert exc.value.detail["code"] == "OTP_INVALID"

    async def test_correct_otp_deleted_on_use(self):
        from modules.auth.service import AuthService
        from modules.auth.schemas import VerifyOTPRequest

        otp_value = "123456"
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=otp_value)
        redis_mock.delete = AsyncMock()

        user = _make_user()
        db = AsyncMock()
        svc = AuthService(db)
        svc._repo = AsyncMock()
        svc._repo.get_by_id = AsyncMock(return_value=user)

        with patch("modules.auth.service.get_redis_client", return_value=redis_mock), \
             patch("modules.auth.service.write_audit_log", new_callable=AsyncMock):
            payload = VerifyOTPRequest(
                user_id="00000000-0000-0000-0000-000000000001",
                otp=otp_value,
                purpose="verify",
            )
            await svc.verify_otp(payload)

        # OTP key must be deleted (single-use)
        redis_mock.delete.assert_any_call(f"otp:00000000-0000-0000-0000-000000000001:verify")


@pytest.mark.asyncio
class TestDeviceRecognition:
    """FR-007: New device flag is set on first login from an unknown fingerprint."""

    async def test_known_device_is_not_flagged(self):
        from modules.auth.service import AuthService
        from modules.auth.schemas import VerifyOTPRequest

        otp_value = "123456"
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=otp_value)
        redis_mock.delete = AsyncMock()
        redis_mock.exists = AsyncMock(return_value=True)  # device already registered
        redis_mock.setex = AsyncMock()

        user = _make_user()
        db = AsyncMock()
        svc = AuthService(db)
        svc._repo = AsyncMock()
        svc._repo.get_by_id = AsyncMock(return_value=user)

        with patch("modules.auth.service.get_redis_client", return_value=redis_mock), \
             patch("modules.auth.service.write_audit_log", new_callable=AsyncMock), \
             patch("modules.auth.service.create_access_token", return_value="acc"), \
             patch("modules.auth.service.create_refresh_token", return_value="ref"):
            payload = VerifyOTPRequest(
                user_id="00000000-0000-0000-0000-000000000001",
                otp=otp_value,
                purpose="login",
                device_fingerprint="fp_abc123",
            )
            response = await svc.verify_otp(payload)

        assert response.data["is_new_device"] is False

    async def test_new_device_is_flagged(self):
        from modules.auth.service import AuthService
        from modules.auth.schemas import VerifyOTPRequest

        otp_value = "123456"
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=otp_value)
        redis_mock.delete = AsyncMock()
        redis_mock.exists = AsyncMock(return_value=False)  # device NOT registered
        redis_mock.set = AsyncMock()
        redis_mock.setex = AsyncMock()

        user = _make_user()
        db = AsyncMock()
        svc = AuthService(db)
        svc._repo = AsyncMock()
        svc._repo.get_by_id = AsyncMock(return_value=user)

        with patch("modules.auth.service.get_redis_client", return_value=redis_mock), \
             patch("modules.auth.service.write_audit_log", new_callable=AsyncMock), \
             patch("modules.auth.service.create_access_token", return_value="acc"), \
             patch("modules.auth.service.create_refresh_token", return_value="ref"):
            payload = VerifyOTPRequest(
                user_id="00000000-0000-0000-0000-000000000001",
                otp=otp_value,
                purpose="login",
                device_fingerprint="fp_new_device",
            )
            response = await svc.verify_otp(payload)

        assert response.data["is_new_device"] is True
        # Device key stored permanently
        redis_mock.set.assert_called_once()


@pytest.mark.asyncio
class TestOTPResendLimit:
    """OTP_MAX_RESEND_ATTEMPTS=3: 4th resend request raises OTP_RESEND_LIMIT."""

    async def test_resend_limit_enforced(self):
        from modules.auth.service import AuthService
        from modules.auth.schemas import ResendOTPRequest

        redis_mock = AsyncMock()
        # 4th call exceeds limit
        redis_mock.incr = AsyncMock(return_value=4)
        redis_mock.expire = AsyncMock()

        user = _make_user()
        db = AsyncMock()
        svc = AuthService(db)
        svc._repo = AsyncMock()
        svc._repo.get_by_id = AsyncMock(return_value=user)

        with patch("modules.auth.service.get_redis_client", return_value=redis_mock):
            payload = ResendOTPRequest(user_id="00000000-0000-0000-0000-000000000001", purpose="verify")
            with pytest.raises(HTTPException) as exc:
                await svc.resend_otp(payload)
            assert exc.value.status_code == 429
            assert exc.value.detail["code"] == "OTP_RESEND_LIMIT"
