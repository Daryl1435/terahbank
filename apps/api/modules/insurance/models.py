import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Column, Date, DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    partner_id     = Column(String(100), nullable=False)
    policy_type    = Column(SAEnum("health", "device", "micro", name="policy_type_enum"), nullable=False)
    product_name   = Column(String(255), nullable=False, server_default="")  # denormalized for display
    policy_number  = Column(String(255), nullable=False)
    status         = Column(
        SAEnum("active", "expired", "cancelled", name="policy_status_enum"),
        nullable=False,
        default="active",
    )
    start_date      = Column(Date, nullable=False)
    expiry_date     = Column(Date, nullable=False, index=True)  # indexed for renewal queries
    commission_amount = Column(BigInteger, nullable=False, default=0)  # XAF earned by TerahBank
    created_at      = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
