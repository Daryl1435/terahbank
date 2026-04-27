# KYC document upload to S3 (server-side encrypted).
# storage_key stored in DB — never expose raw S3 key to clients.
# Presigned URLs generated on-demand and cached (presigned:{doc_id}, 5-min TTL).
# Admin review queue: updates kyc_status on users table + writes audit log.

import logging
import uuid
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit_log
from core.s3 import upload_kyc_document as s3_client  # aliased for test mocking
from core.schemas import TerahResponse

from .repository import KYCRepository
from .schemas import KYCDocumentData, KYCStatusResponseData, KYCUploadResponseData

logger = logging.getLogger("terahbank.kyc")

# ─── Constants ────────────────────────────────────────────────────────────────

_ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/pdf": ".pdf",
}


class KYCService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._repo = KYCRepository(db)

    # ── Upload document ───────────────────────────────────────────────────────

    async def upload_document(
        self, user, file: UploadFile, document_type: str
    ) -> TerahResponse:
        """
        Accept a multipart KYC document upload, store it in S3 (AES256 SSE),
        and create a KYCDocument record in the database.

        Validation:
        - Allowed MIME types: image/jpeg, image/png, application/pdf
        - Max size: configured via KYC_MAX_FILE_SIZE_MB (default 10 MB)
        - document_type: national_id | passport | residence_permit
        """
        from core.config import settings

        # Validate content type
        content_type = file.content_type or ""
        if content_type not in _ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INVALID_FILE_TYPE",
                    "message": "Only JPEG, PNG, and PDF files are accepted.",
                },
            )

        # Validate document type
        if document_type not in ("national_id", "passport", "residence_permit"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INVALID_DOCUMENT_TYPE",
                    "message": "document_type must be one of: national_id, passport, residence_permit",
                },
            )

        # Read and validate file size
        max_bytes = settings.KYC_MAX_FILE_SIZE_MB * 1024 * 1024
        data = await file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "code": "FILE_TOO_LARGE",
                    "message": f"File exceeds {settings.KYC_MAX_FILE_SIZE_MB} MB limit.",
                },
            )

        # Build S3 key: kyc/{user_id}/{doc_type}/{uuid}.{ext}
        ext = _ALLOWED_CONTENT_TYPES[content_type]
        s3_key = f"kyc/{user.id}/{document_type}/{uuid.uuid4()}{ext}"

        # Upload to S3 (encrypted)
        await s3_client(key=s3_key, data=data, content_type=content_type)

        # Persist document record
        doc = await self._repo.create_document(
            user_id=user.id,
            document_type=document_type,
            storage_key=s3_key,
        )

        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="KYC_DOCUMENT_UPLOADED",
            entity_type="kyc_document",
            entity_id=doc.id,
            metadata={"document_type": document_type},
        )

        logger.info("KYC document uploaded: user=%s doc=%s", user.id, doc.id)

        return TerahResponse(
            success=True,
            data=KYCUploadResponseData(document_id=str(doc.id)).model_dump(),
        )

    # ── KYC Status ────────────────────────────────────────────────────────────

    async def get_kyc_status(self, user) -> TerahResponse:
        """Return the user's KYC status and all submitted documents."""
        documents = await self._repo.get_all_for_user(user.id)
        return TerahResponse(
            success=True,
            data=KYCStatusResponseData(
                kyc_status=user.kyc_status,
                documents=[
                    KYCDocumentData(
                        document_id=str(d.id),
                        document_type=d.document_type,
                        status=d.status,
                        uploaded_at=d.uploaded_at,
                        rejection_reason=d.rejection_reason,
                    )
                    for d in documents
                ],
            ).model_dump(mode="json"),
        )

    # ── Stubs (implemented in later milestones) ───────────────────────────────

    async def get_profile(self, user_id: UUID) -> TerahResponse:
        raise NotImplementedError

    async def update_profile(self, user_id: UUID) -> TerahResponse:
        raise NotImplementedError

    async def get_activity_log(self, user_id: UUID) -> TerahResponse:
        raise NotImplementedError

    async def export_user_data(self, user_id: UUID) -> TerahResponse:
        raise NotImplementedError
