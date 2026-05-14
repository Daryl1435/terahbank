"""
BullMQ notification worker — processes queue:notifications jobs.

Job names:
  send_sms   — Termii SMS delivery (OTP, ALERT, REMINDER)
  send_email — SendGrid template email
  send_push  — FCM push to all user device tokens

Retry policy: attempts=3, exponential backoff (safe — notifications are idempotent).
"""
import logging

from bullmq import Worker

from core.redis import get_redis_client

logger = logging.getLogger("terahbank.jobs.notifications")


async def _process_notification(job, token):  # type: ignore[override]
    name = job.name
    data = job.data or {}
    logger.info("Processing notification job: %s (id=%s)", name, job.id)

    try:
        if name == "send_sms":
            await _handle_sms(data)
        elif name == "send_email":
            await _handle_email(data)
        elif name == "send_push":
            await _handle_push(data)
        else:
            logger.warning("Unknown notification job: %s", name)
    except Exception as exc:
        logger.error("Notification job %s failed (attempt %s): %s", name, job.attemptsMade, exc)
        raise   # BullMQ will retry per the attempts/backoff policy


async def _handle_sms(data: dict) -> None:
    from core.sms import send_sms

    to = data.get("to", "")
    message = data.get("message", "")
    msg_type = data.get("msg_type", "ALERT")

    if not to or not message:
        logger.warning("send_sms job missing 'to' or 'message' — skipping")
        return

    await send_sms(to, message, msg_type)


async def _handle_email(data: dict) -> None:
    from core.email import send_email
    from core.config import settings

    template_key = data.get("template_id", "")
    # Map logical template names to SendGrid template IDs
    template_map = {
        "welcome":              settings.SENDGRID_TEMPLATE_WELCOME,
        "kyc_approved":         settings.SENDGRID_TEMPLATE_KYC_APPROVED,
        "kyc_rejected":         settings.SENDGRID_TEMPLATE_KYC_REJECTED,
        "transaction_success":  settings.SENDGRID_TEMPLATE_TRANSACTION_SUCCESS,
        "transaction_failed":   settings.SENDGRID_TEMPLATE_TRANSACTION_FAILED,
        "monthly_summary":      settings.SENDGRID_TEMPLATE_MONTHLY_SUMMARY,
        "maturity_reminder":    settings.SENDGRID_TEMPLATE_MATURITY_REMINDER,
    }
    template_id = template_map.get(template_key, "")

    await send_email(
        to_email=data.get("to_email", ""),
        to_name=data.get("to_name", ""),
        template_id=template_id,
        dynamic_data=data.get("dynamic_data", {}),
    )


async def _handle_push(data: dict) -> None:
    from core.push import send_push_multicast
    from core.database import AsyncSessionLocal
    from modules.notifications.repository import NotificationRepository
    import uuid as _uuid

    user_id_str = data.get("user_id", "")
    if not user_id_str:
        return

    user_id = _uuid.UUID(user_id_str)
    title = data.get("title", "")
    body = data.get("body", "")
    push_data = data.get("data", {})

    async with AsyncSessionLocal() as db:
        repo = NotificationRepository(db)
        tokens = await repo.get_tokens_for_user(user_id)

    if not tokens:
        logger.debug("No device tokens for user %s — push skipped", user_id_str)
        return

    await send_push_multicast(tokens, title, body, push_data)


def create_notification_worker() -> Worker:
    redis = get_redis_client()
    return Worker(
        "notifications",
        _process_notification,
        {"connection": redis},
    )
