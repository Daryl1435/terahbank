"""
FR-014: Monthly savings summary — scheduled BullMQ job.

Schedule: 0 7 1 * * (UTC) = 1st of every month at 08:00 CAT (UTC+1)
Queue:    queue:scheduled

Worker behavior:
  1. Query all users with account_status = 'active'
  2. Process in batches of 100 to avoid DB overload
  3. For each user: calculate monthly stats → log summary
  4. TODO Milestone 6.2: enqueue send_email + send_push_notification per user

The worker function is registered via register_monthly_savings_job() called at startup.
In production: run this worker as a separate ECS task (not inside the API process).
"""

import logging
from datetime import date

from bullmq import Queue, Worker

from core.config import settings

logger = logging.getLogger("terahbank.jobs.monthly_savings_summary")

QUEUE_NAME = "queue:scheduled"
JOB_NAME = "monthly_savings_summary"

# Cron: 1st of every month at 07:00 UTC (= 08:00 CAT)
CRON_EXPRESSION = "0 7 1 * *"


async def process_monthly_savings_summary(job, token: str) -> None:  # type: ignore[no-untyped-def]
    """
    BullMQ worker processor — called for each job execution.

    job.data shape:
        { "month": "2026-04", "batch_size": 100 }
    """
    month: str = job.data.get("month", date.today().strftime("%Y-%m"))
    batch_size: int = int(job.data.get("batch_size", 100))

    logger.info("Monthly savings summary started: month=%s", month)

    try:
        from sqlalchemy import select

        from core.database import AsyncSessionLocal
        from modules.auth.models import User

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.account_status == "active")
            )
            users = list(result.scalars().all())

        total_users = len(users)
        logger.info("Processing %d active users in batches of %d", total_users, batch_size)

        for batch_start in range(0, total_users, batch_size):
            batch = users[batch_start : batch_start + batch_size]
            for user in batch:
                # TODO Milestone 6.2: calculate real monthly stats from transactions
                # then enqueue send_email and send_push_notification per user.
                # Example payload for send_email job:
                #   {
                #     "to": user.email,
                #     "template_id": "d-monthly-savings-summary",
                #     "dynamic_data": {
                #       "user_name": user.full_name,
                #       "total_saved": "...",
                #       "month": month,
                #     }
                #   }
                logger.debug(
                    "Monthly summary queued (stub): user=%s month=%s", user.id, month
                )

            logger.info(
                "Processed batch %d–%d of %d",
                batch_start + 1,
                min(batch_start + batch_size, total_users),
                total_users,
            )

        logger.info("Monthly savings summary complete: month=%s users=%d", month, total_users)

    except Exception as exc:
        logger.exception("Monthly savings summary failed: month=%s error=%s", month, exc)
        raise  # BullMQ will mark the job as failed


async def register_monthly_savings_job() -> None:
    """
    Register the monthly_savings_summary repeating job with BullMQ.

    Called once at application startup. BullMQ deduplicates repeating jobs,
    so calling this on every startup is safe.

    In production: the worker process runs separately. This function only
    enqueues the schedule definition — it does not start the worker.
    """
    queue = Queue(QUEUE_NAME, {"connection": {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}})

    await queue.add(
        JOB_NAME,
        {
            "batch_size": 100,
            # month is set dynamically at execution time by the worker
        },
        {
            "repeat": {"cron": CRON_EXPRESSION},
            "attempts": 1,          # Don't retry monthly summary — next month will run
            "removeOnComplete": False,
            "removeOnFail": False,
        },
    )

    logger.info("Registered scheduled job: %s cron=%s", JOB_NAME, CRON_EXPRESSION)
    await queue.close()


def create_worker() -> Worker:
    """
    Create and return a BullMQ Worker for the scheduled queue.

    Call this from the worker process (python -m modules.jobs.worker),
    NOT from the API process.
    """
    return Worker(
        QUEUE_NAME,
        process_monthly_savings_summary,
        {"connection": {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}},
    )
