import uuid
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Date, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base


class Card(Base):
    __tablename__ = "cards"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id               = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    account_id            = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    card_token            = Column(String(255), nullable=False)   # Tokenized from VISA partner. NEVER raw PAN.
    last_four             = Column(String(4), nullable=False)     # Display only
    expiry_date           = Column(Date, nullable=False)
    status                = Column(SAEnum("active", "frozen", "expired", "cancelled", name="card_status_enum"), nullable=False, default="active")
    daily_limit           = Column(BigInteger)                    # BIGINT smallest XAF unit
    per_transaction_limit = Column(BigInteger)                    # BIGINT smallest XAF unit
    created_at            = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
