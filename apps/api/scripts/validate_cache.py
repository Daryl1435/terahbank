"""
TerahBank Redis Cache Validator — Milestone 7.4.

Connects to Redis and audits all caching mechanisms:
  - Balance cache     (30s TTL,       key: balance:{account_id})
  - OTP codes         (5 min TTL,     key: otp:{user_id}:{type})
  - Config cache      (60 min TTL,    key: config:{key_name})
  - System config     (60 min TTL,    key: config:system)
  - Idempotency keys  (24 hour TTL,   key: idempotency:{key})
  - MTN MoMo token    (55 min TTL,    key: mtn_momo:access_token)
  - Insurance catalog (6 hour TTL,    key: insurance:catalog)
  - PIN tokens        (60s TTL,       key: pin_token:{token})
  - Refresh tokens    (7 day TTL,     key: refresh:{user_id}:{jti})

Usage:
  cd apps/api
  venv/Scripts/activate
  python -m scripts.validate_cache

Prints a table of every cache key found, its current TTL, and whether
that TTL is within the expected range.

Exit codes:
  0 — all keys within expected TTL bounds (or no keys present)
  1 — one or more keys have an out-of-range TTL
"""

import asyncio
import sys

import redis.asyncio as aioredis  # type: ignore[import]

from core.config import settings


# ─── Expected TTL ranges (min, max) in seconds ────────────────────────────────
# min is 0 (key may be about to expire); max is the TTL at creation time + 5s buffer.

TTL_SPEC: dict[str, tuple[int, int]] = {
    "balance:":            (0,     35),         # 30s balance cache
    "otp:":                (0,     310),         # 5 min OTP
    "config:":             (0,     3610),        # 60 min config cache
    "idempotency:":        (0,     86_410),      # 24h idempotency
    "mtn_momo:":           (0,     3_310),       # 55 min token
    "orange_money:":       (0,     3_610),       # up to 60 min
    "insurance:catalog":   (0,     21_610),      # 6 h catalog
    "pin_token:":          (0,     65),          # 60s pin token
    "refresh:":            (0,     604_810),     # 7 days refresh token
    "lock:otp:":           (0,     1_810),       # 30 min lockout
    "presigned:":          (0,     305),         # 5 min S3 URL
}


def _classify(key: str) -> tuple[str, tuple[int, int]] | tuple[None, None]:
    """Return the pattern label and expected TTL range for a given Redis key."""
    for pattern, ttl_range in TTL_SPEC.items():
        if key.startswith(pattern):
            return pattern, ttl_range
    return None, None


async def main() -> int:
    """Run the cache audit. Returns 0 on success, 1 on failure."""
    redis = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=5,
    )

    try:
        await redis.ping()
    except Exception as exc:
        print(f"ERROR: Cannot connect to Redis at {settings.REDIS_URL}: {exc}")
        return 1

    # Scan all keys (SCAN is non-blocking; safe on production)
    all_keys: list[str] = []
    cursor = 0
    while True:
        cursor, batch = await redis.scan(cursor, count=200)
        all_keys.extend(batch)
        if cursor == 0:
            break

    if not all_keys:
        print("Redis is reachable but contains no keys (fresh instance or everything expired).")
        return 0

    # Check TTL for every key we know about
    failures: list[str] = []
    unknown:  list[str] = []
    rows:     list[tuple] = []

    for key in sorted(all_keys):
        pattern, expected_range = _classify(key)
        ttl = await redis.ttl(key)

        if pattern is None:
            unknown.append(key)
            continue

        lo, hi = expected_range
        in_range = lo <= ttl <= hi

        rows.append((
            "PASS" if in_range else "FAIL",
            key[:48],
            f"{ttl}s" if ttl >= 0 else "no expiry",
            f"{lo}–{hi}s",
        ))

        if not in_range:
            failures.append(key)

    # ── Print report ──────────────────────────────────────────────────────────

    col_w = (6, 50, 12, 16)
    header = ("Status", "Key", "Current TTL", "Expected range")
    sep    = "  ".join("-" * w for w in col_w)

    print()
    print("=" * 90)
    print("  TerahBank Redis Cache Audit — Milestone 7.4")
    print("=" * 90)
    print("  " + "  ".join(h.ljust(col_w[i]) for i, h in enumerate(header)))
    print("  " + sep)

    for row in rows:
        print("  " + "  ".join(str(v).ljust(col_w[i]) for i, v in enumerate(row)))

    if unknown:
        print()
        print(f"  {len(unknown)} unclassified key(s) (not part of TerahBank cache spec):")
        for k in unknown:
            print(f"    • {k}")

    print("-" * 90)

    if failures:
        print(f"  FAIL — {len(failures)} key(s) have out-of-range TTL:")
        for k in failures:
            print(f"    • {k}")
        result = 1
    else:
        total = len(rows)
        print(f"  PASS — {total} key(s) audited, all TTLs within expected range")
        result = 0

    print("=" * 90)
    print()
    await redis.aclose()
    return result


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
