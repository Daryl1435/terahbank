import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base


class User(Base):
    __tablename__ = "users"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name          = Column(String(255), nullable=False)        # AES-256-GCM encrypted
    phone_number       = Column(String(20), unique=True, nullable=False)   # encrypted
    email              = Column(String(255), unique=True, nullable=False)   # encrypted
    password_hash      = Column(String(255), nullable=False)        # bcrypt cost=12. NEVER plaintext.
    city               = Column(String(100))
    address            = Column(String, nullable=True)              # encrypted
    kyc_status         = Column(SAEnum("pending", "approved", "rejected", name="kyc_status_enum"), nullable=False, default="pending")
    account_status     = Column(SAEnum("active", "suspended", "closed", name="acct_status_enum"), nullable=False, default="active")
    preferred_language = Column(String(10), default="fr")
    pin_hash           = Column(String(255), nullable=True)   # bcrypt hash of 4–6 digit PIN (FR-006/036)
    created_at         = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at         = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
