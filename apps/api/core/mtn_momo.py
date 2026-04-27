"""
MTN Mobile Money (MoMo) Collections API client.

Authentication:
  - Exchange API key for Bearer access token (valid 1 hour).
  - Token cached in Redis key `mtn_momo:access_token` with 55-min TTL.
  - Auto-refresh on cache miss.

Amounts:
  - All internal DB values are in smallest XAF unit (1 XAF = 100 units).
  - MTN API expects the amount as a string in XAF: amount_xaf = amount_units // 100.

Phone numbers:
  - Our system stores E.164 with leading '+' (e.g. "+237600000001").
  - MTN MSISDN format strips the '+' (e.g. "237600000001").

CRITICAL: This client is called from BullMQ workers only, NEVER from request handlers.
"""

import hashlib
import hmac
import logging
import uuid as _uuid

import httpx

from core.config import settings
from core.redis import get_redis_client, mtn_momo_token_key

logger = logging.getLogger("terahbank.mtn_momo")

# Redis TTL for the access token — 5-min buffer before MTN's 1-hour expiry
_TOKEN_TTL_SECONDS: int = 55 * 60  # 3300 s


def _msisdn(phone_e164: str) -> str:
    """Strip '+' from E.164 phone number for MTN MSISDN format."""
    return phone_e164.lstrip("+")


def _amount_xaf(amount_units: int) -> str:
    """Convert smallest-unit amount to XAF string for MTN API (1 XAF = 100 units)."""
    return str(amount_units // 100)


def validate_mtn_callback_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    Validate HMAC-SHA256 signature on an inbound MTN MoMo callback.

    Returns True only when the HMAC matches. Uses constant-time comparison to
    prevent timing attacks. Caller must return HTTP 200 even on failure (prevents
    MTN from retrying indefinitely), but must NOT process the transaction.
    """
    if not secret or not signature:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected.lower(), signature.lower())


class MTNMoMoClient:
    """
    Async MTN MoMo Collections API client.
    Instantiate per worker call — does not hold state beyond token caching.
    """

    def __init__(self) -> None:
        self._base_url = settings.MTN_MOMO_BASE_URL.rstrip("/")
        self._subscription_key = settings.MTN_MOMO_SUBSCRIPTION_KEY
        self._collection_user_id = settings.MTN_MOMO_COLLECTION_USER_ID
        self._api_key = settings.MTN_MOMO_API_KEY
        self._environment = settings.MTN_MOMO_ENVIRONMENT
        self._callback_url = settings.MTN_MOMO_CALLBACK_URL

    async def get_access_token(self) -> str:
        """
        Return a valid Bearer access token for the Collections API.
        Fetched from Redis cache; refreshed on miss via MTN token endpoint.
        """
        redis = get_redis_client()
        cached = await redis.get(mtn_momo_token_key())
        if cached:
            return cached

        token = await self._fetch_new_token()
        await redis.setex(mtn_momo_token_key(), _TOKEN_TTL_SECONDS, token)
        return token

    async def _fetch_new_token(self) -> str:
        """Exchange API user ID + key for a Bearer access token."""
        url = f"{self._base_url}/collection/token/"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                auth=(self._collection_user_id, self._api_key),
                headers={
                    "Ocp-Apim-Subscription-Key": self._subscription_key,
                },
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"MTN MoMo token fetch failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )
        data = resp.json()
        return data["access_token"]

    async def request_to_pay(
        self,
        amount_units: int,
        phone_e164: str,
        our_reference: str,  # Our TXN-YYYYMMDD-XXXX reference (stored as externalId)
    ) -> str:
        """
        Initiate a Request-to-Pay (deposit) via the MTN Collections API.

        Returns the X-Reference-Id UUID we generated — store this as
        Transaction.external_reference for status polling and reconciliation.

        Raises RuntimeError on non-202 response.
        """
        x_reference_id = str(_uuid.uuid4())
        token = await self.get_access_token()

        url = f"{self._base_url}/collection/v1_0/requesttopay"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": x_reference_id,
            "X-Target-Environment": self._environment,
            "Ocp-Apim-Subscription-Key": self._subscription_key,
            "Content-Type": "application/json",
            "X-Callback-Url": self._callback_url,
        }
        body = {
            "amount": _amount_xaf(amount_units),
            "currency": "XAF",
            "externalId": our_reference,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": _msisdn(phone_e164),
            },
            "payerMessage": f"TerahBank deposit - {our_reference}",
            "payeeNote": "TerahBank savings deposit",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=headers)

        if resp.status_code != 202:
            raise RuntimeError(
                f"MTN MoMo requesttopay failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )

        logger.info(
            "MTN MoMo deposit initiated: x_ref=%s our_ref=%s amount_xaf=%s phone=%s",
            x_reference_id, our_reference, _amount_xaf(amount_units), _msisdn(phone_e164),
        )
        return x_reference_id

    async def get_payment_status(self, x_reference_id: str) -> str:
        """
        Poll the status of a previously initiated Request-to-Pay.

        Returns one of: "SUCCESSFUL" | "FAILED" | "PENDING".
        Used as fallback when webhook is not received within 120s.
        """
        token = await self.get_access_token()
        url = f"{self._base_url}/collection/v1_0/requesttopay/{x_reference_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Target-Environment": self._environment,
            "Ocp-Apim-Subscription-Key": self._subscription_key,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code != 200:
            logger.warning(
                "MTN MoMo status poll failed: HTTP %d for x_ref=%s",
                resp.status_code, x_reference_id,
            )
            return "FAILED"

        data = resp.json()
        status = data.get("status", "FAILED")
        logger.info("MTN MoMo status poll: x_ref=%s status=%s", x_reference_id, status)
        return status
