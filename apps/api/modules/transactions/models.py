import uuid
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference          = Column(String(50), unique=True, nullable=False)   # TXN-20260221-00001
    debit_account_id   = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    credit_account_id  = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    amount             = Column(BigInteger, nullable=False)   # BIGINT smallest XAF unit. NEVER FLOAT.
    currency           = Column(String(3), nullable=False, default="XAF")
    transaction_type   = Column(SAEnum("deposit", "withdrawal", "transfer", "fee", "interest", "penalty", name="txn_type_enum"), nullable=False)
    channel            = Column(SAEnum("mtn_momo", "orange_money", "visa", "mastercard", "internal", name="channel_enum"), nullable=False)
    status             = Column(SAEnum("pending", "processing", "success", "failed", "reversed", name="txn_status_enum"), nullable=False, default="pending")
    external_reference = Column(String(255))   # Reference ID from payment provider
    metadata_          = Column("metadata", JSONB)   # Provider response — audit only
    initiated_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    idempotency_key    = Column(String(255), unique=True, nullable=False)
    created_at         = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at       = Column(DateTime(timezone=True))
