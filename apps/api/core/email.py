"""
SendGrid email client — transactional emails via dynamic templates.
Skips silently in development when API key is not configured.
"""
import logging

import httpx

from core.config import settings

logger = logging.getLogger("terahbank.email")

_BASE = "https://api.sendgrid.com/v3"


async def send_email(
    to_email: str,
    to_name: str,
    template_id: str,
    dynamic_data: dict,
) -> None:
    """Send a transactional email via SendGrid dynamic template."""
    if not settings.SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — email skipped to %s", to_email)
        return
    if not template_id:
        logger.warning("No template_id configured — email skipped to %s", to_email)
        return

    payload = {
        "from": {
            "email": settings.SENDGRID_FROM_EMAIL,
            "name": settings.SENDGRID_FROM_NAME,
        },
        "personalizations": [
            {
                "to": [{"email": to_email, "name": to_name}],
                "dynamic_template_data": dynamic_data,
            }
        ],
        "template_id": template_id,
    }

    headers = {
        "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{_BASE}/mail/send", json=payload, headers=headers)
            resp.raise_for_status()
            logger.info("Email sent to %s (template=%s)", to_email, template_id)
    except Exception as exc:
        logger.error("Email delivery failed to %s: %s", to_email, exc)
        raise


# ── Typed helpers ─────────────────────────────────────────────────────────────

async def send_welcome_email(to_email: str, full_name: str) -> None:
    await send_email(
        to_email, full_name,
        settings.SENDGRID_TEMPLATE_WELCOME,
        {"first_name": full_name.split()[0], "full_name": full_name},
    )


async def send_kyc_approved_email(to_email: str, full_name: str) -> None:
    await send_email(
        to_email, full_name,
        settings.SENDGRID_TEMPLATE_KYC_APPROVED,
        {"first_name": full_name.split()[0]},
    )


async def send_kyc_rejected_email(to_email: str, full_name: str, reason: str) -> None:
    await send_email(
        to_email, full_name,
        settings.SENDGRID_TEMPLATE_KYC_REJECTED,
        {"first_name": full_name.split()[0], "rejection_reason": reason},
    )


async def send_transaction_failed_email(
    to_email: str, full_name: str, amount_xaf: str, channel: str
) -> None:
    await send_email(
        to_email, full_name,
        settings.SENDGRID_TEMPLATE_TRANSACTION_FAILED,
        {"first_name": full_name.split()[0], "amount": amount_xaf, "channel": channel},
    )


async def send_maturity_reminder_email(
    to_email: str, full_name: str, account_name: str, days_left: int, maturity_amount: str
) -> None:
    await send_email(
        to_email, full_name,
        settings.SENDGRID_TEMPLATE_MATURITY_REMINDER,
        {
            "first_name": full_name.split()[0],
            "account_name": account_name,
            "days_left": days_left,
            "maturity_amount": maturity_amount,
        },
    )


async def send_monthly_summary_email(
    to_email: str, full_name: str, summary_data: dict
) -> None:
    await send_email(
        to_email, full_name,
        settings.SENDGRID_TEMPLATE_MONTHLY_SUMMARY,
        {"first_name": full_name.split()[0], **summary_data},
    )
