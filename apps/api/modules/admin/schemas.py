from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr


# ─── Request schemas ──────────────────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    email: str
    password: str


class UpdateUserStatusRequest(BaseModel):
    status: Literal["active", "suspended", "closed"]


class KYCDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    rejection_reason: str | None = None


class UpdateConfigRequest(BaseModel):
    key: str
    value: str


# ─── Admin user ───────────────────────────────────────────────────────────────

class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


# ─── User management ──────────────────────────────────────────────────────────

class AdminUserItem(BaseModel):
    """Single user row in the admin user list."""
    user_id: str
    full_name: str
    email: str
    phone_number: str
    kyc_status: str
    account_status: str
    preferred_language: str
    created_at: datetime


class AdminUserDetail(AdminUserItem):
    """Extended user detail including accounts summary."""
    accounts: list[dict]   # [{account_id, account_type, account_number, balance, status}]


class AdminUserListResponseData(BaseModel):
    users: list[AdminUserItem]
    total: int
    offset: int
    limit: int


# ─── KYC queue ────────────────────────────────────────────────────────────────

class KYCQueueItem(BaseModel):
    document_id: str
    user_id: str
    full_name: str
    email: str
    phone_number: str
    document_type: str
    uploaded_at: datetime


class KYCQueueResponseData(BaseModel):
    items: list[KYCQueueItem]
    total: int
    offset: int
    limit: int


class KYCDecisionResponseData(BaseModel):
    user_id: str
    kyc_status: str
    document_id: str


# ─── Transaction monitoring ───────────────────────────────────────────────────

class AdminTransactionItem(BaseModel):
    transaction_id: str
    reference: str
    user_id: str           # initiated_by
    transaction_type: str
    channel: str
    amount: int
    currency: str
    status: str
    debit_account_id: str | None
    credit_account_id: str | None
    external_reference: str | None
    created_at: datetime
    completed_at: datetime | None


class AdminTransactionListResponseData(BaseModel):
    transactions: list[AdminTransactionItem]
    total: int
    offset: int
    limit: int


# ─── System config ────────────────────────────────────────────────────────────

class ConfigItem(BaseModel):
    key: str
    value: str
    updated_at: datetime


class ConfigListResponseData(BaseModel):
    config: list[ConfigItem]


# ─── Reports ─────────────────────────────────────────────────────────────────

class ReportResponseData(BaseModel):
    """Metadata returned alongside the CSV download."""
    report_type: str
    row_count: int
    generated_at: datetime


# ─── Fraud alerts ────────────────────────────────────────────────────────────

class FraudAlertItem(BaseModel):
    alert_id: str
    rule: str           # LARGE_TRANSACTION | VELOCITY_BREACH | NEW_DEVICE_LARGE_WITHDRAWAL | NEW_ACCOUNT_RECIPIENT
    actor_id: str
    entity_type: str
    entity_id: str | None
    metadata: dict
    created_at: datetime


class FraudAlertListResponseData(BaseModel):
    alerts: list[FraudAlertItem]
    total: int
    offset: int
    limit: int
