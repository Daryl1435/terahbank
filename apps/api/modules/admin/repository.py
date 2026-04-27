# DB queries for admin module — SQLAlchemy async sessions only.
# Report queries MUST use read replica session (DATABASE_URL_READ) where available.

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.admin.models import AdminUser, AuditLog, SystemConfig
from modules.accounts.models import Account
from modules.auth.models import User
from modules.insurance.models import InsurancePolicy
from modules.kyc.models import KYCDocument
from modules.transactions.models import Transaction


class AdminRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Admin users ───────────────────────────────────────────────────────────

    async def get_admin_by_email(self, email: str) -> AdminUser | None:
        result = await self.db.execute(
            select(AdminUser).where(AdminUser.email == email, AdminUser.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_admin_by_id(self, admin_id: UUID) -> AdminUser | None:
        result = await self.db.execute(
            select(AdminUser).where(AdminUser.id == admin_id)
        )
        return result.scalar_one_or_none()

    async def update_admin(self, admin: AdminUser, **fields) -> AdminUser:
        for k, v in fields.items():
            setattr(admin, k, v)
        self.db.add(admin)
        await self.db.flush()
        return admin

    # ── Regular users ─────────────────────────────────────────────────────────

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list_users(
        self,
        search: str | None = None,
        kyc_status: str | None = None,
        account_status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        """
        Paginated user list with optional filters.
        search: matches full_name, email, phone_number (ILIKE).
        """
        base = select(User)

        filters = []
        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                    User.phone_number.ilike(pattern),
                )
            )
        if kyc_status:
            filters.append(User.kyc_status == kyc_status)
        if account_status:
            filters.append(User.account_status == account_status)

        if filters:
            base = base.where(and_(*filters))

        count_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            base.order_by(User.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_user_accounts(self, user_id: UUID) -> list[Account]:
        result = await self.db.execute(
            select(Account).where(Account.user_id == user_id).order_by(Account.created_at.asc())
        )
        return list(result.scalars().all())

    async def update_user(self, user: User, **fields) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        self.db.add(user)
        await self.db.flush()
        return user

    # ── KYC queue ─────────────────────────────────────────────────────────────

    async def get_kyc_queue(
        self, offset: int = 0, limit: int = 20
    ) -> tuple[list[tuple[KYCDocument, User]], int]:
        """Pending KYC documents joined with user info, oldest-first."""
        base = (
            select(KYCDocument, User)
            .join(User, KYCDocument.user_id == User.id)
            .where(KYCDocument.status == "pending")
            .order_by(KYCDocument.uploaded_at.asc())
        )
        count_result = await self.db.execute(
            select(func.count()).select_from(
                select(KYCDocument).where(KYCDocument.status == "pending").subquery()
            )
        )
        total = count_result.scalar_one()
        result = await self.db.execute(base.offset(offset).limit(limit))
        return list(result.all()), total

    async def get_latest_pending_document(self, user_id: UUID) -> KYCDocument | None:
        result = await self.db.execute(
            select(KYCDocument)
            .where(KYCDocument.user_id == user_id, KYCDocument.status == "pending")
            .order_by(KYCDocument.uploaded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_document(self, doc: KYCDocument, **fields) -> KYCDocument:
        for key, value in fields.items():
            setattr(doc, key, value)
        self.db.add(doc)
        await self.db.flush()
        return doc

    # ── Transactions ──────────────────────────────────────────────────────────

    async def list_transactions(
        self,
        user_id: UUID | None = None,
        transaction_type: str | None = None,
        channel: str | None = None,
        txn_status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Transaction], int]:
        """Full-filter paginated transaction list for admin monitoring (FR-053)."""
        base = select(Transaction)

        filters = []
        if user_id:
            filters.append(Transaction.initiated_by == user_id)
        if transaction_type:
            filters.append(Transaction.transaction_type == transaction_type)
        if channel:
            filters.append(Transaction.channel == channel)
        if txn_status:
            filters.append(Transaction.status == txn_status)
        if date_from:
            filters.append(Transaction.created_at >= date_from)
        if date_to:
            filters.append(Transaction.created_at <= date_to)

        if filters:
            base = base.where(and_(*filters))

        count_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            base.order_by(Transaction.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    # ── System config ─────────────────────────────────────────────────────────

    async def get_all_config(self) -> list[SystemConfig]:
        result = await self.db.execute(
            select(SystemConfig).order_by(SystemConfig.key.asc())
        )
        return list(result.scalars().all())

    async def get_config_by_key(self, key: str) -> SystemConfig | None:
        result = await self.db.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        return result.scalar_one_or_none()

    async def upsert_config(self, key: str, value: str, updated_by: UUID) -> SystemConfig:
        """Insert or update a config key."""
        existing = await self.get_config_by_key(key)
        if existing:
            existing.value = value
            existing.updated_by = updated_by
            existing.updated_at = datetime.utcnow()
            self.db.add(existing)
            await self.db.flush()
            return existing
        new_cfg = SystemConfig(key=key, value=value, updated_by=updated_by)
        self.db.add(new_cfg)
        await self.db.flush()
        return new_cfg

    # ── Fraud alerts ──────────────────────────────────────────────────────────

    async def get_fraud_alerts(
        self,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """Return audit log rows where action starts with FRAUD_ALERT_, newest-first."""
        base = (
            select(AuditLog)
            .where(AuditLog.action.like("FRAUD_ALERT_%"))
            .order_by(AuditLog.created_at.desc())
        )
        count_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()
        result = await self.db.execute(base.offset(offset).limit(limit))
        return list(result.scalars().all()), total

    # ── Fraud detection queries ───────────────────────────────────────────────

    async def count_recent_transactions(
        self, user_id: UUID, since: datetime
    ) -> int:
        """Count transactions by user since a given timestamp (velocity check)."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.initiated_by == user_id,
                Transaction.created_at >= since,
            )
        )
        return result.scalar_one()

    async def get_account_age_days(self, account_id: UUID) -> int | None:
        """Return age of account in days, or None if not found."""
        result = await self.db.execute(
            select(Account.created_at).where(Account.id == account_id)
        )
        created = result.scalar_one_or_none()
        if created is None:
            return None
        delta = datetime.utcnow() - created.replace(tzinfo=None)
        return delta.days

    # ── Insurance commissions ─────────────────────────────────────────────────

    async def list_insurance_policies(
        self,
        offset: int = 0,
        limit: int = 100_000,
    ) -> tuple[list[InsurancePolicy], int]:
        """Admin: all insurance policies for commission reporting."""
        total_result = await self.db.execute(
            select(func.count()).select_from(InsurancePolicy)
        )
        total = total_result.scalar_one()
        result = await self.db.execute(
            select(InsurancePolicy)
            .order_by(InsurancePolicy.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total
