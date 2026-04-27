"""
FR-045: Insurance policy renewal reminder — scheduled BullMQ job.

Schedule: 0 9 * * * (daily at 09:00 UTC = 10:00 CAT)
Queue:    queue:scheduled

Worker behavior:
  1. Compute check_dates = [today+30d, today+7d]
  2. Query all active insurance_policies whose expiry_date is in check_dates
  3. For each match: dispatch a renewal notification stub (Milestone 6.2)
"""

import logging
from datetime import date, timedelta

from bullmq import Queue, Worker

from core.config import settings

logger = logging.getLogger("terahbank.jobs.insurance_renewal_notifier")

QUEUE_NAME      = "queue:scheduled"
JOB_NAME        = "insurance_renewal_notifier"
CRON_EXPRESSION = "0 9 * * *"   # daily at 09:00 UTC (10:00 CAT)

ALERT_DAYS: list[int] = [30, 7]


async def process_insurance_renewal_notifier(job, token: str) -> None:  # type: ignore[no-untyped-def]
    """
    BullMQ worker processor — called once per day.
    Finds insurance policies expiring in 30 or 7 days and dispatches notifications.
    """
    today = date.today()
    logger.info("Insurance renewal notifier started: today=%s", today.isoformat())

    check_dates = [today + timedelta(days=d) for d in ALERT_DAYS]

    try:
        from core.database import AsyncSessionLocal
        from modules.insurance.repository import InsuranceRepository

        async with AsyncSessionLocal() as db:
            repo = InsuranceRepository(db)
            expiring = await repo.list_expiring_policies(check_dates)

            logger.info(
                "Renewal notifier: found %d policies expiring in %s days",
                len(expiring), ALERT_DAYS,
            )

            for policy in expiring:
                days_remaining = (policy.expiry_date - today).days
                _dispatch_renewal_notification(policy, days_remaining)

    except Exception as exc:
        logger.exception("Insurance renewal notifier failed: %s", exc)
        raise


def _dispatch_renewal_notification(policy, days_remaining: int) -> None:
    """
    Dispatch a renewal notification stub.
    Full push + email implementation in Milestone 6.2.
    """
    logger.info(
        "INSURANCE_RENEWAL_%dd: policy=%s user=%s partner=%s expiry=%s — TODO Milestone 6.2: enqueue notification",
        days_remaining,
        policy.id,
        policy.user_id,
        policy.partner_id,
        policy.expiry_date,
    )
    # TODO Milestone 6.2:
    # await enqueue_notification(queue:notifications, {
    #     "name": "send_insurance_renewal_reminder",
    #     "data": {
    #         "user_id": str(policy.user_id),
    #         "policy_id": str(policy.id),
    #         "partner_id": policy.partner_id,
    #         "product_name": policy.product_name,
    #         "policy_type": policy.policy_type,
    #         "days_remaining": days_remaining,
    #         "expiry_date": policy.expiry_date.isoformat(),
    #     },
    #     "opts": {"attempts": 3, "backoff": {"type": "exponential", "delay": 5000}},
    # })


async def register_insurance_renewal_job() -> None:
    """
    Register the insurance_renewal_notifier repeating job with BullMQ.
    Called once at application startup. BullMQ deduplicates repeating jobs.
    """
    queue = Queue(
        QUEUE_NAME,
        {"connection": {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}},
    )
    await queue.add(
        JOB_NAME,
        {},
        {
            "repeat":           {"cron": CRON_EXPRESSION},
            "attempts":         1,
            "removeOnComplete": False,
            "removeOnFail":     False,
        },
    )
    logger.info("Registered scheduled job: %s cron=%s", JOB_NAME, CRON_EXPRESSION)
    await queue.close()


def create_worker() -> Worker:
    """
    Create and return a BullMQ Worker for the insurance renewal queue.
    Call from the worker process (python -m modules.jobs.worker), NOT from the API.
    """
    return Worker(
        QUEUE_NAME,
        process_insurance_renewal_notifier,
        {"connection": {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}},
    )
