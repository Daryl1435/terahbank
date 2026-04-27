"""
FR-021 [Should Have]: Auto-save executor — scheduled BullMQ job.

Schedule: 0 * * * * (every hour on the hour UTC)
Queue:    queue:scheduled

Worker behavior:
  1. Query all AutoSaveRule records where is_active=True AND next_execution_at <= now()
  2. For each due rule: verify source account has sufficient balance
  3. If yes → enqueue internal transfer job → update next_execution_at
  4. If no  → log low-balance skip (send notification — TODO Milestone 6.2)

The actual fund movement is handled by the internal transfer job (Milestone 3.1).
This job only validates and queues — it never moves money directly.
"""

import logging
from datetime import datetime, timezone

from bullmq import Queue, Worker

from core.config import settings

logger = logging.getLogger("terahbank.jobs.auto_save_executor")

QUEUE_NAME = "queue:scheduled"
JOB_NAME = "auto_save_executor"
CRON_EXPRESSION = "0 * * * *"  # every hour on the hour


async def process_auto_save_executor(job, token: str) -> None:  # type: ignore[no-untyped-def]
    """
    BullMQ worker processor — called once per hour.
    Processes all auto-save rules due for execution.
    """
    now = datetime.now(tz=timezone.utc)
    logger.info("Auto-save executor started: %s", now.isoformat())

    try:
        from core.database import AsyncSessionLocal
        from modules.accounts.models import AutoSaveRule
        from modules.accounts.repository import AccountRepository
        from modules.accounts.service import _compute_next_execution_at

        async with AsyncSessionLocal() as db:
            repo = AccountRepository(db)
            due_rules = await repo.list_due_auto_save_rules(as_of=now)

            logger.info("Auto-save: found %d due rules", len(due_rules))

            for rule in due_rules:
                await _process_rule(db, repo, rule, now)

            await db.commit()

    except Exception as exc:
        logger.exception("Auto-save executor failed: %s", exc)
        raise


async def _process_rule(db, repo, rule, now: datetime) -> None:
    """Process a single due auto-save rule."""
    from modules.accounts.service import _compute_next_execution_at

    try:
        source = await repo.get_by_id(rule.source_account_id)
        target = await repo.get_by_id(rule.account_id)

        if source is None or target is None:
            logger.warning(
                "Auto-save rule %s: source or target account not found — deactivating",
                rule.id,
            )
            await repo.update_auto_save_rule(rule, is_active=False)
            return

        if source.balance < rule.amount:
            logger.info(
                "Auto-save rule %s: insufficient balance (have=%d need=%d) — skipping",
                rule.id, source.balance, rule.amount,
            )
            # TODO Milestone 6.2: enqueue send_push_notification LOW_BALANCE
            # advance next_execution_at to avoid thrashing
            next_exec = _compute_next_execution_at(rule.frequency, rule.day_of_week, now)
            await repo.update_auto_save_rule(rule, next_execution_at=next_exec)
            return

        # TODO Milestone 3.1: enqueue internal transfer job instead of moving funds directly
        # await enqueue_transfer_job({
        #     "source_account_id": str(rule.source_account_id),
        #     "credit_account_id": str(rule.account_id),
        #     "amount": rule.amount,
        #     "initiated_by": "system",
        #     "idempotency_key": f"auto_save:{rule.id}:{now.date().isoformat()}",
        # })

        logger.info(
            "Auto-save rule %s: would transfer %d units from %s → %s (stub; Milestone 3.1)",
            rule.id, rule.amount, rule.source_account_id, rule.account_id,
        )

        next_exec = _compute_next_execution_at(rule.frequency, rule.day_of_week, now)
        await repo.update_auto_save_rule(rule, next_execution_at=next_exec)

    except Exception as exc:
        logger.error("Auto-save rule %s failed: %s", rule.id, exc)
        # Do not re-raise — continue processing remaining rules


async def register_auto_save_job() -> None:
    """
    Register the auto_save_executor repeating job with BullMQ.
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
    Create and return a BullMQ Worker for the auto-save queue.
    Call from the worker process (python -m modules.jobs.worker), NOT from the API.
    """
    return Worker(
        QUEUE_NAME,
        process_auto_save_executor,
        {"connection": {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}},
    )
