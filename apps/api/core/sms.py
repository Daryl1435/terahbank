"""
Twilio SMS client with monthly budget tracking.

Budget logic:
  - Redis key sms:count:YYYY:MM tracks how many SMS were sent this month.
  - When count >= SMS_MONTHLY_LIMIT, raises SMSBudgetExhaustedError.
  - Admin email is sent once at 80% and once at 100% of the budget.
  - OTP callers must NOT catch SMSBudgetExhaustedError (auth must never silently fail).
  - ALERT callers should catch it and fall back to email.
"""
import logging
from base64 import b64encode
from datetime import datetime

import httpx

from core.config import settings

logger = logging.getLogger("terahbank.sms")

_TWILIO_BASE = "https://api.twilio.com/2010-04-01"


class SMSBudgetExhaustedError(Exception):
    """Monthly SMS limit reached. ALERT callers should fall back to email."""


# ── Redis key helpers ──────────────────────────────────────────────────────────

def _count_key() -> str:
    now = datetime.now()
    return f"sms:count:{now.year}:{now.month:02d}"


def _alerted_key(threshold: int) -> str:
    now = datetime.now()
    return f"sms:alerted:{threshold}:{now.year}:{now.month:02d}"


# ── Budget helpers ─────────────────────────────────────────────────────────────

async def get_sms_usage() -> tuple[int, int]:
    """Return (sms_sent_this_month, monthly_limit)."""
    from core.redis import get_redis_client
    redis = get_redis_client()
    raw = await redis.get(_count_key())
    return int(raw or 0), settings.SMS_MONTHLY_LIMIT


async def _after_send_checks(new_count: int) -> None:
    """Fire one-time admin email alerts when budget crosses 80% or 100%."""
    limit = settings.SMS_MONTHLY_LIMIT
    if limit <= 0:
        return

    pct = (new_count / limit) * 100

    thresholds = [(100, "🚨 Budget SMS ÉPUISÉ"), (80, "⚠️ Budget SMS à 80%")]
    for threshold, subject in thresholds:
        if pct >= threshold:
            from core.redis import get_redis_client
            redis = get_redis_client()
            already_sent = await redis.get(_alerted_key(threshold))
            if already_sent:
                break
            await redis.setex(_alerted_key(threshold), 40 * 86400, "1")
            await _send_budget_alert(threshold, new_count, limit, subject)
            break  # only fire the highest crossed threshold


async def _send_budget_alert(threshold: int, used: int, limit: int, subject: str) -> None:
    if not settings.ADMIN_ALERT_EMAIL:
        logger.warning("SMS at %d%% but ADMIN_ALERT_EMAIL not set — alert skipped", threshold)
        return

    month = datetime.now().strftime("%B %Y")
    body = (
        f"Alerte budget SMS — TerahBank\n\n"
        f"Mois       : {month}\n"
        f"Utilisation: {used} / {limit} SMS ({threshold}%)\n\n"
    )
    if threshold >= 100:
        body += (
            "Les SMS sont maintenant BLOQUÉS.\n"
            "Les alertes de transactions sont envoyées par email à la place.\n"
            "Les OTP de connexion sont également bloqués — rechargez Twilio immédiatement.\n\n"
            "Action requise: connectez-vous sur console.twilio.com et rechargez votre solde."
        )
    else:
        body += (
            f"Il vous reste environ {limit - used} SMS pour le reste du mois.\n"
            "Pensez à recharger votre compte Twilio."
        )

    try:
        from core.email import send_plain_email
        await send_plain_email(settings.ADMIN_ALERT_EMAIL, subject, body)
    except Exception as exc:
        logger.error("Failed to send SMS budget alert email: %s", exc)


# ── Public API ─────────────────────────────────────────────────────────────────

async def send_sms(phone_e164: str, message: str, msg_type: str = "ALERT") -> None:
    """
    Send SMS via Twilio.

    Raises SMSBudgetExhaustedError if the monthly limit is reached.
    - OTP callers: do NOT catch this — a blocked auth OTP must surface as an error.
    - ALERT callers: catch this and fall back to email notification.
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Twilio credentials not set — SMS skipped (type=%s)", msg_type)
        return

    # ── Budget gate ────────────────────────────────────────────────────────────
    used, limit = await get_sms_usage()
    if limit > 0 and used >= limit:
        logger.warning(
            "SMS budget exhausted (%d/%d) — blocking %s to %s",
            used, limit, msg_type, phone_e164[:7] + "****",
        )
        raise SMSBudgetExhaustedError(f"Monthly SMS limit of {limit} reached ({used} used)")

    # ── Send via Twilio ────────────────────────────────────────────────────────
    url = f"{_TWILIO_BASE}/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                headers={"Authorization": "Basic " + b64encode(
                    f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}".encode()
                ).decode()},
                data={
                    "From": settings.TWILIO_PHONE_NUMBER,
                    "To": phone_e164,
                    "Body": message,
                },
            )
            resp.raise_for_status()
            sid = resp.json().get("sid", "")

        # ── Increment budget counter ───────────────────────────────────────────
        from core.redis import get_redis_client
        redis = get_redis_client()
        new_count = await redis.incr(_count_key())
        await redis.expire(_count_key(), 40 * 86400)  # auto-expire after ~40 days

        await _after_send_checks(new_count)

        logger.info(
            "SMS sent to %s (type=%s sid=%s count=%d/%d)",
            phone_e164[:7] + "****", msg_type, sid, new_count, limit,
        )

    except SMSBudgetExhaustedError:
        raise
    except Exception as exc:
        logger.error("SMS delivery failed to %s: %s", phone_e164[:7] + "****", exc)
        raise


async def send_otp_sms(phone_e164: str, otp_code: str) -> None:
    """
    Send OTP via SMS. Never falls back silently — auth must never be bypassed.
    If budget is exhausted, this raises SMSBudgetExhaustedError which the auth
    service converts to a 503 response so the user knows to retry later.
    """
    message = (
        f"Votre code TerahBank est : {otp_code}. "
        "Valable 5 minutes. Ne le partagez jamais."
    )
    await send_sms(phone_e164, message, msg_type="OTP")
