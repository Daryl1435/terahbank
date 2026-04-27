"""
Orange Money (CEMAC) Collections & Disbursements API client.

Authentication:
  - OAuth2 client_credentials flow: POST /oauth/token.
  - Token cached in Redis key `orange_money:access_token` with TTL = expires_in - 60s.
  - Auto-refresh on cache miss.

Amounts:
  - All internal DB values are in smallest XAF unit (1 XAF = 100 units).
  - Orange Money API expects the amount in whole XAF: amount_xaf = amount_units // 100.

Phone numbers:
  - Our system stores E.164 with leading '+' (e.g. "+237690000001").
  - Pass as-is to Orange Money (they accept E.164).

Callback validation:
  - HMAC-SHA256 over the raw request body using ORANGE_MONEY_WEBHOOK_SECRET.
  - Orange Money sends the signature in the X-Orange-Signature header.
  - Always return HTTP 200 even on validation failure (prevents retry storms).

CRITICAL: This client is called from BullMQ workers only, NEVER from request handlers.
"""

import hashlib
import hmac
import logging

import httpx

from core.config import settings
from core.redis import get_redis_client, orange_money_token_key

logger = logging.getLogger("terahbank.orange_money")

# Buffer (seconds) subtracted from expires_in to avoid using a stale token
_TOKEN_TTL_BUFFER: int = 60


def _amount_xaf(amount_units: int) -> int:
    """Convert smallest-unit amount to whole XAF for Orange Money API."""
    return amount_units // 100


def validate_orange_callback_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    Validate HMAC-SHA256 signature on an inbound Orange Money callback.

    Orange Money sends the signature in the X-Orange-Signature header as a
    lowercase hex digest of the raw request body.

    Returns True only when the HMAC matches. Uses constant-time comparison to
    prevent timing attacks. Caller must return HTTP 200 even on failure (prevents
    Orange Money from retrying indefinitely), but must NOT process the transaction.
    """
    if not secret or not signature:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected.lower(), signature.lower())


class OrangeMoneyClient:
    """
    Async Orange Money CEMAC API client.
    Handles deposits (collections) and withdrawals (disbursements).
    Instantiate per worker call — does not hold state beyond token caching.
    """

    def __init__(self) -> None:
        self._base_url = settings.ORANGE_MONEY_BASE_URL.rstrip("/")
        self._client_id = settings.ORANGE_MONEY_CLIENT_ID
        self._client_secret = settings.ORANGE_MONEY_CLIENT_SECRET
        self._merchant_id = settings.ORANGE_MONEY_MERCHANT_ID
        self._merchant_key = settings.ORANGE_MONEY_MERCHANT_KEY
        self._callback_url = settings.ORANGE_MONEY_CALLBACK_URL

    async def get_access_token(self) -> str:
        """
        Return a valid Bearer access token.
        Fetched from Redis cache; refreshed on miss via OAuth token endpoint.
        """
        redis = get_redis_client()
        cached = await redis.get(orange_money_token_key())
        if cached:
            return cached

        token, ttl = await self._fetch_new_token()
        await redis.setex(orange_money_token_key(), ttl, token)
        return token

    async def _fetch_new_token(self) -> tuple[str, int]:
        """Exchange client_id + client_secret for a Bearer access token via OAuth."""
        url = f"{self._base_url}/oauth/token"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Orange Money token fetch failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )
        data = resp.json()
        token: str = data["access_token"]
        expires_in: int = int(data.get("expires_in", 3600))
        ttl = max(expires_in - _TOKEN_TTL_BUFFER, 60)
        return token, ttl

    async def pay(
        self,
        amount_units: int,
        phone_e164: str,
        our_reference: str,  # Our TXN-YYYYMMDD-XXXX reference (used as order.id)
    ) -> str:
        """
        Initiate a payment (deposit) via the Orange Money Collections API.

        Returns the payment_id (our_reference) — stored as Transaction.external_reference
        for webhook reconciliation.

        Raises RuntimeError on non-200/201 response.
        """
        token = await self.get_access_token()

        url = f"{self._base_url}/omcoreapis/1.0.2/mp/pay"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-AUTH-KEY": self._merchant_key,
            "Content-Type": "application/json",
        }
        body = {
            "merchant": {"id": self._merchant_id},
            "money": {"amount": _amount_xaf(amount_units), "cents": 0},
            "customer": {"key": phone_e164},
            "order": {"id": our_reference},
            "return_url": self._callback_url,
            "cancel_url": self._callback_url,
            "notif_url": self._callback_url,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=headers)

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Orange Money pay failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )

        logger.info(
            "Orange Money deposit initiated: ref=%s amount_xaf=%d phone=%s",
            our_reference, _amount_xaf(amount_units), phone_e164,
        )
        # We use our reference as the external_reference for lookup at callback time
        return our_reference

    async def get_payment_status(self, order_id: str) -> str:
        """
        Poll the status of a previously initiated payment by order ID (our reference).

        Returns one of: "SUCCESSFUL" | "FAILED" | "PENDING".
        Used as fallback when webhook is not received within 125s.
        """
        token = await self.get_access_token()
        url = f"{self._base_url}/omcoreapis/1.0.2/mp/pay/{order_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-AUTH-KEY": self._merchant_key,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code != 200:
            logger.warning(
                "Orange Money status poll failed: HTTP %d for order_id=%s",
                resp.status_code, order_id,
            )
            return "FAILED"

        data = resp.json()
        # Orange Money returns status in data.status or data.data.status depending on version
        raw_status: str = (
            data.get("status")
            or (data.get("data") or {}).get("status")
            or "FAILED"
        ).upper()

        # Normalise to our standard status strings
        if raw_status in ("SUCCESSFUL", "SUCCESS"):
            return "SUCCESSFUL"
        if raw_status in ("FAILED", "CANCELLED", "EXPIRED"):
            return "FAILED"
        return "PENDING"

    async def transfer(
        self,
        amount_units: int,
        destination_phone: str,
        our_reference: str,
    ) -> str:
        """
        Initiate a disbursement (withdrawal) — send funds from merchant to user's phone.

        Returns our_reference (stored as Transaction.external_reference).
        Raises RuntimeError on non-200/201 response.
        """
        token = await self.get_access_token()

        url = f"{self._base_url}/omcoreapis/1.0.2/mp/transfer"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-AUTH-KEY": self._merchant_key,
            "Content-Type": "application/json",
        }
        body = {
            "merchant": {"id": self._merchant_id},
            "money": {"amount": _amount_xaf(amount_units), "cents": 0},
            "recipient": {"key": destination_phone},
            "order": {"id": our_reference},
            "notif_url": self._callback_url,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=headers)

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Orange Money transfer failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )

        logger.info(
            "Orange Money withdrawal initiated: ref=%s amount_xaf=%d dest=%s",
            our_reference, _amount_xaf(amount_units), destination_phone,
        )
        return our_reference
