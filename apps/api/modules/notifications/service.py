"""
NotificationService — orchestrates in-app storage + BullMQ dispatch.

All notification sends go through enqueue_notification() which puts a job on
queue:notifications. The notification_processor worker picks it up and calls
the actual SMS/email/push clients (Termii / SendGrid / FCM).

In-app notifications are written to the DB synchronously so the bell count
is immediately accurate without waiting for the worker.
"""
import logging
import uuid
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit_log
from core.schemas import TerahResponse

from .repository import NotificationRepository
from .schemas import (
    NotificationData,
    NotificationListData,
    PreferencesData,
    UnreadCountData,
    UpdatePreferencesRequest,
)

logger = logging.getLogger("terahbank.notifications")


# ── BullMQ enqueue helper ─────────────────────────────────────────────────────

async def enqueue_notification(job_name: str, data: dict) -> None:
    """Push a notification job onto queue:notifications (attempts=3, exponential backoff)."""
    try:
        from bullmq import Queue
        from core.redis import get_redis_client

        redis = get_redis_client()
        queue = Queue("notifications", {"connection": redis})
        await queue.add(
            job_name,
            data,
            opts={"attempts": 3, "backoff": {"type": "exponential", "delay": 3000}},
        )
    except Exception as exc:
        logger.error("Failed to enqueue notification job %s: %s", job_name, exc)


# ── Typed dispatch helpers (called from other services) ───────────────────────

async def dispatch_otp_sms(phone_e164: str, otp_code: str) -> None:
    """
    Send OTP via SMS synchronously (not queued — OTPs are time-sensitive).
    Raises SMSBudgetExhaustedError if the monthly limit or Twilio rate limit is reached.
    Callers (auth service) must catch this and return HTTP 503.

    In APP_ENV=development the OTP is always logged so it can be used even if
    SMS delivery fails. SMSBudgetExhaustedError is still re-raised so the API
    returns 503 — this makes the mobile show the OTP from the response field
    `otp_dev` instead of waiting for an SMS that will never arrive.
    """
    from core.config import settings
    from core.sms import SMSBudgetExhaustedError, send_otp_sms

    # Always log in dev so the OTP is usable from the terminal even when SMS fails
    if settings.APP_ENV == "development":
        logger.warning("╔══════════════════════════════╗")
        logger.warning("║  DEV OTP  %-6s  →  %-6s  ║", phone_e164[-6:], otp_code)
        logger.warning("╚══════════════════════════════╝")

    try:
        await send_otp_sms(phone_e164, otp_code)
    except SMSBudgetExhaustedError:
        # Always surface budget/rate-limit errors so auth returns 503
        raise
    except Exception as exc:
        if settings.APP_ENV == "development":
            # Non-budget SMS failures in dev are non-fatal — OTP is already logged
            logger.warning("Dev SMS delivery failed (use otp_dev from response): %s", exc)
        else:
            raise


async def dispatch_push_and_inapp(
    db: AsyncSession,
    user_id: UUID,
    notif_type: str,
    title: str,
    body: str,
    metadata: dict | None = None,
) -> None:
    """Write in-app notification to DB + enqueue push job."""
    repo = NotificationRepository(db)
    prefs = await repo.get_preferences(user_id)

    if prefs.in_app_enabled:
        await repo.create(user_id=user_id, type=notif_type, title=title, body=body, metadata=metadata)

    if prefs.push_enabled:
        await enqueue_notification("send_push", {
            "user_id": str(user_id),
            "title": title,
            "body": body,
            "data": {"type": notif_type, **(metadata or {})},
        })


async def dispatch_kyc_approved(db: AsyncSession, user) -> None:
    title = "KYC approuvé ✅"
    body = "Votre identité a été vérifiée. Vous pouvez maintenant effectuer des transactions."
    await dispatch_push_and_inapp(db, user.id, "KYC_APPROVED", title, body)
    await enqueue_notification("send_email", {
        "to_email": user.email,
        "to_name": user.full_name,
        "template_id": "kyc_approved",
        "dynamic_data": {"first_name": user.full_name.split()[0]},
    })


async def dispatch_kyc_rejected(db: AsyncSession, user, reason: str) -> None:
    title = "KYC refusé"
    body = f"Votre dossier KYC a été refusé : {reason}. Veuillez soumettre à nouveau."
    await dispatch_push_and_inapp(db, user.id, "KYC_REJECTED", title, body, {"reason": reason})
    await enqueue_notification("send_email", {
        "to_email": user.email,
        "to_name": user.full_name,
        "template_id": "kyc_rejected",
        "dynamic_data": {"first_name": user.full_name.split()[0], "rejection_reason": reason},
    })


async def dispatch_transaction_success(
    db: AsyncSession, user, amount_xaf: str, txn_type: str, txn_id: str
) -> None:
    title = "Transaction réussie ✅"
    body = f"{txn_type.capitalize()} de {amount_xaf} XAF confirmé."
    await dispatch_push_and_inapp(
        db, user.id, "TRANSACTION_SUCCESS", title, body,
        {"transaction_id": txn_id, "amount": amount_xaf, "type": txn_type},
    )


