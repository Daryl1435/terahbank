"""
Orange Money payment BullMQ jobs.

Queue: queue:orange

Jobs:
  process_orange_payment    — attempts=1, timeout=130s (deposit)
    Calls OrangeMoneyClient.pay() → updates txn to "processing" → stores external_reference.
    Enqueues orange_deposit_timeout_check (delayed 125s) as fallback if no webhook arrives.

  orange_deposit_timeout_check — attempts=1, delay=125s
    Polls Orange Money for final deposit status. No-op if webhook already resolved the txn.

  process_orange_withdrawal — attempts=1, timeout=130s
    Account already debited. Calls OrangeMoneyClient.transfer() → stores external_reference.
    Enqueues orange_withdrawal_timeout_check (delayed 125s) as fallback.
    On API failure: compensating credit back to account, marks txn failed.

  orange_withdrawal_timeout_check — attempts=1, delay=125s
    Polls Orange Money for final withdrawal status.
    On FAILED/PENDING: compensating credit, marks txn failed.

CRITICAL:
  - attempts=1 on ALL payment jobs — NEVER auto-retry (double-charge risk).
  - Withdrawals: account debited BEFORE this worker runs. Any failure triggers a compensating credit.
  - Always check txn.status before mutating — webhook may have already resolved it.
  - Run workers as a separate ECS task, NOT inside the API process.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from bullmq import Queue, Worker

from core.config import settings
from core.orange_money import OrangeMoneyClient

logger = logging.getLogger("terahbank.jobs.orange")

QUEUE_NAME = "queue:orange"
_CONN = {"connection": {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}}

_TIMEOUT_DELAY_MS: int = 125_000


# ── Worker: process_orange_payment (deposit) ──────────────────────────────────

async def process_orange_payment(job, token: str) -> None:  # type: ignore[no-untyped-def]
    """
    BullMQ worker — initiated by TransactionService.deposit() for orange_money channel.

    job.data keys:
      txn_id       (str UUID)
      phone_e164   (E.164, e.g. "+237690000001")
      amount_units (int, smallest XAF unit)
      reference    (str, TXN-YYYYMMDD-XXXX)
    """
    txn_id: str = job.data["txn_id"]
    phone_e164: str = job.data["phone_e164"]
    amount_units: int = int(job.data["amount_units"])
    reference: str = job.data["reference"]

    logger.info("Orange deposit job started: txn_id=%s ref=%s", txn_id, reference)

    from core.database import AsyncSessionLocal
    from core.audit import write_audit_log
    from modules.transactions.repository import TransactionRepository

    async with AsyncSessionLocal() as db:
        repo = TransactionRepository(db)
        txn = await repo.get_by_id_unchecked(UUID(txn_id))

        if txn is None:
            logger.error("Orange deposit job: transaction not found txn_id=%s", txn_id)
            return

        if txn.status != "pending":
            logger.warning(
                "Orange deposit job: txn not pending, skipping txn_id=%s status=%s",
                txn_id, txn.status,
            )
            return

        # Mark as processing before calling the API
        await repo.update(txn, status="processing")
        await db.commit()

    # Call Orange Money API outside the DB session
    client = OrangeMoneyClient()
    order_id: str | None = None

    async with AsyncSessionLocal() as db:
        repo = TransactionRepository(db)
        txn = await repo.get_by_id_unchecked(UUID(txn_id))

        try:
            order_id = await client.pay(
                amount_units=amount_units,
                phone_e164=phone_e164,
                our_reference=reference,
            )
        except Exception as exc:
            logger.error(
                "Orange deposit job: pay() failed txn_id=%s error=%s", txn_id, exc
            )
            now = datetime.now(tz=timezone.utc)
            await repo.update(txn, status="failed", completed_at=now)
            await write_audit_log(
                db,
                actor_id=txn.initiated_by,
                action="DEPOSIT_FAILED",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={"reason": str(exc), "channel": "orange_money"},
            )
            await db.commit()
            # TODO Milestone 6.2: enqueue push/SMS notification (FR-040)
            return

        # Store our TXN reference as external_reference for webhook reconciliation
        await repo.update(txn, external_reference=order_id)
        await db.commit()

    logger.info(
        "Orange deposit job: pay accepted txn_id=%s order_id=%s", txn_id, order_id
    )

    await _enqueue_deposit_timeout_check(txn_id=txn_id, order_id=order_id)


# ── Worker: orange_deposit_timeout_check ──────────────────────────────────────

async def process_orange_deposit_timeout_check(job, token: str) -> None:  # type: ignore[no-untyped-def]
    """
    BullMQ worker — delayed 125s after process_orange_payment.
    Polls Orange Money for final status only if webhook hasn't already resolved the txn.
    """
    txn_id: str = job.data["txn_id"]
    order_id: str = job.data["order_id"]

    logger.info("Orange deposit timeout check: txn_id=%s order_id=%s", txn_id, order_id)

    from core.database import AsyncSessionLocal
    from core.audit import write_audit_log
    from modules.accounts.service import AccountService
    from modules.transactions.repository import TransactionRepository

    async with AsyncSessionLocal() as db:
        repo = TransactionRepository(db)
        txn = await repo.get_by_id_unchecked(UUID(txn_id))

        if txn is None:
            logger.error("Orange deposit timeout: txn not found txn_id=%s", txn_id)
            return

        if txn.status in ("success", "failed", "reversed"):
            logger.info(
                "Orange deposit timeout: txn already resolved txn_id=%s status=%s",
                txn_id, txn.status,
            )
            return

        client = OrangeMoneyClient()
        orange_status = await client.get_payment_status(order_id)
        now = datetime.now(tz=timezone.utc)

        if orange_status == "SUCCESSFUL":
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
                    "channel": "orange_money",
                    "amount": txn.amount,
                    "order_id": order_id,
                    "resolved_by": "timeout_poll",
                },
            )
            await db.commit()
            logger.info("Orange deposit timeout: resolved SUCCESS txn_id=%s", txn_id)

        else:
            await repo.update(txn, status="failed", completed_at=now)
            await write_audit_log(
                db,
                actor_id=txn.initiated_by,
                action="DEPOSIT_FAILED",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={
                    "channel": "orange_money",
                    "amount": txn.amount,
                    "order_id": order_id,
                    "orange_status": orange_status,
                    "resolved_by": "timeout_poll",
                },
            )
            await db.commit()
            # TODO Milestone 6.2: enqueue push/SMS notification (FR-040)
            logger.info(
                "Orange deposit timeout: resolved FAILED txn_id=%s orange_status=%s",
                txn_id, orange_status,
            )


# ── Worker: process_orange_withdrawal ─────────────────────────────────────────

async def process_orange_withdrawal(job, token: str) -> None:  # type: ignore[no-untyped-def]
    """
    BullMQ worker — account already debited by TransactionService.withdraw().

    job.data keys:
      txn_id             (str UUID)
      destination_phone  (E.164 — recipient's wallet)
      amount_units       (int, smallest XAF unit)
      reference          (str, TXN-YYYYMMDD-XXXX)

    On API failure: compensating credit back to debit_account_id, marks txn failed.
    """
    txn_id: str = job.data["txn_id"]
    destination_phone: str = job.data["destination_phone"]
    amount_units: int = int(job.data["amount_units"])
    reference: str = job.data["reference"]

    logger.info("Orange withdrawal job started: txn_id=%s ref=%s", txn_id, reference)

    from core.database import AsyncSessionLocal
    from core.audit import write_audit_log
    from modules.accounts.service import AccountService
    from modules.transactions.repository import TransactionRepository

    async with AsyncSessionLocal() as db:
        repo = TransactionRepository(db)
        txn = await repo.get_by_id_unchecked(UUID(txn_id))

        if txn is None:
            logger.error("Orange withdrawal job: txn not found txn_id=%s", txn_id)
            return

        if txn.status != "pending":
            logger.warning(
                "Orange withdrawal job: txn not pending txn_id=%s status=%s",
                txn_id, txn.status,
            )
            return

        await repo.update(txn, status="processing")
        await db.commit()

    client = OrangeMoneyClient()
    order_id: str | None = None

    async with AsyncSessionLocal() as db:
        repo = TransactionRepository(db)
        txn = await repo.get_by_id_unchecked(UUID(txn_id))

        try:
            order_id = await client.transfer(
                amount_units=amount_units,
                destination_phone=destination_phone,
                our_reference=reference,
            )
        except Exception as exc:
            logger.error(
                "Orange withdrawal job: transfer() failed txn_id=%s error=%s", txn_id, exc
            )
            # Compensating credit — return funds to account
            now = datetime.now(tz=timezone.utc)
            acct_service = AccountService(db)
            await acct_service.apply_balance_delta(txn.debit_account_id, txn.amount)
            await repo.update(txn, status="failed", completed_at=now)
            await write_audit_log(
                db,
                actor_id=txn.initiated_by,
                action="WITHDRAWAL_FAILED",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={"reason": str(exc), "channel": "orange_money", "compensated": True},
            )
            await db.commit()
            # TODO Milestone 6.2: enqueue push/SMS notification (FR-040)
            return

        await repo.update(txn, external_reference=order_id)
        await db.commit()

    logger.info(
        "Orange withdrawal job: transfer accepted txn_id=%s order_id=%s", txn_id, order_id
    )

    await _enqueue_withdrawal_timeout_check(txn_id=txn_id, order_id=order_id)


# ── Worker: orange_withdrawal_timeout_check ───────────────────────────────────

async def process_orange_withdrawal_timeout_check(job, token: str) -> None:  # type: ignore[no-untyped-def]
    """
    BullMQ worker — delayed 125s after process_orange_withdrawal.
    Polls Orange Money for final withdrawal status.
    On FAILED/PENDING: compensating credit restores funds to account.
    """
    txn_id: str = job.data["txn_id"]
    order_id: str = job.data["order_id"]

    logger.info("Orange withdrawal timeout check: txn_id=%s order_id=%s", txn_id, order_id)

    from core.database import AsyncSessionLocal
    from core.audit import write_audit_log
    from modules.accounts.service import AccountService
    from modules.transactions.repository import TransactionRepository

    async with AsyncSessionLocal() as db:
        repo = TransactionRepository(db)
        txn = await repo.get_by_id_unchecked(UUID(txn_id))

        if txn is None:
            logger.error("Orange withdrawal timeout: txn not found txn_id=%s", txn_id)
            return

        if txn.status in ("success", "failed", "reversed"):
            logger.info(
                "Orange withdrawal timeout: already resolved txn_id=%s status=%s",
                txn_id, txn.status,
            )
            return

        client = OrangeMoneyClient()
        orange_status = await client.get_payment_status(order_id)
        now = datetime.now(tz=timezone.utc)
        acct_service = AccountService(db)

        if orange_status == "SUCCESSFUL":
            await repo.update(txn, status="success", completed_at=now)
            await write_audit_log(
                db,
                actor_id=txn.initiated_by,
                action="WITHDRAWAL_SUCCESS",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={
                    "channel": "orange_money",
                    "amount": txn.amount,
                    "order_id": order_id,
                    "resolved_by": "timeout_poll",
                },
            )
            await db.commit()
            logger.info("Orange withdrawal timeout: resolved SUCCESS txn_id=%s", txn_id)

        else:
            # FAILED or PENDING after 125s → fail, compensating credit
            await acct_service.apply_balance_delta(txn.debit_account_id, txn.amount)
            await repo.update(txn, status="failed", completed_at=now)
            await write_audit_log(
                db,
                actor_id=txn.initiated_by,
                action="WITHDRAWAL_FAILED",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={
                    "channel": "orange_money",
                    "amount": txn.amount,
                    "order_id": order_id,
                    "orange_status": orange_status,
                    "resolved_by": "timeout_poll",
                    "compensated": True,
                },
            )
            await db.commit()
            # TODO Milestone 6.2: enqueue push/SMS notification (FR-040)
            logger.info(
                "Orange withdrawal timeout: resolved FAILED txn_id=%s orange_status=%s",
                txn_id, orange_status,
            )


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _enqueue_deposit_timeout_check(txn_id: str, order_id: str) -> None:
    """Enqueue orange_deposit_timeout_check with 125s delay. attempts=1."""
    queue = Queue(QUEUE_NAME, _CONN)
    await queue.add(
        "orange_deposit_timeout_check",
        {"txn_id": txn_id, "order_id": order_id},
        {
            "delay": _TIMEOUT_DELAY_MS,
            "attempts": 1,
            "removeOnComplete": True,
            "removeOnFail": False,
        },
    )
    await queue.close()


async def _enqueue_withdrawal_timeout_check(txn_id: str, order_id: str) -> None:
    """Enqueue orange_withdrawal_timeout_check with 125s delay. attempts=1."""
    queue = Queue(QUEUE_NAME, _CONN)
    await queue.add(
        "orange_withdrawal_timeout_check",
        {"txn_id": txn_id, "order_id": order_id},
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
    """Route jobs within queue:orange to the correct processor."""
    name = job.name
    if name == "process_orange_payment":
        await process_orange_payment(job, token)
    elif name == "orange_deposit_timeout_check":
        await process_orange_deposit_timeout_check(job, token)
    elif name == "process_orange_withdrawal":
        await process_orange_withdrawal(job, token)
    elif name == "orange_withdrawal_timeout_check":
        await process_orange_withdrawal_timeout_check(job, token)
    else:
        logger.warning("Orange queue: unknown job name '%s'", name)


def create_worker() -> Worker:
    """
    Create and return a BullMQ Worker for queue:orange.
    Call this from the worker process, NOT from the API process.
    """
    return Worker(QUEUE_NAME, _dispatch, _CONN)
