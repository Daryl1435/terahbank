# Deposits, withdrawals, transfers — transaction state machine.
# MoMo flows are ASYNC: create transaction (pending) → queue BullMQ job → return 202.
# Webhook callback handler updates status → credits/debits account.
# CRITICAL: payment BullMQ jobs use attempts=1. NEVER auto-retry (double charge risk).
# All DB writes atomic (PostgreSQL transactions). No partial success ever.
# Duplicate idempotency_key → return 409 without processing.
# Audit log written before returning on every mutation.

import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit_log
from core.config import settings
from core.redis import get_redis_client, idempotency_key, pin_token_key
from core.schemas import TerahResponse

from modules.accounts.repository import AccountRepository
from modules.accounts.service import AccountService, notify_project_milestones
from modules.auth.repository import AuthRepository

from .models import Transaction
from .repository import TransactionRepository
from .schemas import (
    DepositRequest,
    DepositResponseData,
    ListTransactionsResponseData,
    TransactionData,
    TransactionStatusData,
    TransferRequest,
    TransferResponseData,
    WithdrawRequest,
    WithdrawResponseData,
)

logger = logging.getLogger("terahbank.transactions")

# Redis TTL for idempotency keys — 24 hours
_IDEMPOTENCY_TTL: int = 86_400


def _generate_reference() -> str:
    """TXN-YYYYMMDD-XXXXXXXX (8 uppercase hex chars for collision safety)."""
    date_str = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    return f"TXN-{date_str}-{uuid.uuid4().hex[:8].upper()}"


async def _enqueue_orange_payment_job(
    txn_id: str,
    phone_e164: str,
    amount_units: int,
    reference: str,
) -> None:
    """
    Enqueue a process_orange_payment BullMQ job (deposit).
    attempts=1 — NEVER auto-retry (double-charge risk).
    """
    from bullmq import Queue
    queue = Queue(
        "queue:orange",
        {"connection": {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}},
    )
    await queue.add(
        "process_orange_payment",
        {
            "txn_id": txn_id,
            "phone_e164": phone_e164,
            "amount_units": amount_units,
            "reference": reference,
            "job_type": "deposit",
        },
        {
            "attempts": 1,
            "timeout": 130_000,
            "removeOnComplete": True,
            "removeOnFail": False,
        },
    )
    await queue.close()


async def _enqueue_orange_withdrawal_job(
    txn_id: str,
    destination_phone: str,
    amount_units: int,
    reference: str,
) -> None:
    """
    Enqueue a process_orange_withdrawal BullMQ job.
    attempts=1 — NEVER auto-retry (double-charge risk). Account already debited.
    """
    from bullmq import Queue
    queue = Queue(
        "queue:orange",
        {"connection": {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}},
    )
    await queue.add(
        "process_orange_withdrawal",
        {
            "txn_id": txn_id,
            "destination_phone": destination_phone,
            "amount_units": amount_units,
            "reference": reference,
        },
        {
            "attempts": 1,
            "timeout": 130_000,
            "removeOnComplete": True,
            "removeOnFail": False,
        },
    )
    await queue.close()


async def _enqueue_momo_payment_job(
    txn_id: str,
    phone_e164: str,
    amount_units: int,
    reference: str,
) -> None:
    """
    Enqueue a process_momo_payment BullMQ job.
    attempts=1 — NEVER auto-retry payment jobs (double-charge risk).
    timeout=130_000ms — 120s MoMo SLA + 10s buffer.
    """
    from bullmq import Queue
    queue = Queue(
        "queue:momo",
        {"connection": {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}},
    )
    await queue.add(
        "process_momo_payment",
        {
            "txn_id": txn_id,
            "phone_e164": phone_e164,
            "amount_units": amount_units,
            "reference": reference,
        },
        {
            "attempts": 1,
            "timeout": 130_000,
            "removeOnComplete": True,
            "removeOnFail": False,
        },
    )
    await queue.close()


def _build_txn_data(txn: Transaction) -> TransactionData:
    return TransactionData(
        transaction_id=str(txn.id),
        reference=txn.reference,
        transaction_type=txn.transaction_type,
        channel=txn.channel,
        amount=txn.amount,
        currency=txn.currency,
        status=txn.status,
        debit_account_id=str(txn.debit_account_id) if txn.debit_account_id else None,
        credit_account_id=str(txn.credit_account_id) if txn.credit_account_id else None,
        initiated_by=str(txn.initiated_by),
        created_at=txn.created_at,
        completed_at=txn.completed_at,
    )


class TransactionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._repo = TransactionRepository(db)

    @property
    def _redis(self):
        return get_redis_client()

    # ── FR-036: PIN token validation (single-use) ─────────────────────────────

    async def _consume_pin_token(self, pin_token: str, user_id: UUID) -> None:
        """
        Validate pin_token against Redis and delete it (single-use).
        Raises 401 if token is missing, expired, or doesn't belong to user_id.
        """
        key = pin_token_key(pin_token)
        stored_user_id = await self._redis.get(key)

        if stored_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_PIN_TOKEN", "message": "PIN token is invalid or has expired. Please verify your PIN again."},
            )
        if stored_user_id != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_PIN_TOKEN", "message": "PIN token does not match the authenticated user."},
            )

        # Delete immediately — single-use
        await self._redis.delete(key)

    # ── FR-034/035: Internal transfer ─────────────────────────────────────────

    async def transfer(
        self,
        payload: TransferRequest,
        user,
        idem_key: str,
    ) -> TerahResponse:
        """
        FR-034: Transfer between own accounts (Standard → Project, etc.)
        FR-035: Transfer to another TerahBank user by phone or account ID.
        FR-036: PIN token consumed before processing.
        Idempotency: duplicate key → 409 with existing transaction ID.
        Atomic: both balance deltas in one DB transaction — no partial success.
        """
        # 1. Validate PIN token (FR-036) — consumed first so it's invalidated
        #    even if subsequent validation fails (prevents token reuse attempts)
        await self._consume_pin_token(payload.pin_token, user.id)

        # 2. Idempotency check
        existing = await self._repo.get_by_idempotency_key(idem_key)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_IDEMPOTENCY_KEY",
                    "message": "This request was already processed.",
                    "details": {"transaction_id": str(existing.id), "reference": existing.reference},
                },
            )

        # 3. Resolve from_account (must belong to user)
        acct_repo = AccountRepository(self.db)
        try:
            from_uuid = UUID(payload.from_account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ACCOUNT_ID", "message": "Invalid from_account_id format."},
            )

        from_account = await acct_repo.get_user_account(from_uuid, user.id)
        if from_account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ACCOUNT_NOT_FOUND", "message": "Source account not found or not owned by you."},
            )
        if from_account.status != "active":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "ACCOUNT_LOCKED", "message": f"Source account is {from_account.status}."},
            )

        # 4. Resolve to_account (FR-034: own, FR-035: other user)
        to_account = await self._resolve_to_account(payload.to_identifier, acct_repo)

        # 5. Block self-transfer (same account)
        if from_account.id == to_account.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "SELF_TRANSFER", "message": "Cannot transfer to the same account."},
            )

        if to_account.status != "active":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "ACCOUNT_LOCKED", "message": f"Destination account is {to_account.status}."},
            )

        # 6. Create pending transaction record
        txn = Transaction(
            reference=_generate_reference(),
            debit_account_id=from_account.id,
            credit_account_id=to_account.id,
            amount=payload.amount,
            transaction_type="transfer",
            channel="internal",
            status="pending",
            initiated_by=user.id,
            idempotency_key=idem_key,
            created_at=datetime.now(tz=timezone.utc),
        )
        txn = await self._repo.create(txn)

        # 7 & 8. Apply balance deltas atomically
        #         apply_balance_delta validates minimum balances and flushes (same transaction)
        acct_service = AccountService(self.db)

        old_to_balance = to_account.balance
        await acct_service.apply_balance_delta(from_account.id, -payload.amount)
        updated_to = await acct_service.apply_balance_delta(to_account.id, +payload.amount)

        # 9. Mark transaction success + set completed_at
        now = datetime.now(tz=timezone.utc)
        txn = await self._repo.update(txn, status="success", completed_at=now)

        # 10. Project milestone notifications (FR-020) — if credit side is a project account
        notify_project_milestones(user.id, to_account, old_to_balance, updated_to.balance)

        # 11. Audit log
        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="TRANSFER_INITIATED",
            entity_type="transaction",
            entity_id=txn.id,
            metadata={
                "amount": payload.amount,
                "from_account": str(from_account.id),
                "to_account": str(to_account.id),
                "reference": txn.reference,
                "cross_user": str(from_account.user_id) != str(to_account.user_id),
            },
        )

        # 12. Commit — all DB changes (both balance deltas + txn) in one commit
        await self.db.commit()

        # 13. Store idempotency key in Redis (24 h) — after commit so partial failures don't cache
        await self._redis.setex(
            idempotency_key(idem_key),
            _IDEMPOTENCY_TTL,
            str(txn.id),
        )

        logger.info(
            "Transfer success: ref=%s amount=%d from=%s to=%s user=%s",
            txn.reference, payload.amount, from_account.id, to_account.id, user.id,
        )

        return TerahResponse(
            success=True,
            data=TransferResponseData(
                transaction_id=str(txn.id),
                reference=txn.reference,
                amount=txn.amount,
                from_account_id=str(from_account.id),
                to_account_id=str(to_account.id),
                status=txn.status,
                created_at=txn.created_at,
            ).model_dump(mode="json"),
            message="Transfer completed successfully.",
        )

    async def _resolve_to_account(self, to_identifier: str, acct_repo):
        """
        Resolve to_identifier to an Account:
        - Starts with '+': phone number → look up user → their Standard Account
        - Valid UUID: direct account_id lookup
        - Otherwise: treat as account_number (STD/PRJ/TDG prefix)
        """
        # Phone number lookup (FR-035)
        if to_identifier.startswith("+"):
            auth_repo = AuthRepository(self.db)
            recipient = await auth_repo.get_by_phone(to_identifier)
            if recipient is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "RECIPIENT_NOT_FOUND", "message": f"No TerahBank user found with phone {to_identifier}."},
                )
            account = await acct_repo.get_standard_account_by_user(recipient.id)
            if account is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "RECIPIENT_NO_ACCOUNT", "message": "Recipient does not have an active Standard Account."},
                )
            return account

        # UUID account_id lookup
        try:
            acct_uuid = UUID(to_identifier)
            account = await acct_repo.get_by_id(acct_uuid)
            if account is None or account.status == "closed":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "ACCOUNT_NOT_FOUND", "message": "Destination account not found."},
                )
            return account
        except ValueError:
            pass  # not a UUID — fall through to account_number

        # Account number lookup (STD..., PRJ..., TDG...)
        account = await acct_repo.get_by_account_number(to_identifier)
        if account is None or account.status == "closed":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ACCOUNT_NOT_FOUND", "message": f"No account found with number {to_identifier}."},
            )
        return account

    # ── FR-037: Transaction history ───────────────────────────────────────────

    async def list_transactions(
        self,
        user_id: UUID,
        account_id: str | None = None,
        transaction_type: str | None = None,
        txn_status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> TerahResponse:
        """FR-037: Paginated, searchable transaction history."""
        acct_uuid: UUID | None = None
        if account_id is not None:
            try:
                acct_uuid = UUID(account_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "INVALID_ACCOUNT_ID", "message": "Invalid account_id filter."},
                )

        rows, total = await self._repo.list_by_user(
            user_id=user_id,
            account_id=acct_uuid,
            transaction_type=transaction_type,
            txn_status=txn_status,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

        return TerahResponse(
            success=True,
            data=ListTransactionsResponseData(
                transactions=[_build_txn_data(t) for t in rows],
                total=total,
                limit=limit,
                offset=offset,
            ).model_dump(mode="json"),
        )

    # ── Get single transaction ─────────────────────────────────────────────────

    async def get_transaction(self, transaction_id: str, user_id: UUID) -> TerahResponse:
        try:
            txn_uuid = UUID(transaction_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_TRANSACTION_ID", "message": "Invalid transaction ID format."},
            )

        txn = await self._repo.get_by_id(txn_uuid, user_id)
        if txn is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "TRANSACTION_NOT_FOUND", "message": "Transaction not found."},
            )

        return TerahResponse(success=True, data=_build_txn_data(txn).model_dump(mode="json"))

    # ── FR-038: MTN MoMo deposit ──────────────────────────────────────────────

    async def deposit(
        self,
        payload: DepositRequest,
        user,
        idem_key: str,
    ) -> TerahResponse:
        """
        FR-038: Initiate a deposit via MTN MoMo (channel=mtn_momo).
        UC-003: Async — creates pending transaction, enqueues BullMQ job, returns 202.
        CRITICAL: payment jobs use attempts=1. Never auto-retry (double-charge risk).
        """
        if payload.channel == "mtn_momo":
            if not settings.FEATURE_MTN_MOMO:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"code": "FEATURE_DISABLED", "message": "MTN MoMo deposits are currently disabled."},
                )
        elif payload.channel == "orange_money":
            if not settings.FEATURE_ORANGE_MONEY:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"code": "FEATURE_DISABLED", "message": "Orange Money deposits are currently disabled."},
                )
        elif payload.channel in ("visa", "mastercard"):
            if not settings.FEATURE_CARD_DEPOSIT:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"code": "FEATURE_DISABLED", "message": "Card deposits are currently disabled."},
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail={"code": "CHANNEL_NOT_SUPPORTED", "message": f"Channel '{payload.channel}' is not yet supported."},
            )

        # 1. Idempotency check
        existing = await self._repo.get_by_idempotency_key(idem_key)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_IDEMPOTENCY_KEY",
                    "message": "This request was already processed.",
                    "details": {"transaction_id": str(existing.id), "reference": existing.reference},
                },
            )

        # 2. Validate target account belongs to user
        acct_repo = AccountRepository(self.db)
        try:
            acct_uuid = UUID(payload.account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ACCOUNT_ID", "message": "Invalid account_id format."},
            )

        account = await acct_repo.get_user_account(acct_uuid, user.id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ACCOUNT_NOT_FOUND", "message": "Account not found or not owned by you."},
            )
        if account.status != "active":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "ACCOUNT_LOCKED", "message": f"Account is {account.status}."},
            )

        # 3. Create pending transaction (no debit_account — external payer)
        reference = _generate_reference()
        txn = Transaction(
            reference=reference,
            debit_account_id=None,
            credit_account_id=account.id,
            amount=payload.amount,
            transaction_type="deposit",
            channel=payload.channel,
            status="pending",
            initiated_by=user.id,
            idempotency_key=idem_key,
            created_at=datetime.now(tz=timezone.utc),
        )
        txn = await self._repo.create(txn)

        # 4a. Card deposit (visa / mastercard): create hosted payment session BEFORE commit.
        #     On gateway failure: HTTP 502 is raised, txn record is NOT committed (rolled back).
        payment_url: str | None = None
        if payload.channel in ("visa", "mastercard"):
            from core.visa_gateway import VisaGatewayClient
            gateway = VisaGatewayClient()
            try:
                payment_url = await gateway.create_payment_session(
                    amount_units=payload.amount,
                    our_reference=reference,
                )
            except Exception as exc:
                logger.error("VISA gateway session creation failed: user=%s error=%s", user.id, exc)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"code": "PAYMENT_SESSION_FAILED", "message": "Card payment session temporarily unavailable. Please try again."},
                )

        # 4b. Audit log before commit
        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="DEPOSIT_INITIATED",
            entity_type="transaction",
            entity_id=txn.id,
            metadata={
                "amount": payload.amount,
                "channel": payload.channel,
                "account_id": str(account.id),
                "reference": reference,
            },
        )

        # 5. Commit txn record
        await self.db.commit()

        # 6. Store idempotency key in Redis (24h) — after commit
        await self._redis.setex(
            idempotency_key(idem_key),
            _IDEMPOTENCY_TTL,
            str(txn.id),
        )

        logger.info(
            "Deposit initiated: ref=%s amount=%d channel=%s user=%s",
            reference, payload.amount, payload.channel, user.id,
        )

        # 7a. Card deposit — return payment_url for WebView; no BullMQ job needed.
        #     Partner sends webhook to /webhooks/visa-card on completion.
        if payload.channel in ("visa", "mastercard"):
            from modules.cards.schemas import CardDepositSessionData
            return TerahResponse(
                success=True,
                data=CardDepositSessionData(
                    transaction_id=str(txn.id),
                    reference=reference,
                    amount=payload.amount,
                    account_id=str(account.id),
                    channel=payload.channel,
                    status="pending",
                    payment_url=payment_url,
                    created_at=txn.created_at,
                ).model_dump(mode="json"),
                message="Card payment session created. Open the payment URL to complete your deposit.",
            )

        # 7b. MoMo/Orange — enqueue BullMQ job (attempts=1, no auto-retry)
        if payload.channel == "mtn_momo":
            await _enqueue_momo_payment_job(
                txn_id=str(txn.id),
                phone_e164=user.phone,
                amount_units=payload.amount,
                reference=reference,
            )
        else:  # orange_money
            await _enqueue_orange_payment_job(
                txn_id=str(txn.id),
                phone_e164=user.phone,
                amount_units=payload.amount,
                reference=reference,
            )

        return TerahResponse(
            success=True,
            data=DepositResponseData(
                transaction_id=str(txn.id),
                reference=reference,
                amount=payload.amount,
                account_id=str(account.id),
                channel=payload.channel,
                status="pending",
                created_at=txn.created_at,
            ).model_dump(mode="json"),
            message="Deposit initiated. You will receive a payment prompt on your phone.",
        )

    # ── FR-041: Real-time transaction status ─────────────────────────────────

    async def get_transaction_status(self, transaction_id: str, user_id: UUID) -> TerahResponse:
        """FR-041: Return current status for a pending/processing/completed transaction."""
        try:
            txn_uuid = UUID(transaction_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_TRANSACTION_ID", "message": "Invalid transaction ID format."},
            )

        txn = await self._repo.get_by_id(txn_uuid, user_id)
        if txn is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "TRANSACTION_NOT_FOUND", "message": "Transaction not found."},
            )

        return TerahResponse(
            success=True,
            data=TransactionStatusData(
                transaction_id=str(txn.id),
                reference=txn.reference,
                status=txn.status,
                channel=txn.channel,
                external_reference=txn.external_reference,
                created_at=txn.created_at,
                completed_at=txn.completed_at,
            ).model_dump(mode="json"),
        )

    # ── MTN MoMo webhook state machine ───────────────────────────────────────

    async def handle_mtn_webhook(self, x_reference_id: str, payload: dict) -> None:
        """
        Process an inbound MTN MoMo callback (signature already validated by router).

        Looks up the transaction by external_reference (our X-Reference-Id UUID).
        Duplicate callbacks are silently ignored.
        On SUCCESSFUL: credits account, marks txn success, writes audit log.
        On FAILED: marks txn failed, writes audit log, stubs FR-040 notification.
        CRITICAL: always returns without raising — caller returns HTTP 200 to MTN.
        """
        mtn_status = payload.get("status", "").upper()

        # 1. Look up transaction by the X-Reference-Id we generated
        txn = await self._repo.get_by_external_reference(x_reference_id)
        if txn is None:
            logger.warning("MTN webhook: no transaction for x_ref=%s", x_reference_id)
            return

        # 2. Duplicate callback guard — idempotent
        if txn.status in ("success", "failed", "reversed"):
            logger.info(
                "MTN webhook: duplicate callback ignored txn_id=%s status=%s",
                txn.id, txn.status,
            )
            return

        now = datetime.now(tz=timezone.utc)

        if mtn_status == "SUCCESSFUL":
            # Credit account atomically
            acct_service = AccountService(self.db)
            await acct_service.apply_balance_delta(txn.credit_account_id, txn.amount)
            await self._repo.update(txn, status="success", completed_at=now)
            await write_audit_log(
                self.db,
                actor_id=txn.initiated_by,
                action="DEPOSIT_SUCCESS",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={"channel": txn.channel, "amount": txn.amount, "x_reference_id": x_reference_id},
            )
            await self.db.commit()
            logger.info("MTN webhook: deposit success txn_id=%s amount=%d", txn.id, txn.amount)

        elif mtn_status == "FAILED":
            await self._repo.update(txn, status="failed", completed_at=now)
            await write_audit_log(
                self.db,
                actor_id=txn.initiated_by,
                action="DEPOSIT_FAILED",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={"channel": txn.channel, "amount": txn.amount, "x_reference_id": x_reference_id, "reason": payload.get("reason")},
            )
            await self.db.commit()
            # TODO Milestone 6.2: enqueue push/SMS notification to user (FR-040)
            logger.info("MTN webhook: deposit failed txn_id=%s", txn.id)

        else:
            # PENDING or unknown — no state change
            logger.info("MTN webhook: status=%s txn_id=%s — no action", mtn_status, txn.id)

    # ── FR-039: MoMo withdrawal (MTN + Orange Money) ─────────────────────────

    async def withdraw(
        self,
        payload: WithdrawRequest,
        user,
        idem_key: str,
    ) -> TerahResponse:
        """
        FR-039: Initiate a withdrawal via MTN MoMo or Orange Money.
        Async — debits account atomically, enqueues BullMQ job, returns 202.
        CRITICAL: account is debited BEFORE the BullMQ job runs.
                  If the MoMo API fails, the worker creates a compensating credit.
                  payment jobs use attempts=1. Never auto-retry (double-charge risk).
        """
        # 1. Feature flag check
        if payload.channel == "mtn_momo":
            if not settings.FEATURE_MTN_MOMO:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"code": "FEATURE_DISABLED", "message": "MTN MoMo withdrawals are currently disabled."},
                )
        elif payload.channel == "orange_money":
            if not settings.FEATURE_ORANGE_MONEY:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"code": "FEATURE_DISABLED", "message": "Orange Money withdrawals are currently disabled."},
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail={"code": "CHANNEL_NOT_SUPPORTED", "message": f"Channel '{payload.channel}' is not yet supported."},
            )

        # 2. Validate PIN token (FR-036) — consumed first
        await self._consume_pin_token(payload.pin_token, user.id)

        # 3. Idempotency check
        existing = await self._repo.get_by_idempotency_key(idem_key)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_IDEMPOTENCY_KEY",
                    "message": "This request was already processed.",
                    "details": {"transaction_id": str(existing.id), "reference": existing.reference},
                },
            )

        # 4. Validate source account belongs to user and is active
        acct_repo = AccountRepository(self.db)
        try:
            acct_uuid = UUID(payload.account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ACCOUNT_ID", "message": "Invalid account_id format."},
            )

        account = await acct_repo.get_user_account(acct_uuid, user.id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ACCOUNT_NOT_FOUND", "message": "Account not found or not owned by you."},
            )
        if account.status != "active":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "ACCOUNT_LOCKED", "message": f"Account is {account.status}."},
            )

        # 5. Create pending transaction
        reference = _generate_reference()
        txn = Transaction(
            reference=reference,
            debit_account_id=account.id,
            credit_account_id=None,  # external recipient — mobile wallet
            amount=payload.amount,
            transaction_type="withdrawal",
            channel=payload.channel,
            status="pending",
            initiated_by=user.id,
            idempotency_key=idem_key,
            created_at=datetime.now(tz=timezone.utc),
        )
        txn = await self._repo.create(txn)

        # 6. Debit account atomically BEFORE enqueueing — prevents race conditions.
        #    apply_balance_delta raises 422 if insufficient funds.
        acct_service = AccountService(self.db)
        await acct_service.apply_balance_delta(account.id, -payload.amount)

        # 7. Audit log before commit
        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="WITHDRAWAL_INITIATED",
            entity_type="transaction",
            entity_id=txn.id,
            metadata={
                "amount": payload.amount,
                "channel": payload.channel,
                "account_id": str(account.id),
                "destination_phone": payload.destination_phone,
                "reference": reference,
            },
        )

        # 8. Commit — txn record + debit in one atomic DB transaction
        await self.db.commit()

        # 9. Store idempotency key in Redis (24h)
        await self._redis.setex(
            idempotency_key(idem_key),
            _IDEMPOTENCY_TTL,
            str(txn.id),
        )

        # 10. Enqueue BullMQ job — worker calls MoMo disbursement API
        if payload.channel == "orange_money":
            await _enqueue_orange_withdrawal_job(
                txn_id=str(txn.id),
                destination_phone=payload.destination_phone,
                amount_units=payload.amount,
                reference=reference,
            )
        else:
            # MTN MoMo withdrawal uses the same queue:momo with job_type=withdrawal
            from bullmq import Queue
            queue = Queue(
                "queue:momo",
                {"connection": {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}},
            )
            await queue.add(
                "process_momo_withdrawal",
                {
                    "txn_id": str(txn.id),
                    "destination_phone": payload.destination_phone,
                    "amount_units": payload.amount,
                    "reference": reference,
                },
                {"attempts": 1, "timeout": 130_000, "removeOnComplete": True, "removeOnFail": False},
            )
            await queue.close()

        logger.info(
            "Withdrawal initiated: ref=%s amount=%d channel=%s user=%s",
            reference, payload.amount, payload.channel, user.id,
        )

        return TerahResponse(
            success=True,
            data=WithdrawResponseData(
                transaction_id=str(txn.id),
                reference=reference,
                amount=payload.amount,
                account_id=str(account.id),
                channel=payload.channel,
                destination_phone=payload.destination_phone,
                status="pending",
                created_at=txn.created_at,
            ).model_dump(mode="json"),
            message="Withdrawal initiated. Funds will be sent to your mobile wallet.",
        )

    # ── Orange Money webhook state machine ───────────────────────────────────

    async def handle_orange_webhook(self, order_id: str, payload: dict) -> None:
        """
        Process an inbound Orange Money callback (signature already validated by router).

        Looks up the transaction by external_reference (our TXN-YYYYMMDD reference).
        Duplicate callbacks are silently ignored.
        On SUCCESSFUL:
          - Deposit: credits account, marks txn success.
          - Withdrawal: marks txn success (account already debited).
        On FAILED:
          - Deposit: marks txn failed.
          - Withdrawal: compensating credit back to account, marks txn failed.
        CRITICAL: always returns without raising — caller returns HTTP 200.
        """
        raw_status = payload.get("status", "").upper()
        # Normalise to SUCCESSFUL | FAILED | PENDING
        if raw_status in ("SUCCESS",):
            orange_status = "SUCCESSFUL"
        elif raw_status in ("CANCELLED", "EXPIRED"):
            orange_status = "FAILED"
        else:
            orange_status = raw_status

        # 1. Look up transaction by order_id (our TXN reference)
        txn = await self._repo.get_by_external_reference(order_id)
        if txn is None:
            logger.warning("Orange webhook: no transaction for order_id=%s", order_id)
            return

        # 2. Duplicate callback guard
        if txn.status in ("success", "failed", "reversed"):
            logger.info(
                "Orange webhook: duplicate callback ignored txn_id=%s status=%s",
                txn.id, txn.status,
            )
            return

        now = datetime.now(tz=timezone.utc)

        if orange_status == "SUCCESSFUL":
            acct_service = AccountService(self.db)
            if txn.transaction_type == "deposit":
                # Credit account for deposits
                await acct_service.apply_balance_delta(txn.credit_account_id, txn.amount)
            # For withdrawals: account already debited — no balance change needed
            await self._repo.update(txn, status="success", completed_at=now)
            await write_audit_log(
                self.db,
                actor_id=txn.initiated_by,
                action="DEPOSIT_SUCCESS" if txn.transaction_type == "deposit" else "WITHDRAWAL_SUCCESS",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={"channel": "orange_money", "amount": txn.amount, "order_id": order_id},
            )
            await self.db.commit()
            logger.info(
                "Orange webhook: %s success txn_id=%s amount=%d",
                txn.transaction_type, txn.id, txn.amount,
            )

        elif orange_status == "FAILED":
            acct_service = AccountService(self.db)
            if txn.transaction_type == "withdrawal":
                # Compensating credit — return funds to account
                await acct_service.apply_balance_delta(txn.debit_account_id, txn.amount)
            await self._repo.update(txn, status="failed", completed_at=now)
            await write_audit_log(
                self.db,
                actor_id=txn.initiated_by,
                action="DEPOSIT_FAILED" if txn.transaction_type == "deposit" else "WITHDRAWAL_FAILED",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={
                    "channel": "orange_money",
                    "amount": txn.amount,
                    "order_id": order_id,
                    "reason": payload.get("reason"),
                },
            )
            await self.db.commit()
            # TODO Milestone 6.2: enqueue push/SMS notification (FR-040)
            logger.info("Orange webhook: %s failed txn_id=%s", txn.transaction_type, txn.id)

        else:
            # PENDING or unknown — no state change
            logger.info("Orange webhook: status=%s txn_id=%s — no action", orange_status, txn.id)
