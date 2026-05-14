import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DeviceToken, Notification, NotificationPreference


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Notifications ─────────────────────────────────────────────────────────

    async def create(
        self,
        user_id: uuid.UUID,
        type: str,
        title: str,
        body: str,
        metadata: dict | None = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            metadata_=metadata or {},
        )
        self.db.add(notif)
        await self.db.flush()
        return notif

    async def list_for_user(self, user_id: uuid.UUID, limit: int = 50) -> list[Notification]:
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def unread_count(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        return result.scalar_one()

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(read_at=datetime.now(timezone.utc))
        )
        return result.rowcount > 0

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=datetime.now(timezone.utc))
        )

    # ── Preferences ───────────────────────────────────────────────────────────

    async def get_preferences(self, user_id: uuid.UUID) -> NotificationPreference:
        result = await self.db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        prefs = result.scalar_one_or_none()
        if prefs is None:
            prefs = NotificationPreference(user_id=user_id)
            self.db.add(prefs)
            await self.db.flush()
        return prefs

    async def update_preferences(self, user_id: uuid.UUID, updates: dict) -> NotificationPreference:
        prefs = await self.get_preferences(user_id)
        for field, value in updates.items():
            if hasattr(prefs, field):
                setattr(prefs, field, value)
        await self.db.flush()
        return prefs

    # ── Device tokens ─────────────────────────────────────────────────────────

    async def upsert_device_token(
        self, user_id: uuid.UUID, token: str, platform: str = "android"
    ) -> DeviceToken:
        result = await self.db.execute(
            select(DeviceToken).where(DeviceToken.token == token)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.user_id = user_id
            existing.platform = platform
            await self.db.flush()
            return existing
        dt = DeviceToken(user_id=user_id, token=token, platform=platform)
        self.db.add(dt)
        await self.db.flush()
        return dt

    async def get_tokens_for_user(self, user_id: uuid.UUID) -> list[str]:
        result = await self.db.execute(
            select(DeviceToken.token).where(DeviceToken.user_id == user_id)
        )
        return list(result.scalars().all())

    async def delete_token(self, token: str) -> None:
        result = await self.db.execute(
            select(DeviceToken).where(DeviceToken.token == token)
        )
        dt = result.scalar_one_or_none()
        if dt:
            await self.db.delete(dt)
