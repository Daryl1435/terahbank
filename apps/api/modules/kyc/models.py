import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base


class KYCDocument(Base):
    __tablename__ = "kyc_documents"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    document_type    = Column(SAEnum("national_id", "passport", "residence_permit", name="doc_type_enum"), nullable=False)
    storage_key      = Column(String(500), nullable=False)   # Encrypted S3 object key. NEVER expose directly.
    status           = Column(SAEnum("pending", "approved", "rejected", name="kyc_doc_status_enum"), nullable=False, default="pending")
    reviewed_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text)
    reviewed_at      = Column(DateTime(timezone=True))
    uploaded_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
