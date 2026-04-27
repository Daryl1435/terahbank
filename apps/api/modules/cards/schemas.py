from datetime import date, datetime
from pydantic import BaseModel


class IssueCardRequest(BaseModel):
    account_id: str   # Must be a Standard Account


class UpdateLimitsRequest(BaseModel):
    daily_limit: int | None = None             # BIGINT smallest XAF unit
    per_transaction_limit: int | None = None   # BIGINT smallest XAF unit


# ─── Response payloads ────────────────────────────────────────────────────────

class CardData(BaseModel):
    """Single virtual card record."""
    card_id: str
    account_id: str
    last_four: str
    expiry_date: str           # YYYY-MM-DD
    status: str                # active | frozen | expired | cancelled
    daily_limit: int | None
    per_transaction_limit: int | None
    created_at: datetime


class IssueCardResponse(BaseModel):
    """Returned after successful card issuance."""
    card_id: str
    account_id: str
    last_four: str
    expiry_date: str
    status: str
    created_at: datetime


class CardListResponse(BaseModel):
    cards: list[CardData]
    total: int


class CardDepositSessionData(BaseModel):
    """
    Returned after POST /transactions/deposit with channel=visa or mastercard.
    Client opens payment_url in a WebView — user enters card details on
    the PCI-certified partner hosted page.
    """
    transaction_id: str
    reference: str
    amount: int
    account_id: str
    channel: str
    status: str            # always "pending"
    payment_url: str       # Hosted payment page — open in WebView
    created_at: datetime
