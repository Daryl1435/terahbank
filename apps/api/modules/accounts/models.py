import uuid
from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime,
    Enum as SAEnum, ForeignKey, Integer, Numeric, String,
)
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    account_type   = Column(SAEnum("standard", "project", "term_deposit", name="acct_type_enum"), nullable=False)
    account_number = Column(String(20), unique=True, nullable=False)
    balance        = Column(BigInteger, nullable=False, default=0)  # BIGINT smallest XAF unit. NEVER FLOAT.
    status         = Column(SAEnum("active", "closed", "locked", name="acct_stat_enum"), nullable=False, default="active")
    project_name   = Column(String(255))
    target_amount  = Column(BigInteger)        # Project accounts only. BIGINT.
    target_date    = Column(Date)              # Project accounts only
    penalty_rate   = Column(Numeric(5, 4))     # Early withdrawal penalty rate (snapshot from system_config at creation)
    interest_rate  = Column(Numeric(5, 4))     # Term deposits only
    maturity_date  = Column(Date)              # Term deposits only
    created_at     = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class AutoSaveRule(Base):
    """
    FR-021 [Should Have]: Automatic recurring transfer from a Standard Account
    into a Project Account Vault on a user-configured schedule.

    The auto_save_executor BullMQ job runs hourly and processes all rules
    where next_execution_at <= now() and is_active=True.
    """
    __tablename__ = "auto_save_rules"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id         = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    source_account_id  = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    amount             = Column(BigInteger, nullable=False)   # BIGINT — XAF units. NEVER FLOAT.
    frequency          = Column(
        SAEnum("daily", "weekly", "monthly", name="auto_save_freq_enum"),
        nullable=False,
    )
    day_of_week        = Column(Integer)         # 0=Monday … 6=Sunday; used when frequency='weekly'
    next_execution_at  = Column(DateTime(timezone=True), nullable=False)
    is_active          = Column(Boolean, nullable=False, default=True)
    created_at         = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at         = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
