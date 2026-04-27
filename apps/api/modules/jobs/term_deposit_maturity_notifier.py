"""
FR-028: Term Deposit maturity notifier — scheduled BullMQ job.

Schedule: 0 7 * * * (daily at 07:00 UTC = 08:00 CAT)
Queue:    queue:scheduled

Worker behavior:
  1. Compute check_dates = [today+14d, today+7d, today+1d]
  2. Query all active term_deposit accounts whose maturity_date is in check_dates
  3. For each match: dispatch a push/email notification stub (Milestone 6.2)

Notification thresholds: 14 days, 7 days, 1 day before maturity.
"""

import logging
from datetime import date, timedelta

from bullmq import Queue, Worker

from core.config import settings

logger = logging.getLogger("terahbank.jobs.term_deposit_maturity_notifier")

QUEUE_NAME = "queue:scheduled"
JOB_NAME = "term_deposit_maturity_notifier"
CRON_EXPRESSION = "0 7 * * *"  # daily at 07:00 UTC

# Days before maturity at which we notify users
ALERT_DAYS: list[int] = [14, 7, 1]


async def process_term_deposit_maturity_notifier(job, token: str) -> None:  # type: ignore[no-untyped-def]
    """
    BullMQ worker processor — called once per day.
    Finds term deposits maturing in 14, 7, or 1 day and dispatches notifications.
    """
    today = date.today()
    logger.info("Term deposit maturity notifier started: today=%s", today.isoformat())

    check_dates = [today + timedelta(days=d) for d in ALERT_DAYS]

    try:
        from core.database import AsyncSessionLocal
        from modules.accounts.repository import AccountRepository

        async with AsyncSessionLocal() as db:
            repo = AccountRepository(db)
            maturing_accounts = await repo.list_term_deposits_maturing_on(check_dates)

            logger.info(
                "Maturity notifier: found %d accounts maturing in %s",
                len(maturing_accounts), ALERT_DAYS,
            )

            for account in maturing_accounts:
                days_remaining = (account.maturity_date - today).days
                _dispatch_maturity_notification(account, days_remaining)

    except Exception as exc:
        logger.exception("Term deposit maturity notifier failed: %s", exc)
        raise


def _dispatch_maturity_notification(account, days_remaining: int) -> None:
    """
    Dispatch a maturity notification stub for a term deposit account.
    Implemented in Milestone 6.2 (push + email).
    """
    logger.info(
        "MATURITY_ALERT_%dd: account=%s user=%s maturity=%s — TODO Milestone 6.2: enqueue notification",
        days_remaining, account.id, account.user_id, account.maturity_date,
    )
    # TODO Milestone 6.2:
    # await enqueue_notification(queue:notifications, {
    #     "name": "send_maturity_alert",
    #     "data": {
    #         "user_id": str(account.user_id),
    #         "account_id": str(account.id),
    #         "days_remaining": days_remaining,
    #         "maturity_date": account.maturity_date.isoformat(),
    #         "principal": account.balance,
    #     },
    #     "opts": {"attempts": 3, "backoff": {"type": "exponential", "delay": 5000}},
    # })


async def register_term_deposit_maturity_job() -> None:
    """
    Register the term_deposit_maturity_notifier repeating job with BullMQ.
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
            "repeat": {"cron": CRON_EXPRESSION},
            "attempts": 1,
            "removeOnComplete": False,
            "removeOnFail": False,
        },
    )
    logger.info("Registered scheduled job: %s cron=%s", JOB_NAME, CRON_EXPRESSION)
    await queue.close()


def create_worker() -> Worker:
    """
    Create and return a BullMQ Worker for the maturity notifier queue.
    Call from the worker process (python -m modules.jobs.worker), NOT from the API.
    """
    return Worker(
        QUEUE_NAME,
        process_term_deposit_maturity_notifier,
        {"connection": {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}},
    )
