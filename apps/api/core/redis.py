import redis.asyncio as aioredis
from .config import settings

# Module-level client — initialised in lifespan startup, closed in shutdown.
# Use get_redis() as a FastAPI dependency for request-scoped access.
_redis_client: aioredis.Redis | None = None


async def init_redis() -> None:
    """Called once at application startup."""
    global _redis_client
    _redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=20,
    )
    # Verify connectivity immediately so startup fails fast if Redis is down.
    await _redis_client.ping()


async def close_redis() -> None:
    """Called once at application shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


def get_redis_client() -> aioredis.Redis:
    """Return the shared Redis client. Raises if init_redis() was not called."""
    if _redis_client is None:
        raise RuntimeError("Redis client is not initialised. Call init_redis() first.")
    return _redis_client


# FastAPI dependency — use with Depends(get_redis)
async def get_redis() -> aioredis.Redis:
    return get_redis_client()


# ─── Redis key helpers ────────────────────────────────────────────────────────
# Centralising key patterns prevents typos and makes TTL audits trivial.

def otp_key(user_id: str, otp_type: str = "verify") -> str:
    """otp:{user_id}:{type}  — 5-min TTL (OTP_EXPIRE_MINUTES)"""
    return f"otp:{user_id}:{otp_type}"


def refresh_token_key(user_id: str, jti: str) -> str:
    """refresh:{user_id}:{jti}  — 7-day TTL (JWT_REFRESH_TOKEN_EXPIRE_DAYS)"""
    return f"refresh:{user_id}:{jti}"


def balance_cache_key(account_id: str) -> str:
    """balance:{account_id}  — 30-sec TTL"""
    return f"balance:{account_id}"


def session_lock_key(user_id: str) -> str:
    """lock:otp:{user_id}  — OTP_SESSION_LOCK_MINUTES TTL after 5 failed attempts"""
    return f"lock:otp:{user_id}"


def idempotency_key(key: str) -> str:
    """idempotency:{key}  — 24-hour TTL"""
    return f"idempotency:{key}"


def presigned_url_key(document_id: str) -> str:
    """presigned:{document_id}  — 5-min TTL (same as URL expiry)"""
    return f"presigned:{document_id}"


def insurance_catalog_key() -> str:
    """insurance:catalog  — 6-hour TTL"""
    return "insurance:catalog"


def config_cache_key() -> str:
    """config:system  — invalidated on every admin config PATCH"""
    return "config:system"


def pin_token_key(token: str) -> str:
    """pin_token:{token}  — 60-sec TTL, single-use (deleted on first transfer use)"""
    return f"pin_token:{token}"


def mtn_momo_token_key() -> str:
    """mtn_momo:access_token  — 55-min TTL (5-min buffer before MTN's 1-hour expiry)"""
    return "mtn_momo:access_token"


def mtn_momo_disbursement_token_key() -> str:
    """mtn_momo:disbursement_token  — 55-min TTL (5-min buffer before MTN's 1-hour expiry)"""
    return "mtn_momo:disbursement_token"


def orange_money_token_key() -> str:
    """orange_money:access_token  — TTL set dynamically from expires_in - 60s"""
    return "orange_money:access_token"
