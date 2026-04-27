from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator


# ── Request schemas ───────────────────────────────────────────────────────────

class CreateStandardAccountRequest(BaseModel):
    initial_deposit: int  # BIGINT — smallest XAF unit. Min 10_000 (100 XAF).

    @field_validator("initial_deposit")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("initial_deposit must be greater than zero")
        return v


class CreateProjectAccountRequest(BaseModel):
    project_name: str
    target_amount: int    # BIGINT — smallest XAF unit

    # target_date is validated for min 6 months in the service layer
    # (requires knowing "today" which should not be baked into Pydantic validators)
    target_date: date

    @field_validator("project_name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("project_name must not be blank")
        return v.strip()

    @field_validator("target_amount")
    @classmethod
    def amount_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Target amount must be greater than zero")
        return v


class UpdateAutoSaveRuleRequest(BaseModel):
    """PATCH /accounts/project/:id — configure or update the auto-save rule."""
    amount: int                           # BIGINT — XAF units. Must be > 0.
    frequency: Literal["daily", "weekly", "monthly"]
    day_of_week: int | None = None        # 0=Monday … 6=Sunday; required when frequency='weekly'
    is_active: bool = True

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Auto-save amount must be greater than zero")
        return v


class CreateTermDepositRequest(BaseModel):
    amount: int           # BIGINT — min 20_000_000 (200,000 XAF)
    duration_months: int  # Fixed term duration in months (min 1)

    @field_validator("amount")
    @classmethod
    def min_term_deposit(cls, v: int) -> int:
        if v < 20_000_000:
            raise ValueError("Minimum term deposit is 200,000 XAF")
        return v

    @field_validator("duration_months")
    @classmethod
    def duration_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("duration_months must be at least 1")
        return v


# ── Response schemas ──────────────────────────────────────────────────────────

class AutoSaveRuleData(BaseModel):
    rule_id: str
    account_id: str
    source_account_id: str
    amount: int                       # BIGINT
    frequency: str                    # daily | weekly | monthly
    day_of_week: int | None
    next_execution_at: datetime
    is_active: bool


class AccountData(BaseModel):
    """Shared shape for all account types returned by list and get endpoints."""
    account_id: str
    account_number: str
    account_type: str          # standard | project | term_deposit
    balance: int               # BIGINT — smallest XAF unit, NEVER FLOAT
    status: str                # active | closed | locked
    created_at: datetime

    # Project account fields
    project_name: str | None = None
    target_amount: int | None = None
    target_date: date | None = None
    progress_pct: int | None = None    # 0–100, calculated from balance / target_amount
    penalty_rate: Decimal | None = None
    auto_save_rule: AutoSaveRuleData | None = None

    # Term deposit fields
    maturity_date: date | None = None
    interest_rate: Decimal | None = None  # Decimal, never float
    days_to_maturity: int | None = None   # FR-027: countdown timer; None for non-term-deposit

    # Optional dashboard insight (FR-015)
    savings_insight: str | None = None


class OpenProjectAccountResponseData(BaseModel):
    account_id: str
    account_number: str
    project_name: str
    target_amount: int
    target_date: date
    balance: int
    penalty_rate: Decimal
    status: str


class OpenStandardAccountResponseData(BaseModel):
    account_id: str
    account_number: str
    balance: int               # equals initial_deposit
    status: str


class ListAccountsResponseData(BaseModel):
    accounts: list[AccountData]
    total_balance: int         # Aggregate of all active account balances — BIGINT


class ProjectWithdrawalPreviewData(BaseModel):
    """
    Preview of an early withdrawal calculation — returned before user confirms.
    FR-018/019: shows gross amount, penalty, and net payout.
    """
    withdrawal_amount: int     # BIGINT — what the user requested
    is_early: bool             # True if target_date has not yet been reached
    penalty_amount: int        # BIGINT — 0 if not early
    net_payout: int            # BIGINT — withdrawal_amount - penalty_amount
    penalty_rate: Decimal      # Rate applied (0 if not early)


class OpenTermDepositResponseData(BaseModel):
    """Response data after successfully opening a Term Deposit account."""
    account_id: str
    account_number: str
    principal: int             # BIGINT — the deposited amount
    interest_rate: Decimal     # Annual rate snapshotted at creation (e.g. 0.0200)
    early_break_rate: Decimal  # Penalty rate snapshotted at creation (e.g. 0.0150)
    projected_interest: int    # BIGINT — expected interest if held to maturity
    total_at_maturity: int     # BIGINT — principal + projected_interest
    maturity_date: date        # Computed: open_date + duration_months
    duration_months: int
    days_to_maturity: int      # FR-027
    status: str


class TermDepositCalculatorResponseData(BaseModel):
    """
    FR-025: Pre-confirmation interest projection.
    Returned before the user commits to opening a term deposit.
    """
    amount: int                # BIGINT — principal being evaluated
    duration_months: int
    interest_rate: Decimal     # Current annual rate from system_config
    projected_interest: int    # BIGINT — floor(principal × rate × months / 12)
    total_at_maturity: int     # BIGINT — amount + projected_interest
    early_break_penalty: int   # BIGINT — floor(principal × early_break_rate)
    net_if_broken_early: int   # BIGINT — amount - early_break_penalty
    maturity_date: date        # Simulated maturity date from today + duration_months


class CloseAccountResponseData(BaseModel):
    """Response data after successfully closing an account."""
    account_id: str
    account_number: str
    account_type: str
    status: str                # Will be "closed"
