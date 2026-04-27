from datetime import datetime
from typing import Literal

from pydantic import BaseModel


# ─── Request schemas ──────────────────────────────────────────────────────────

class KYCDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    rejection_reason: str | None = None


# ─── Response data payloads ───────────────────────────────────────────────────

class KYCDocumentData(BaseModel):
    document_id: str
    document_type: str
    status: str
    uploaded_at: datetime
    rejection_reason: str | None = None

    class Config:
        from_attributes = True


class KYCUploadResponseData(BaseModel):
    document_id: str
    status: str = "pending"
    message: str = "Document uploaded. Pending admin review."


class KYCStatusResponseData(BaseModel):
    kyc_status: str
    documents: list[KYCDocumentData]
