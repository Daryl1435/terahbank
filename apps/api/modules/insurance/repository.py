from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import InsurancePolicy


class InsuranceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_policies_for_user(self, user_id: UUID) -> list[InsurancePolicy]:
        result = await self.db.execute(
            select(InsurancePolicy)
            .where(InsurancePolicy.user_id == user_id)
            .order_by(InsurancePolicy.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_policy(self, policy_id: UUID, user_id: UUID) -> InsurancePolicy | None:
        result = await self.db.execute(
            select(InsurancePolicy).where(
                InsurancePolicy.id == policy_id,
                InsurancePolicy.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_policy_by_id(self, policy_id: UUID) -> InsurancePolicy | None:
        result = await self.db.execute(
            select(InsurancePolicy).where(InsurancePolicy.id == policy_id)
        )
        return result.scalar_one_or_none()

    async def create_policy(self, **kwargs) -> InsurancePolicy:
        policy = InsurancePolicy(**kwargs)
        self.db.add(policy)
        await self.db.flush()
        return policy

    async def update_policy(self, policy: InsurancePolicy, **kwargs) -> InsurancePolicy:
        for key, value in kwargs.items():
            setattr(policy, key, value)
        self.db.add(policy)
        await self.db.flush()
        return policy

    async def list_expiring_policies(self, check_dates: list[date]) -> list[InsurancePolicy]:
        """Return active policies whose expiry_date is in the given check_dates list."""
        result = await self.db.execute(
            select(InsurancePolicy).where(
                InsurancePolicy.status == "active",
                InsurancePolicy.expiry_date.in_(check_dates),
            )
        )
        return list(result.scalars().all())

    async def list_all_policies(
        self,
        offset: int = 0,
        limit: int = 10_000,
    ) -> tuple[list[InsurancePolicy], int]:
        """Admin: all policies for commission reporting."""
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
