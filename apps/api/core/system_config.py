"""
System config reader with Redis cache.

Reads from the system_config table (keyed by string key, value is TEXT).
Each key cached individually as config:{key} with a 1-hour TTL.
Cache is invalidated on every admin PATCH /admin/config (Milestone 5.1).

Usage:
    value = await get_config_value(db, "penalty_rate_project", default="0.0500")
    rate = Decimal(value)
"""

import logging
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import get_redis_client

logger = logging.getLogger("terahbank.system_config")

CONFIG_CACHE_TTL: int = 3600  # 1 hour


def _config_key(key: str) -> str:
    return f"config:{key}"


async def get_config_value(
    db: AsyncSession,
    key: str,
    default: str = "",
) -> str:
    """
    Return the TEXT value for system_config.key.
    Redis cache consulted first (1-hour TTL); DB fallback on miss.
    Returns `default` if the key does not exist in either.
    """
    redis = get_redis_client()
    cached = await redis.get(_config_key(key))
    if cached is not None:
        return cached

    from modules.admin.models import SystemConfig  # avoid circular import at module level

    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    value = config.value if config else default

    await redis.setex(_config_key(key), CONFIG_CACHE_TTL, value)
    return value


async def get_config_decimal(
    db: AsyncSession,
    key: str,
    default: Decimal = Decimal("0"),
) -> Decimal:
    """
    Convenience wrapper — returns a Decimal parsed from the config value.
    Falls back to `default` if the key is missing or unparseable.
    """
    raw = await get_config_value(db, key, default=str(default))
    try:
        return Decimal(raw)
    except InvalidOperation:
        logger.error("system_config key=%s has invalid Decimal value=%r; using default=%s", key, raw, default)
        return default


async def invalidate_config_cache(key: str | None = None) -> None:
    """
    Invalidate one config key (or all config:* keys if key is None).
    Called by admin PATCH /admin/config (Milestone 5.1).
    """
    redis = get_redis_client()
    if key is not None:
        await redis.delete(_config_key(key))
    else:
        # Scan and delete all config:* keys
        async for k in redis.scan_iter("config:*"):
            await redis.delete(k)
