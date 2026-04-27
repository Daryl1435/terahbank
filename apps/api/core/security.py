import secrets
from datetime import datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.BCRYPT_ROUNDS
)

# ─── Password helpers ─────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """bcrypt cost=12. Never SHA or MD5."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ─── OTP ──────────────────────────────────────────────────────────────────────


def generate_otp() -> str:
    """6-digit OTP via cryptographically secure PRNG (secrets.randbelow)."""
    return str(secrets.randbelow(1_000_000)).zfill(6)


# ─── Idempotency ──────────────────────────────────────────────────────────────


def generate_idempotency_key() -> str:
    return secrets.token_urlsafe(32)


# ─── JWT (RS256) ──────────────────────────────────────────────────────────────

_private_key: str | None = None
_public_key: str | None = None


def _ensure_keys_loaded() -> None:
    """Lazy-load RSA key files on first use."""
    global _private_key, _public_key
    if _private_key is None:
        with open(settings.JWT_PRIVATE_KEY_PATH) as f:
            _private_key = f.read()
    if _public_key is None:
        with open(settings.JWT_PUBLIC_KEY_PATH) as f:
            _public_key = f.read()


def create_access_token(user_id: str | UUID, jti: str) -> str:
    """
    Issue a 15-minute RS256 JWT access token.
    FR-008: short expiry enforces session inactivity termination.
    """
    _ensure_keys_loaded()
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _private_key, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str | UUID, jti: str) -> str:
    """
    Issue a 7-day RS256 JWT refresh token.
    The JTI is stored in Redis so the token can be revoked on logout/password change.
    """
    _ensure_keys_loaded()
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, _private_key, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate an RS256 JWT.
    Raises jose.JWTError on any failure (expired, invalid signature, malformed).
    """
    _ensure_keys_loaded()
    return jwt.decode(token, _public_key, algorithms=[settings.JWT_ALGORITHM])
