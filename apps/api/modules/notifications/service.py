# Dispatches push (FCM), email (SendGrid), SMS notifications.
# All sends go through BullMQ queue:notifications.
# Retry policy: attempts=3, exponential backoff — safe to retry (non-financial).
# Select SendGrid template based on user.preferred_language (fr/en).

from sqlalchemy.ext.asyncio import AsyncSession


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_preferences(self, user_id: str):
        raise NotImplementedError

    async def update_preferences(self, payload, user_id: str):
        raise NotImplementedError

    async def list_notifications(self, user_id: str):
        raise NotImplementedError

    async def mark_read(self, notification_id: str, user_id: str):
        raise NotImplementedError
