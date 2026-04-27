import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from core.database import Base


class AdminUser(Base):
    """
    FR-056: Separate admin user table — never mixed with regular users.
    Roles: super_admin (full access), operations_staff (read + user/KYC actions),
           read_only_analyst (GET only).
    TOTP secret stored for Milestone 5.2 MFA — NULL until TOTP is enrolled.
    Password: bcrypt cost=12 — same policy as regular users.
    """
    __tablename__ = "admin_users"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String(255), unique=True, nullable=False)
    full_name     = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)   # bcrypt cost=12. NEVER plaintext.
    role          = Column(
        SAEnum("super_admin", "operations_staff", "read_only_analyst", name="admin_role_enum"),
        nullable=False,
    )
    totp_secret   = Column(String(64), nullable=True)     # Base32 TOTP secret — Milestone 5.2
    is_active     = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at    = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    # IMMUTABLE — no UPDATE or DELETE on this table. Ever.
    # API service account has no UPDATE/DELETE privileges on this table.

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id    = Column(UUID(as_uuid=True), nullable=False)
    actor_type  = Column(String(20), nullable=False)    # user | admin | system
    action      = Column(String(100), nullable=False)   # LOGIN_SUCCESS, KYC_APPROVED, TRANSFER_INITIATED, etc.
    entity_type = Column(String(50))                    # account | transaction | user
    entity_id   = Column(UUID(as_uuid=True))
    ip_address  = Column(INET)
    user_agent  = Column(Text)
    metadata_   = Column("metadata", JSONB)             # before/after state — redacted of sensitive fields
    created_at  = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class SystemConfig(Base):
    __tablename__ = "system_config"

    key        = Column(String(100), primary_key=True)   # penalty_rate_project, term_deposit_interest_rate, etc.
    value      = Column(Text, nullable=False)
    updated_by = Column(UUID(as_uuid=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
