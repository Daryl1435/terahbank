"""
VISA Card-Issuing Partner Gateway client.

PCI-DSS scope: TerahBank is SAQ-A (lightest tier).
Raw cardholder data (PAN, CVV, expiry) NEVER stored, processed, or transmitted here.

Two capabilities:
  1. Payment sessions (card deposit):
     - createPaymentSession() → returns a hosted payment URL.
     - User enters card details on the partner's PCI-certified hosted page.
     - Partner sends webhook to /webhooks/visa-card confirming success/failure.
     - Only card_token (opaque) + last_four stored on success — never raw PAN.

  2. Virtual card issuance (card management):
     - issueCard() → partner returns card_token + last_four + expiry_date.
     - We store ONLY these three fields — partner manages the full card lifecycle.
     - Freeze/unfreeze is a local DB status change + optional partner API call.

Webhook validation:
  - HMAC-SHA256 over raw request body using VISA_GATEWAY_WEBHOOK_SECRET.
  - Partner sends signature in X-Visa-Signature header.
  - Always return HTTP 200 even on failure (prevents retry storm).

CRITICAL: This client is called from request handlers (payment session creation)
          and BullMQ workers are NOT needed — card payment is synchronous on the
          partner side. Webhook arrives after user completes hosted form.
"""

import hashlib
import hmac
import logging
from datetime import date

import httpx

from core.config import settings

logger = logging.getLogger("terahbank.visa_gateway")


def validate_visa_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    Validate HMAC-SHA256 signature on an inbound VISA gateway webhook.

    Returns True only when the HMAC matches. Constant-time comparison prevents
    timing attacks. Caller must return HTTP 200 even on failure.
    """
    if not secret or not signature:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected.lower(), signature.lower())


class VisaGatewayClient:
    """
    Async VISA card-issuing partner API client.
    Instantiate per request — stateless beyond configuration.
    """

    def __init__(self) -> None:
        self._base_url    = settings.VISA_GATEWAY_BASE_URL.rstrip("/")
        self._api_key     = settings.VISA_GATEWAY_API_KEY
        self._merchant_id = settings.VISA_GATEWAY_MERCHANT_ID
        self._callback_url   = settings.VISA_GATEWAY_CALLBACK_URL
        self._success_url    = settings.VISA_GATEWAY_SUCCESS_URL
        self._cancel_url     = settings.VISA_GATEWAY_CANCEL_URL
        self._environment    = settings.VISA_GATEWAY_ENVIRONMENT

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "X-Merchant-Id": self._merchant_id,
            "Content-Type": "application/json",
        }

    # ── Deposit: create a hosted payment session ───────────────────────────────

    async def create_payment_session(
        self,
        amount_units: int,
        our_reference: str,    # TXN-YYYYMMDD-XXXX — stored as externalId / order reference
        currency: str = "XAF",
    ) -> str:
        """
        Create a hosted payment session on the VISA partner's platform.

        Returns the hosted_payment_url — client opens this in a WebView.
        User enters card details on the partner's PCI-certified page.
        Partner redirects to success_url/cancel_url and sends webhook.

        Raises RuntimeError on API failure.
        """
        url = f"{self._base_url}/v1/payment-sessions"
        body = {
            "amount": amount_units // 100,   # Whole XAF units
            "currency": currency,
            "merchantId": self._merchant_id,
            "reference": our_reference,
            "callbackUrl": self._callback_url,
            "successUrl": f"{self._success_url}?ref={our_reference}",
            "cancelUrl": f"{self._cancel_url}?ref={our_reference}",
            "environment": self._environment,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=self._headers())

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"VISA gateway createPaymentSession failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )

        data = resp.json()
        payment_url: str = data.get("paymentUrl") or data.get("payment_url") or data.get("url", "")
        if not payment_url:
            raise RuntimeError("VISA gateway response missing paymentUrl field")

        logger.info(
            "VISA payment session created: ref=%s amount_xaf=%d",
            our_reference, amount_units // 100,
        )
        return payment_url

    async def get_payment_status(self, our_reference: str) -> dict:
        """
        Poll the status of a payment session by our TXN reference.

        Returns dict with keys: status (SUCCESSFUL|FAILED|PENDING),
        card_token, last_four (only on SUCCESSFUL).
        """
        url = f"{self._base_url}/v1/payment-sessions/{our_reference}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers())

        if resp.status_code != 200:
            logger.warning(
                "VISA gateway status poll failed: HTTP %d for ref=%s",
                resp.status_code, our_reference,
            )
            return {"status": "FAILED"}

        data = resp.json()
        raw_status = (data.get("status") or "FAILED").upper()
        if raw_status in ("SUCCESSFUL", "SUCCESS", "APPROVED"):
            return {
                "status": "SUCCESSFUL",
                "card_token": data.get("cardToken") or data.get("card_token"),
                "last_four": data.get("lastFour") or data.get("last_four"),
            }
        if raw_status in ("PENDING", "PROCESSING"):
            return {"status": "PENDING"}
        return {"status": "FAILED", "reason": data.get("failureReason")}

    # ── Virtual card issuance ─────────────────────────────────────────────────

    async def issue_virtual_card(
        self,
        user_id: str,
        account_id: str,
        phone_e164: str,
        full_name: str,
    ) -> dict:
        """
        Request a new virtual VISA prepaid card from the card-issuing partner.

        PCI-DSS: partner manages full card lifecycle. We receive only:
          - card_token  (opaque reference — never expires)
          - last_four   (display only)
          - expiry_date (YYYY-MM-DD)

        Raises RuntimeError on API failure.
        """
        url = f"{self._base_url}/v1/virtual-cards"
        body = {
            "merchantId": self._merchant_id,
            "userId": user_id,
            "accountId": account_id,
            "holderName": full_name,
            "holderPhone": phone_e164,
            "currency": "XAF",
            "environment": self._environment,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=self._headers())

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"VISA gateway issueVirtualCard failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )

        data = resp.json()
        card_token  = data.get("cardToken") or data.get("card_token")
        last_four   = data.get("lastFour")  or data.get("last_four")
        expiry_raw  = data.get("expiryDate") or data.get("expiry_date")   # YYYY-MM-DD or YYYY-MM

        if not all([card_token, last_four, expiry_raw]):
            raise RuntimeError("VISA gateway issue response missing required fields")

        logger.info(
            "VISA virtual card issued: user=%s account=%s last_four=%s",
            user_id, account_id, last_four,
        )
        return {
            "card_token": card_token,
            "last_four": last_four,
            "expiry_date": expiry_raw,
        }

    async def update_card_status(self, card_token: str, action: str) -> bool:
        """
        Notify partner of a card status change (freeze / unfreeze / cancel).

        action: "freeze" | "unfreeze" | "cancel"
        Returns True on success. Local DB status is always updated regardless —
        partner notification is best-effort.
        """
        url = f"{self._base_url}/v1/virtual-cards/{card_token}/status"
        body = {"action": action}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.patch(url, json=body, headers=self._headers())
            if resp.status_code not in (200, 204):
                logger.warning(
                    "VISA gateway card status update failed: HTTP %d action=%s token=%s",
                    resp.status_code, action, card_token[:8],
                )
                return False
        except Exception as exc:
            logger.warning(
                "VISA gateway card status update error: action=%s token=%s error=%s",
                action, card_token[:8], exc,
            )
            return False

        logger.info("VISA card %s: token=%s", action, card_token[:8])
        return True
