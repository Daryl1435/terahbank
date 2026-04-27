"""
MTN MoMo payment BullMQ jobs.

Queue: queue:momo

Jobs:
  process_momo_payment  — attempts=1, timeout=130s
    Calls MTN requesttopay → updates txn to "processing" → stores external_reference.
    Enqueues momo_timeout_check (delayed 125s) as fallback if no webhook arrives.

  momo_timeout_check    — attempts=1, delay=125s
    Polls MTN for final status. No-op if webhook already resolved the txn.
    On SUCCESSFUL: credits account, marks txn success.
    On FAILED/PENDING: marks txn failed, stubs FR-040 notification.

CRITICAL:
  - attempts=1 on ALL payment jobs — NEVER auto-retry (double-charge risk).
  - Always check txn.status before mutating — webhook may have already resolved it.
  - Run workers as a separate ECS task, NOT inside the API process.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from bullmq import Queue, Worker

from core.config import settings
from core.mtn_momo import MTNMoMoClient

logger = logging.getLogger("terahbank.jobs.momo")

QUEUE_NAME = "queue:momo"
_CONN = {"connection": {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}}

# 125s: 120s MTN SLA + 5s padding before the timeout job polls
_TIMEOUT_DELAY_MS: int = 125_000


# ── Worker: process_momo_payment ──────────────────────────────────────────────

async def process_momo_payment(job, token: str) -> None:  # type: ignore[no-untyped-def]
    """
    BullMQ worker — initiated by TransactionService.deposit().

    job.data keys:
      txn_id       (str UUID)
      phone_e164   (E.164, e.g. "+237600000001")
      amount_units (int, smallest XAF unit)
      reference    (str, TXN-YYYYMMDD-XXXX)
    """
    txn_id: str = job.data["txn_id"]
    phone_e164: str = job.data["phone_e164"]
    amount_units: int = int(job.data["amount_units"])
    reference: str = job.data["reference"]

    logger.info("MoMo payment job started: txn_id=%s ref=%s", txn_id, reference)

    from core.database import AsyncSessionLocal
    from core.audit import write_audit_log
    from modules.transactions.repository import TransactionRepository

    async with AsyncSessionLocal() as db:
        repo = TransactionRepository(db)
        txn = await repo.get_by_id_unchecked(UUID(txn_id))

        if txn is None:
            logger.error("MoMo job: transaction not found txn_id=%s", txn_id)
            return

        if txn.status != "pending":
            logger.warning(
                "MoMo job: txn not pending, skipping txn_id=%s status=%s",
                txn_id, txn.status,
            )
            return

        # Mark as processing — MTN call is imminent
        await repo.update(txn, status="processing")
        await db.commit()

    # Call MTN API (outside the DB session to avoid long-held connections)
    client = MTNMoMoClient()
    x_reference_id: str | None = None

    async with AsyncSessionLocal() as db:
        repo = TransactionRepository(db)
        txn = await repo.get_by_id_unchecked(UUID(txn_id))

        try:
            x_reference_id = await client.request_to_pay(
                amount_units=amount_units,
                phone_e164=phone_e164,
                our_reference=reference,
            )
        except Exception as exc:
            logger.error(
                "MoMo job: requesttopay failed txn_id=%s error=%s", txn_id, exc
            )
            # Immediately fail — no retry (double-charge risk)
            now = datetime.now(tz=timezone.utc)
            await repo.update(txn, status="failed", completed_at=now)
            await write_audit_log(
                db,
                actor_id=txn.initiated_by,
                action="DEPOSIT_FAILED",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={"reason": str(exc), "channel": "mtn_momo"},
            )
            await db.commit()
            # TODO Milestone 6.2: enqueue push/SMS notification (FR-040)
            return

        # Store MTN's X-Reference-Id for webhook reconciliation
        await repo.update(txn, external_reference=x_reference_id)
        await db.commit()

    logger.info(
        "MoMo job: requesttopay accepted txn_id=%s x_ref=%s", txn_id, x_reference_id
    )

    # Enqueue fallback timeout check — fires if webhook doesn't arrive within 125s
    await _enqueue_timeout_check(txn_id=txn_id, x_reference_id=x_reference_id)


# ── Worker: momo_timeout_check ────────────────────────────────────────────────

async def process_momo_timeout_check(job, token: str) -> None:  # type: ignore[no-untyped-def]
    """
    BullMQ worker — delayed 125s after process_momo_payment.
    Polls MTN for final status only if webhook hasn't already resolved the txn.

    job.data keys:
      txn_id         (str UUID)
      x_reference_id (str UUID — MTN X-Reference-Id)
    """
    txn_id: str = job.data["txn_id"]
    x_reference_id: str = job.data["x_reference_id"]

    logger.info("MoMo timeout check: txn_id=%s x_ref=%s", txn_id, x_reference_id)

    from core.database import AsyncSessionLocal
    from core.audit import write_audit_log
    from modules.accounts.service import AccountService
    from modules.transactions.repository import TransactionRepository

    async with AsyncSessionLocal() as db:
        repo = TransactionRepository(db)
        txn = await repo.get_by_id_unchecked(UUID(txn_id))

        if txn is None:
            logger.error("MoMo timeout: txn not found txn_id=%s", txn_id)
            return

        # Webhook already resolved — nothing to do
        if txn.status in ("success", "failed", "reversed"):
            logger.info(
                "MoMo timeout: txn already resolved txn_id=%s status=%s",
                txn_id, txn.status,
            )
            return

        # Poll MTN for final answer
        client = MTNMoMoClient()
        mtn_status = await client.get_payment_status(x_reference_id)
        now = datetime.now(tz=timezone.utc)

        if mtn_status == "SUCCESSFUL":
            acct_service = AccountService(db)
            await acct_service.apply_balance_delta(txn.credit_account_id, txn.amount)
            await repo.update(txn, status="success", completed_at=now)
            await write_audit_log(
                db,
                actor_id=txn.initiated_by,
                action="DEPOSIT_SUCCESS",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={
                    "channel": "mtn_momo",
                    "amount": txn.amount,
                    "x_reference_id": x_reference_id,
                    "resolved_by": "timeout_poll",
                },
            )
            await db.commit()
            logger.info("MoMo timeout: deposit resolved SUCCESS txn_id=%s", txn_id)

        else:
            # FAILED or still PENDING after 125s → treat as failed
            await repo.update(txn, status="failed", completed_at=now)
            await write_audit_log(
                db,
                actor_id=txn.initiated_by,
                action="DEPOSIT_FAILED",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={
                    "channel": "mtn_momo",
                    "amount": txn.amount,
                    "x_reference_id": x_reference_id,
                    "mtn_status": mtn_status,
                    "resolved_by": "timeout_poll",
                },
            )
            await db.commit()
            # TODO Milestone 6.2: enqueue push/SMS notification (FR-040)
            logger.info(
                "MoMo timeout: deposit resolved FAILED txn_id=%s mtn_status=%s",
                txn_id, mtn_status,
            )


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _enqueue_timeout_check(txn_id: str, x_reference_id: str) -> None:
    """Enqueue momo_timeout_check with 125s delay. attempts=1 — no retry."""
    queue = Queue(QUEUE_NAME, _CONN)
    await queue.add(
        "momo_timeout_check",
        {"txn_id": txn_id, "x_reference_id": x_reference_id},
        {
            "delay": _TIMEOUT_DELAY_MS,
            "attempts": 1,
            "removeOnComplete": True,
            "removeOnFail": False,
        },
    )
    await queue.close()


# ── Worker factory ────────────────────────────────────────────────────────────

async def _dispatch(job, token: str) -> None:
    """Route jobs within queue:momo to the correct processor."""
    name = job.name
    if name == "process_momo_payment":
        await process_momo_payment(job, token)
    elif name == "momo_timeout_check":
        await process_momo_timeout_check(job, token)
    else:
        logger.warning("MoMo queue: unknown job name '%s'", name)


def create_worker() -> Worker:
    """
    Create and return a BullMQ Worker for queue:momo.
    Call this from the worker process, NOT from the API process.
    """
    return Worker(QUEUE_NAME, _dispatch, _CONN)
