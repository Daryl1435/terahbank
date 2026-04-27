# DB queries for auth module — raw SQLAlchemy async sessions only.
# No business logic here. Called by AuthService only.

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User


class AuthRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone_number: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create(
        self,
        full_name: str,
        phone_number: str,
        email: str,
        password_hash: str,
        city: str | None,
        address: str | None,
        preferred_language: str,
    ) -> User:
        user = User(
            full_name=full_name,
            phone_number=phone_number,
            email=email,
            password_hash=password_hash,
            city=city,
            address=address,
            preferred_language=preferred_language,
        )
        self.db.add(user)
        await self.db.flush()  # populate user.id without committing
        return user

    async def update_fields(self, user: User, **fields) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        self.db.add(user)
        await self.db.flush()
        return user
