from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Literal


class DepositRequest(BaseModel):
    account_id: str
    amount: int   # BIGINT — smallest XAF unit
    channel: Literal["mtn_momo", "orange_money", "visa", "mastercard"]

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v


class WithdrawRequest(BaseModel):
    account_id: str
    amount: int
    channel: Literal["mtn_momo", "orange_money"]
    destination_phone: str   # E.164 — mobile wallet to receive funds
    pin_token: str           # Single-use token from POST /auth/verify-pin

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v


class TransferRequest(BaseModel):
    """
    FR-034: from_account_id → to_identifier (own account by UUID/account_number)
    FR-035: from_account_id → to_identifier (other user by phone or account ID/number)
    FR-036: pin_token required — obtained from POST /auth/verify-pin (valid 60 s, single-use)
    """
    from_account_id: str
    to_identifier: str   # phone (+237...) | account_id (UUID) | account_number (STD/PRJ/TDG...)
    amount: int          # BIGINT smallest XAF unit
    pin_token: str       # short-lived token from POST /auth/verify-pin

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v


# ─── Response payloads ────────────────────────────────────────────────────────

class TransactionData(BaseModel):
    """Single transaction record — used in list and detail responses."""
    transaction_id: str
    reference: str
    transaction_type: str
    channel: str
    amount: int
    currency: str
    status: str
    debit_account_id: str | None
    credit_account_id: str | None
    initiated_by: str
    created_at: datetime
    completed_at: datetime | None


class TransferResponseData(BaseModel):
    """Returned after a successful internal transfer."""
    transaction_id: str
    reference: str
    amount: int
    from_account_id: str
    to_account_id: str
    status: str
    created_at: datetime


class DepositResponseData(BaseModel):
    """Returned immediately after a deposit is queued (202 Accepted)."""
    transaction_id: str
    reference: str
    amount: int
    account_id: str
    channel: str
    status: str      # always "pending" at this point
    created_at: datetime


class WithdrawResponseData(BaseModel):
    """Returned immediately after a withdrawal is queued (202 Accepted)."""
    transaction_id: str
    reference: str
    amount: int
    account_id: str
    channel: str
    destination_phone: str
    status: str      # always "pending" at this point
    created_at: datetime


class TransactionStatusData(BaseModel):
    """FR-041: Real-time status for a single transaction."""
    transaction_id: str
    reference: str
    status: str
    channel: str
    external_reference: str | None
    created_at: datetime
    completed_at: datetime | None


class ListTransactionsResponseData(BaseModel):
    transactions: list[TransactionData]
    total: int
    limit: int
    offset: int
