# DB queries for accounts module — SQLAlchemy async sessions only.
# No business logic here. Called by AccountService only.

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Account, AutoSaveRule


class AccountRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, account_id: UUID) -> Account | None:
        """Fetch account by PK regardless of owner — used internally."""
        result = await self.db.execute(
            select(Account).where(Account.id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_user_account(self, account_id: UUID, user_id: UUID) -> Account | None:
        """Fetch an active account owned by user_id. Returns None if not found or closed."""
        result = await self.db.execute(
            select(Account).where(
                Account.id == account_id,
                Account.user_id == user_id,
                Account.status != "closed",
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> list[Account]:
        """Return all non-closed accounts for a user, oldest first."""
        result = await self.db.execute(
            select(Account)
            .where(Account.user_id == user_id, Account.status != "closed")
            .order_by(Account.created_at)
        )
        return list(result.scalars().all())

    async def get_standard_account_by_user(self, user_id: UUID) -> Account | None:
        """Return the user's existing Standard Account (or None)."""
        result = await self.db.execute(
            select(Account).where(
                Account.user_id == user_id,
                Account.account_type == "standard",
                Account.status != "closed",
            )
        )
        return result.scalar_one_or_none()

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create(self, account: Account) -> Account:
        self.db.add(account)
        await self.db.flush()   # assigns PK, stays in transaction — caller commits
        return account

    async def update(self, account: Account, **fields) -> Account:
        """Apply field updates to account in place and flush."""
        for key, value in fields.items():
            setattr(account, key, value)
        self.db.add(account)
        await self.db.flush()
        return account

    # ── Auto-save rules (FR-021) ──────────────────────────────────────────────

    async def get_auto_save_rule(self, account_id: UUID) -> AutoSaveRule | None:
        """Return the auto-save rule for a project account, or None."""
        result = await self.db.execute(
            select(AutoSaveRule).where(AutoSaveRule.account_id == account_id)
        )
        return result.scalar_one_or_none()

    async def upsert_auto_save_rule(
        self,
        account_id: UUID,
        source_account_id: UUID,
        amount: int,
        frequency: str,
        day_of_week: int | None,
        next_execution_at: datetime,
        is_active: bool,
    ) -> AutoSaveRule:
        """Create or update the auto-save rule for a project account."""
        existing = await self.get_auto_save_rule(account_id)
        if existing:
            existing.source_account_id = source_account_id
            existing.amount = amount
            existing.frequency = frequency
            existing.day_of_week = day_of_week
            existing.next_execution_at = next_execution_at
            existing.is_active = is_active
            existing.updated_at = datetime.utcnow()
            self.db.add(existing)
            await self.db.flush()
            return existing

        rule = AutoSaveRule(
            account_id=account_id,
            source_account_id=source_account_id,
            amount=amount,
            frequency=frequency,
            day_of_week=day_of_week,
            next_execution_at=next_execution_at,
            is_active=is_active,
        )
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def list_due_auto_save_rules(self, as_of: datetime) -> list[AutoSaveRule]:
        """Return all active auto-save rules due for execution."""
        result = await self.db.execute(
            select(AutoSaveRule).where(
                AutoSaveRule.is_active.is_(True),
                AutoSaveRule.next_execution_at <= as_of,
            )
        )
        return list(result.scalars().all())

    async def update_auto_save_rule(self, rule: AutoSaveRule, **fields) -> AutoSaveRule:
        for key, value in fields.items():
            setattr(rule, key, value)
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def get_by_account_number(self, account_number: str) -> Account | None:
        """Fetch account by account_number regardless of owner or status."""
        result = await self.db.execute(
            select(Account).where(Account.account_number == account_number)
        )
        return result.scalar_one_or_none()

    # ── Term deposit maturity queries (FR-028) ────────────────────────────────

    async def list_term_deposits_maturing_on(self, check_dates: list[date]) -> list[Account]:
        """
        Return all active term deposit accounts whose maturity_date is in check_dates.
        Used by the maturity notifier job to find accounts due for 14d/7d/1d alerts.
        """
        result = await self.db.execute(
            select(Account).where(
                Account.account_type == "term_deposit",
                Account.status == "active",
                Account.maturity_date.in_(check_dates),
            )
        )
        return list(result.scalars().all())