async def dispatch_transaction_failed(
    db: AsyncSession, user, amount_xaf: str, txn_type: str, txn_id: str
) -> None:
    title = "Transaction échouée"
    body = f"Votre {txn_type} de {amount_xaf} XAF a échoué. Aucun débit effectué."
    await dispatch_push_and_inapp(
        db, user.id, "TRANSACTION_FAILED", title, body,
        {"transaction_id": txn_id, "amount": amount_xaf, "type": txn_type},
    )
    from core.sms import SMSBudgetExhaustedError, get_sms_usage
    used, limit = await get_sms_usage()
    if limit > 0 and used >= limit:
        logger.warning("SMS budget exhausted — falling back to email for TRANSACTION_FAILED alert (user=%s)", user.id)
        await enqueue_notification("send_email", {
            "to_email": user.email,
            "to_name": user.full_name,
            "template_id": "transaction_failed",
            "dynamic_data": {
                "first_name": user.full_name.split()[0],
                "amount": amount_xaf,
                "channel": txn_type,
            },
        })
    else:
        await enqueue_notification("send_sms", {
            "to": user.phone_number,
            "message": f"TerahBank: Votre {txn_type} de {amount_xaf} XAF a echoue. Contactez le support si necessaire.",
            "msg_type": "ALERT",
        })


async def dispatch_project_milestone(
    db: AsyncSession, user, project_name: str, milestone: int, account_id: str
) -> None:
    title = f"Objectif {milestone}% atteint ! 🎉"
    body = f"Votre projet « {project_name} » a atteint {milestone}% de son objectif."
    await dispatch_push_and_inapp(
        db, user.id, f"PROJECT_MILESTONE_{milestone}", title, body,
        {"account_id": account_id, "milestone": milestone, "project_name": project_name},
    )


async def dispatch_maturity_reminder(
    db: AsyncSession, user, account_name: str, days_left: int, amount_xaf: str, account_id: str
) -> None:
    title = f"Dépôt à terme : {days_left} jour(s) restant(s)"
    body = f"Votre dépôt « {account_name} » arrive à échéance dans {days_left} jour(s). Montant: {amount_xaf} XAF."
    await dispatch_push_and_inapp(
        db, user.id, "MATURITY_REMINDER", title, body,
        {"account_id": account_id, "days_left": days_left},
    )
    await enqueue_notification("send_email", {
        "to_email": user.email,
        "to_name": user.full_name,
        "template_id": "maturity_reminder",
        "dynamic_data": {
            "first_name": user.full_name.split()[0],
            "account_name": account_name,
            "days_left": days_left,
            "maturity_amount": amount_xaf,
        },
    })


# ── NotificationService (HTTP-layer operations) ───────────────────────────────

class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._repo = NotificationRepository(db)

    async def list_notifications(self, user) -> TerahResponse:
        notifications = await self._repo.list_for_user(user.id, limit=50)
        unread = await self._repo.unread_count(user.id)
        return TerahResponse(
            success=True,
            data=NotificationListData(
                notifications=[
                    NotificationData(
                        notification_id=str(n.id),
                        type=n.type,
                        title=n.title,
                        body=n.body,
                        metadata=n.metadata_,
                        read=n.read_at is not None,
                        created_at=n.created_at,
                    )
                    for n in notifications
                ],
                unread_count=unread,
            ).model_dump(mode="json"),
        )

    async def get_unread_count(self, user) -> TerahResponse:
        count = await self._repo.unread_count(user.id)
        return TerahResponse(success=True, data=UnreadCountData(unread_count=count).model_dump())

    async def mark_read(self, notification_id: UUID, user) -> TerahResponse:
        success = await self._repo.mark_read(notification_id, user.id)
        return TerahResponse(success=success)

    async def mark_all_read(self, user) -> TerahResponse:
        await self._repo.mark_all_read(user.id)
        return TerahResponse(success=True)

    async def get_preferences(self, user) -> TerahResponse:
        prefs = await self._repo.get_preferences(user.id)
        return TerahResponse(
            success=True,
            data=PreferencesData(
                push_enabled=prefs.push_enabled,
                email_enabled=prefs.email_enabled,
                sms_enabled=prefs.sms_enabled,
                in_app_enabled=prefs.in_app_enabled,
                transaction_alerts=prefs.transaction_alerts,
                security_alerts=prefs.security_alerts,
                monthly_summary=prefs.monthly_summary,
                milestone_alerts=prefs.milestone_alerts,
                maturity_reminders=prefs.maturity_reminders,
            ).model_dump(),
        )

    async def update_preferences(self, payload: UpdatePreferencesRequest, user) -> TerahResponse:
        updates = payload.model_dump(exclude_none=True)
        prefs = await self._repo.update_preferences(user.id, updates)
        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="NOTIFICATION_PREFERENCES_UPDATED",
            entity_type="notification_preferences",
            entity_id=str(user.id),
            metadata=updates,
        )
        await self.db.commit()
        return await self.get_preferences(user)

    async def register_device_token(self, token: str, platform: str, user) -> TerahResponse:
        await self._repo.upsert_device_token(user.id, token, platform)
        await self.db.commit()
        return TerahResponse(success=True)
