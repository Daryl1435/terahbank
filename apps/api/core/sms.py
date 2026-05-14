"""
Termii SMS client — OTP and alert delivery for Cameroon (MTN + Orange).
Skips silently in development when API key is not configured.
"""
import logging

import httpx

from core.config import settings

logger = logging.getLogger("terahbank.sms")

_BASE = settings.TERMII_BASE_URL


async def send_sms(phone_e164: str, message: str, msg_type: str = "ALERT") -> None:
    """Send a plain SMS via Termii. msg_type: OTP | ALERT | REMINDER."""
    if not settings.TERMII_API_KEY:
        logger.warning("TERMII_API_KEY not set — SMS skipped: %s", message[:40])
        return

    payload = {
        "to": phone_e164,
        "from": settings.TERMII_SENDER_ID,
        "sms": message,
        "type": "plain",
        "channel": "generic",
        "api_key": settings.TERMII_API_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{_BASE}/sms/send", json=payload)
            resp.raise_for_status()
            logger.info("SMS sent to %s (type=%s)", phone_e164[:7] + "****", msg_type)
    except Exception as exc:
        logger.error("SMS delivery failed to %s: %s", phone_e164[:7] + "****", exc)
        raise


async def send_otp_sms(phone_e164: str, otp_code: str) -> None:
    """Send OTP code via SMS."""
    message = f"Votre code TerahBank est : {otp_code}. Valable 5 minutes. Ne le partagez jamais."
    await send_sms(phone_e164, message, msg_type="OTP")
