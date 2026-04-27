# DB queries for transactions module — SQLAlchemy async sessions only.
# No business logic here. Called by TransactionService only.

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Transaction


class TransactionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create(self, txn: Transaction) -> Transaction:
        self.db.add(txn)
        await self.db.flush()   # assigns PK; caller commits
        return txn

    async def update(self, txn: Transaction, **fields) -> Transaction:
        for key, value in fields.items():
            setattr(txn, key, value)
        self.db.add(txn)
        await self.db.flush()
        return txn

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, txn_id: UUID, user_id: UUID) -> Transaction | None:
        """Fetch a transaction visible to user_id (must be the initiator or owner of either account)."""
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.id == txn_id,
                Transaction.initiated_by == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Transaction | None:
        result = await self.db.execute(
            select(Transaction).where(Transaction.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def get_by_external_reference(self, external_reference: str) -> Transaction | None:
        """Fetch transaction by MTN X-Reference-Id UUID (for webhook reconciliation)."""
        result = await self.db.execute(
            select(Transaction).where(Transaction.external_reference == external_reference)
        )
        return result.scalar_one_or_none()

    async def get_by_id_unchecked(self, txn_id: UUID) -> Transaction | None:
        """No ownership check — for BullMQ workers and webhook handlers only."""
        result = await self.db.execute(
            select(Transaction).where(Transaction.id == txn_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: UUID,
        account_id: UUID | None = None,
        transaction_type: str | None = None,
        txn_status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """
        FR-037: Return paginated, filtered transactions for user_id.
        Searchable by account_id (debit or credit side), type, status, and date range.
        Returns (rows, total_count).
        """
        base = select(Transaction).where(Transaction.initiated_by == user_id)

        if account_id is not None:
            base = base.where(
                or_(
                    Transaction.debit_account_id == account_id,
                    Transaction.credit_account_id == account_id,
                )
            )
        if transaction_type is not None:
            base = base.where(Transaction.transaction_type == transaction_type)
        if txn_status is not None:
            base = base.where(Transaction.status == txn_status)
        if date_from is not None:
            base = base.where(Transaction.created_at >= date_from)
        if date_to is not None:
            base = base.where(Transaction.created_at <= date_to)

        # Count total (before pagination)
        count_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        # Paginated rows — newest first
        rows_result = await self.db.execute(
            base.order_by(Transaction.created_at.desc()).limit(limit).offset(offset)
        )
        rows = list(rows_result.scalars().all())

        return rows, total
