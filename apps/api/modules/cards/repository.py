# DB queries for cards module — SQLAlchemy async sessions only.
# Raw PAN/CVV never stored. Only card_token + last_four + expiry_date.

from datetime import date
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Card


class CardRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, card_id: UUID, user_id: UUID) -> Card | None:
        result = await self.db.execute(
            select(Card).where(Card.id == card_id, Card.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, card_token: str) -> Card | None:
        """Lookup by card_token — used by webhook handler to match incoming notifications."""
        result = await self.db.execute(
            select(Card).where(Card.card_token == card_token)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> list[Card]:
        result = await self.db.execute(
            select(Card)
            .where(Card.user_id == user_id)
            .order_by(Card.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_active_by_user(self, user_id: UUID) -> int:
        """Count non-cancelled cards for limit enforcement (FR-033)."""
        result = await self.db.execute(
            select(func.count()).select_from(Card).where(
                Card.user_id == user_id,
                Card.status != "cancelled",
            )
        )
        return result.scalar_one()

    async def create(self, card: Card) -> Card:
        self.db.add(card)
        await self.db.flush()
        await self.db.refresh(card)
        return card

    async def update(self, card: Card, **kwargs) -> Card:
        for k, v in kwargs.items():
            setattr(card, k, v)
        await self.db.flush()
        await self.db.refresh(card)
        return card
