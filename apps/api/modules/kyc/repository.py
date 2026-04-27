# DB queries for kyc module — SQLAlchemy async sessions only.
# No business logic. Called by KYCService only.

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import KYCDocument


class KYCRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, doc_id: UUID) -> KYCDocument | None:
        result = await self.db.execute(
            select(KYCDocument).where(KYCDocument.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_pending_by_user(self, user_id: UUID) -> KYCDocument | None:
        """Return the most recent pending document for a user, or None."""
        result = await self.db.execute(
            select(KYCDocument)
            .where(KYCDocument.user_id == user_id, KYCDocument.status == "pending")
            .order_by(KYCDocument.uploaded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_for_user(self, user_id: UUID) -> list[KYCDocument]:
        result = await self.db.execute(
            select(KYCDocument)
            .where(KYCDocument.user_id == user_id)
            .order_by(KYCDocument.uploaded_at.desc())
        )
        return list(result.scalars().all())

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create_document(
        self,
        user_id: UUID,
        document_type: str,
        storage_key: str,
    ) -> KYCDocument:
        doc = KYCDocument(
            user_id=user_id,
            document_type=document_type,
            storage_key=storage_key,
            status="pending",
        )
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def update_document(self, doc: KYCDocument, **fields) -> KYCDocument:
        for key, value in fields.items():
            setattr(doc, key, value)
        self.db.add(doc)
        await self.db.flush()
        return doc
