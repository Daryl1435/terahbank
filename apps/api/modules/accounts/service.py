# Account CRUD, balance management, savings rules, progress tracking.
# All balance writes wrapped in PostgreSQL transactions — no partial success.
# Minimum Standard Account balance: 1,000 XAF (100_000 smallest unit).
# Minimum initial deposit Standard: 100 XAF (10_000 smallest unit).
# Minimum Term Deposit: 200,000 XAF (20_000_000 smallest unit).
# Minimum Project Account duration: 6 months.
# Interest: always use Decimal arithmetic — never float.

import calendar
import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit_log
from core.redis import balance_cache_key, get_redis_client
from core.schemas import TerahResponse
from core.system_config import get_config_decimal

from .models import Account, AutoSaveRule
from .repository import AccountRepository
from .schemas import (
    AccountData,
    AutoSaveRuleData,
    CloseAccountResponseData,
    CreateProjectAccountRequest,
    CreateStandardAccountRequest,
    CreateTermDepositRequest,
    ListAccountsResponseData,
    OpenProjectAccountResponseData,
    OpenStandardAccountResponseData,
    OpenTermDepositResponseData,
    ProjectWithdrawalPreviewData,
    TermDepositCalculatorResponseData,
    UpdateAutoSaveRuleRequest,
)

logger = logging.getLogger("terahbank.accounts")

# ─── Constants (smallest XAF unit) ───────────────────────────────────────────
MIN_INITIAL_DEPOSIT: int = 10_000        # 100 XAF — minimum to open a Standard Account
MIN_STANDARD_BALANCE: int = 100_000      # 1,000 XAF — cannot go below this on withdrawal
MIN_TERM_DEPOSIT_AMOUNT: int = 20_000_000  # 200,000 XAF — opening minimum
MIN_PROJECT_DURATION_MONTHS: int = 6
_MILESTONES: list[int] = [25, 50, 75, 100]

# system_config keys
CONFIG_KEY_PROJECT_PENALTY_RATE: str = "penalty_rate_project"
DEFAULT_PROJECT_PENALTY_RATE: Decimal = Decimal("0.0500")   # 5%

CONFIG_KEY_TERM_DEPOSIT_RATE: str = "interest_rate_term_deposit"
DEFAULT_TERM_DEPOSIT_RATE: Decimal = Decimal("0.0200")       # 2.0% p.a.

CONFIG_KEY_TERM_DEPOSIT_BREAK_RATE: str = "early_break_rate_term_deposit"
DEFAULT_TERM_DEPOSIT_BREAK_RATE: Decimal = Decimal("0.0150") # 1.5% of principal

# Redis balance cache TTL (seconds)
BALANCE_CACHE_TTL: int = 30


# ─── Pure financial calculation functions (module-level, no DB) ───────────────


def calculate_annual_interest(principal: int, rate: Decimal) -> int:
    """
    Return annual interest on `principal` at `rate`.
    Always uses integer floor division — never float arithmetic.
    Returns BIGINT (smallest XAF unit).
    """
    return int(Decimal(principal) * rate)


def calculate_early_withdrawal(balance: int, penalty_rate: Decimal) -> tuple[int, int]:
    """
    Compute early-withdrawal amounts.
    Returns (net_amount, penalty_amount) where net + penalty == balance exactly.
    penalty is floor-truncated; net takes the remainder so invariant holds.
    """
    penalty = int(Decimal(balance) * penalty_rate)
    penalty = min(penalty, balance)  # cap penalty at balance for extreme rates
    net = balance - penalty
    return net, penalty


def calculate_progress(current: int, target: int) -> int:
    """
    Return progress percentage (0–100) toward `target`.
    Uses integer arithmetic; capped at 100.
    """
    if target <= 0:
        return 100
    pct = int(Decimal(current) * 100 // Decimal(target))
    return min(pct, 100)


def get_triggered_milestones(old_pct: int, new_pct: int) -> list[int]:
    """
    Return milestone values (25, 50, 75, 100) crossed between old_pct and new_pct.
    A milestone is triggered when new_pct has just reached or passed it,
    while old_pct had not yet reached it.
    """
    return [m for m in _MILESTONES if old_pct < m <= new_pct]


def validate_withdrawal(balance: int, amount: int) -> None:
    """
    Raise HTTP 422 if the withdrawal would leave a Standard Account below MIN_STANDARD_BALANCE.
    balance and amount are in smallest XAF units.
    """
    remaining = balance - amount
    if remaining < MIN_STANDARD_BALANCE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "MIN_BALANCE_VIOLATION",
                "message": (
                    f"Withdrawal would leave {remaining} units — "
                    f"minimum maintained balance is {MIN_STANDARD_BALANCE} units (1,000 XAF)."
                ),
            },
        )


def validate_term_deposit_opening(amount: int) -> None:
    """Raise HTTP 422 if `amount` is below the Term Deposit minimum."""
    if amount < MIN_TERM_DEPOSIT_AMOUNT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "TERM_DEPOSIT_MIN_AMOUNT",
                "message": (
                    f"Term Deposit requires a minimum of {MIN_TERM_DEPOSIT_AMOUNT} units "
                    f"(200,000 XAF). Got {amount}."
                ),
            },
        )


def validate_project_target_date(target_date: date, today: date | None = None) -> None:
    """
    FR-016: Raise HTTP 422 if target_date is less than 6 months from today.
    Uses month arithmetic to avoid floating-point calendar math.
    """
    today = today or date.today()
    # Month difference: (year delta × 12) + month delta
    month_diff = (target_date.year - today.year) * 12 + (target_date.month - today.month)
    # Also require day-of-month to be ≥ today's day when months are equal at the 6-month boundary
    if month_diff < MIN_PROJECT_DURATION_MONTHS or (
        month_diff == MIN_PROJECT_DURATION_MONTHS and target_date.day < today.day
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "MIN_PROJECT_DURATION",
                "message": (
                    f"Project Account target_date must be at least "
                    f"{MIN_PROJECT_DURATION_MONTHS} months from today. "
                    f"Got {target_date} (today is {today})."
                ),
            },
        )


def calculate_project_withdrawal(
    account: Account,
    withdrawal_amount: int,
) -> tuple[int, int, bool]:
    """
    FR-018/019: Compute project account early withdrawal result.

    Returns (net_payout, penalty_amount, is_early).
    - is_early: True when today < account.target_date
    - penalty_amount: floor(withdrawal_amount × penalty_rate) if early, else 0
    - net_payout: withdrawal_amount - penalty_amount

    Penalty is applied to the withdrawal amount (not the full balance).
    The net + penalty invariant holds exactly (no rounding loss).
    Caller ensures withdrawal_amount <= account.balance.
    """
    today = date.today()
    is_early = account.target_date is not None and today < account.target_date

    if not is_early or account.penalty_rate is None:
        return withdrawal_amount, 0, is_early

    penalty_rate = Decimal(str(account.penalty_rate))
    net, penalty = calculate_early_withdrawal(withdrawal_amount, penalty_rate)
    return net, penalty, is_early


def calculate_savings_insight(
    current_month_savings: int,
    last_month_savings: int,
) -> str | None:
    """
    FR-015 [Should Have]: Return a human-readable month-over-month savings insight.
    Returns None when there is no comparison basis (last_month_savings == 0).
    Uses integer arithmetic — no float.
    """
    if last_month_savings <= 0:
        return None
    pct_change = int(
        (current_month_savings - last_month_savings) * 100 // last_month_savings
    )
    if pct_change > 0:
        return f"You saved {pct_change}% more this month"
    if pct_change < 0:
        return f"You saved {abs(pct_change)}% less this month"
    return None


def calculate_term_deposit_interest(
    principal: int, rate: Decimal, term_months: int
) -> int:
    """
    FR-024: Pro-rata annual interest for a term deposit.
    Interest = floor(principal × rate × term_months / 12).
    Always BIGINT floor — never float, never round.

    Example: 20,000,000 units × 0.02 × 12 / 12 = 400,000 units (4,000 XAF).
    Example: 20,000,000 units × 0.02 × 6  / 12 = 200,000 units (2,000 XAF).
    """
    return int(Decimal(principal) * rate * Decimal(term_months) / Decimal(12))


def calculate_term_deposit_maturity_date(open_date: date, term_months: int) -> date:
    """
    Compute maturity date by adding term_months to open_date using proper month
    arithmetic. End-of-month days are clamped to the last valid day of the target
    month (e.g. Jan 31 + 1 month = Feb 28, not Mar 2).
    """
    raw_month = open_date.month + term_months
    year = open_date.year + (raw_month - 1) // 12
    month = ((raw_month - 1) % 12) + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(open_date.day, last_day))


def calculate_days_to_maturity(maturity_date: date, today: date | None = None) -> int:
    """
    FR-027: Days remaining until maturity_date. Returns 0 if already matured.
    """
    today = today or date.today()
    return max((maturity_date - today).days, 0)


def _generate_account_number(prefix: str) -> str:
    """Generate a unique account number: {PREFIX}{12 hex chars uppercase}."""
    return f"{prefix}{uuid.uuid4().hex[:12].upper()}"


def _compute_next_execution_at(
    frequency: str,
    day_of_week: int | None,
    from_dt: datetime | None = None,
) -> datetime:
    """
    Compute the next scheduled execution datetime for an auto-save rule.

    - daily:   from_dt + 1 day (at midnight UTC of the next day)
    - weekly:  next occurrence of day_of_week (0=Mon) at midnight UTC
    - monthly: first day of next calendar month at midnight UTC
    """
    from_dt = from_dt or datetime.now(tz=timezone.utc)
    # Normalise to midnight UTC of the next eligible day
    today_midnight = from_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    if frequency == "daily":
        from datetime import timedelta
        return today_midnight + timedelta(days=1)

    if frequency == "weekly":
        from datetime import timedelta
        dow = day_of_week if day_of_week is not None else 0  # default Monday
        current_dow = from_dt.weekday()  # 0=Mon
        days_ahead = (dow - current_dow) % 7
        if days_ahead == 0:
            days_ahead = 7  # same day means next week
        return today_midnight + timedelta(days=days_ahead)

    # monthly: 1st of next month at midnight UTC
    if from_dt.month == 12:
        return today_midnight.replace(year=from_dt.year + 1, month=1, day=1)
    return today_midnight.replace(month=from_dt.month + 1, day=1)


def _build_auto_save_data(rule: AutoSaveRule) -> AutoSaveRuleData:
    return AutoSaveRuleData(
        rule_id=str(rule.id),
        account_id=str(rule.account_id),
        source_account_id=str(rule.source_account_id),
        amount=rule.amount,
        frequency=rule.frequency,
        day_of_week=rule.day_of_week,
        next_execution_at=rule.next_execution_at,
        is_active=rule.is_active,
    )


def _build_account_data(
    account: Account,
    balance: int,
    auto_save_rule: AutoSaveRule | None = None,
) -> AccountData:
    """Build the AccountData response shape from an ORM Account + resolved balance."""
    progress_pct = None
    if account.account_type == "project" and account.target_amount:
        progress_pct = calculate_progress(balance, account.target_amount)

    rule_data = _build_auto_save_data(auto_save_rule) if auto_save_rule else None

    days_to_mat = None
    if account.account_type == "term_deposit" and account.maturity_date:
        days_to_mat = calculate_days_to_maturity(account.maturity_date)

    return AccountData(
        account_id=str(account.id),
        account_number=account.account_number,
        account_type=account.account_type,
        balance=balance,
        status=account.status,
        created_at=account.created_at,
        project_name=account.project_name,
        target_amount=account.target_amount,
        target_date=account.target_date,
        progress_pct=progress_pct,
        penalty_rate=Decimal(str(account.penalty_rate)) if account.penalty_rate else None,
        auto_save_rule=rule_data,
        maturity_date=account.maturity_date,
        interest_rate=account.interest_rate,
        days_to_maturity=days_to_mat,
        savings_insight=None,  # TODO Milestone 3: populate from transaction history
    )


async def _get_cached_balance(account_id: str, db_balance: int) -> int:
    """Return balance from Redis cache (30s TTL). On miss repopulate from DB value."""
    redis = get_redis_client()
    cached = await redis.get(balance_cache_key(account_id))
    if cached is not None:
        return int(cached)
    await redis.setex(balance_cache_key(account_id), BALANCE_CACHE_TTL, db_balance)
    return db_balance


async def _set_balance_cache(account_id: str, balance: int) -> None:
    redis = get_redis_client()
    await redis.setex(balance_cache_key(account_id), BALANCE_CACHE_TTL, balance)


async def _invalidate_balance_cache(account_id: str) -> None:
    """Delete balance from Redis cache — call BEFORE any balance mutation."""
    redis = get_redis_client()
    await redis.delete(balance_cache_key(account_id))


def _dispatch_milestone_notification(
    user_id: UUID,
    account: Account,
    milestone: int,
) -> None:
    logger.info(
        "MILESTONE_%d: user=%s account=%s project=%r",
        milestone, user_id, account.id, account.project_name,
    )


def notify_project_milestones(
    user_id: UUID,
    account: Account,
    old_balance: int,
    new_balance: int,
) -> list[int]:
    """
    FR-020: Check if any milestones (25/50/75/100) were crossed by the balance change.
    Dispatches notification stubs for each triggered milestone.
    Returns the list of triggered milestone values (for testing).

    Called after apply_balance_delta() for project accounts.
    """
    if account.account_type != "project" or not account.target_amount:
        return []

    old_pct = calculate_progress(old_balance, account.target_amount)
    new_pct = calculate_progress(new_balance, account.target_amount)
    triggered = get_triggered_milestones(old_pct, new_pct)

    for m in triggered:
        _dispatch_milestone_notification(user_id, account, m)

    return triggered


# ─── Service class ────────────────────────────────────────────────────────────


class AccountService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._repo = AccountRepository(db)

    # ── FR-010, FR-011: Open Standard Account ────────────────────────────────

    async def open_standard(
        self, user, payload: CreateStandardAccountRequest
    ) -> TerahResponse:
        """
        FR-010: Open a Standard Savings Account for a KYC-approved user.
        FR-011: initial_deposit must be >= 100 XAF (MIN_INITIAL_DEPOSIT = 10,000 units).
        One Standard Account per user — returns 409 if one already exists.
        """
        existing = await self._repo.get_standard_account_by_user(user.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "ACCOUNT_ALREADY_EXISTS",
                    "message": "You already have an active Standard Savings Account.",
                },
            )

        if payload.initial_deposit < MIN_INITIAL_DEPOSIT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "BELOW_MIN_INITIAL_DEPOSIT",
                    "message": (
                        f"Minimum initial deposit is {MIN_INITIAL_DEPOSIT} units "
                        f"(100 XAF). Got {payload.initial_deposit}."
                    ),
                },
            )

        account = Account(
            user_id=user.id,
            account_type="standard",
            account_number=_generate_account_number("STD"),
            balance=payload.initial_deposit,
            status="active",
        )
        account = await self._repo.create(account)
        await _set_balance_cache(str(account.id), account.balance)

        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="ACCOUNT_OPENED",
            entity_type="account",
            entity_id=account.id,
            metadata={
                "account_type": "standard",
                "initial_deposit": payload.initial_deposit,
                "account_number": account.account_number,
            },
        )

        logger.info("Standard account opened: user=%s account=%s", user.id, account.id)

        return TerahResponse(
            success=True,
            data=OpenStandardAccountResponseData(
                account_id=str(account.id),
                account_number=account.account_number,
                balance=account.balance,
                status=account.status,
            ).model_dump(),
            message="Standard Savings Account opened successfully.",
        )

    # ── FR-016, FR-022: Open Project Account (Vault) ─────────────────────────

    async def open_project(
        self, user, payload: CreateProjectAccountRequest
    ) -> TerahResponse:
        """
        FR-016: Create a Project Account with name, target_amount, and target_date.
        FR-022: Multiple active Project Accounts per user are allowed.
        FR-018: Penalty rate snapshot from system_config at creation time.

        target_date must be at least 6 months from today (validated here,
        not in Pydantic, because "today" must not be baked into validators).
        """
        # FR-016: validate minimum 6-month duration
        validate_project_target_date(payload.target_date)

        # FR-018: snapshot penalty rate from system_config at creation time
        penalty_rate = await get_config_decimal(
            self.db,
            CONFIG_KEY_PROJECT_PENALTY_RATE,
            default=DEFAULT_PROJECT_PENALTY_RATE,
        )

        account = Account(
            user_id=user.id,
            account_type="project",
            account_number=_generate_account_number("PRJ"),
            balance=0,  # starts at zero — funded via deposits
            status="active",
            project_name=payload.project_name,
            target_amount=payload.target_amount,
            target_date=payload.target_date,
            penalty_rate=penalty_rate,
        )
        account = await self._repo.create(account)
        await _set_balance_cache(str(account.id), 0)

        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="ACCOUNT_OPENED",
            entity_type="account",
            entity_id=account.id,
            metadata={
                "account_type": "project",
                "project_name": payload.project_name,
                "target_amount": payload.target_amount,
                "target_date": payload.target_date.isoformat(),
                "penalty_rate": str(penalty_rate),
                "account_number": account.account_number,
            },
        )

        logger.info(
            "Project account opened: user=%s account=%s project=%r target=%d",
            user.id, account.id, payload.project_name, payload.target_amount,
        )

        return TerahResponse(
            success=True,
            data=OpenProjectAccountResponseData(
                account_id=str(account.id),
                account_number=account.account_number,
                project_name=account.project_name,
                target_amount=account.target_amount,
                target_date=account.target_date,
                balance=account.balance,
                penalty_rate=penalty_rate,
                status=account.status,
            ).model_dump(mode="json"),
            message="Project Account created successfully.",
        )

    # ── FR-021: Configure auto-save rule on a project account ────────────────

    async def update_project_auto_save(
        self, account_id: str, user_id: UUID, payload: UpdateAutoSaveRuleRequest
    ) -> TerahResponse:
        """
        FR-021 [Should Have]: Set or update the recurring auto-save rule for a project account.

        The source account (Standard Account) is determined by looking up the user's
        Standard Account — users have one Standard Account (FR-010).
        auto_save_executor BullMQ job runs hourly and executes due rules.
        """
        try:
            acct_uuid = UUID(account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ACCOUNT_ID", "message": "Invalid account ID format."},
            )

        account = await self._repo.get_user_account(acct_uuid, user_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ACCOUNT_NOT_FOUND", "message": "Project account not found."},
            )
        if account.account_type != "project":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "NOT_PROJECT_ACCOUNT", "message": "Auto-save rules can only be set on Project Accounts."},
            )

        # Source: the user's Standard Account
        source = await self._repo.get_standard_account_by_user(user_id)
        if source is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "NO_SOURCE_ACCOUNT",
                    "message": "You need a Standard Savings Account to use auto-save.",
                },
            )

        if payload.frequency == "weekly" and payload.day_of_week is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "DAY_OF_WEEK_REQUIRED",
                    "message": "day_of_week is required when frequency is 'weekly'.",
                },
            )

        next_execution_at = _compute_next_execution_at(
            payload.frequency, payload.day_of_week
        )

        rule = await self._repo.upsert_auto_save_rule(
            account_id=account.id,
            source_account_id=source.id,
            amount=payload.amount,
            frequency=payload.frequency,
            day_of_week=payload.day_of_week,
            next_execution_at=next_execution_at,
            is_active=payload.is_active,
        )

        await write_audit_log(
            self.db,
            actor_id=user_id,
            action="AUTO_SAVE_RULE_UPDATED",
            entity_type="account",
            entity_id=account.id,
            metadata={
                "amount": payload.amount,
                "frequency": payload.frequency,
                "is_active": payload.is_active,
            },
        )

        return TerahResponse(
            success=True,
            data=_build_auto_save_data(rule).model_dump(mode="json"),
            message="Auto-save rule updated.",
        )

    # ── FR-013: List accounts ─────────────────────────────────────────────────

    async def list_accounts(self, user_id: UUID) -> TerahResponse:
        """
        Return all active accounts for user_id.
        Balances served from Redis cache (30s TTL) with DB fallback.
        """
        accounts = await self._repo.list_by_user(user_id)

        account_data: list[AccountData] = []
        total_balance: int = 0

        for acct in accounts:
            balance = await _get_cached_balance(str(acct.id), acct.balance)
            total_balance += balance
            rule = None
            if acct.account_type == "project":
                rule = await self._repo.get_auto_save_rule(acct.id)
            account_data.append(_build_account_data(acct, balance, rule))

        return TerahResponse(
            success=True,
            data=ListAccountsResponseData(
                accounts=account_data,
                total_balance=total_balance,
            ).model_dump(mode="json"),
        )

    # ── FR-013: Get single account ────────────────────────────────────────────

    async def get_account(self, account_id: str, user_id: UUID) -> TerahResponse:
        """Return detailed view of a single account (must be owned by user_id)."""
        try:
            acct_uuid = UUID(account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ACCOUNT_ID", "message": "Invalid account ID format."},
            )

        account = await self._repo.get_user_account(acct_uuid, user_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ACCOUNT_NOT_FOUND", "message": "Account not found."},
            )

        balance = await _get_cached_balance(str(account.id), account.balance)
        rule = None
        if account.account_type == "project":
            rule = await self._repo.get_auto_save_rule(account.id)

        return TerahResponse(
            success=True,
            data=_build_account_data(account, balance, rule).model_dump(mode="json"),
        )

    # ── FR-017/018/019: Project withdrawal preview ────────────────────────────

    async def preview_project_withdrawal(
        self, account_id: str, user_id: UUID, withdrawal_amount: int
    ) -> TerahResponse:
        """
        FR-017/018/019: Show the user a breakdown of a project withdrawal before confirmation.
        Returns net_payout, penalty_amount, is_early, and progress impact.
        Called from the withdrawal UI — no funds moved here.
        """
        try:
            acct_uuid = UUID(account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ACCOUNT_ID", "message": "Invalid account ID format."},
            )

        account = await self._repo.get_user_account(acct_uuid, user_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ACCOUNT_NOT_FOUND", "message": "Account not found."},
            )
        if account.account_type != "project":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "NOT_PROJECT_ACCOUNT", "message": "Account is not a Project Account."},
            )
        if withdrawal_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "INVALID_AMOUNT", "message": "withdrawal_amount must be greater than zero."},
            )
        if withdrawal_amount > account.balance:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INSUFFICIENT_BALANCE",
                    "message": f"Insufficient balance. Available: {account.balance} units.",
                },
            )

        net, penalty, is_early = calculate_project_withdrawal(account, withdrawal_amount)
        penalty_rate = Decimal(str(account.penalty_rate)) if account.penalty_rate else Decimal("0")

        return TerahResponse(
            success=True,
            data=ProjectWithdrawalPreviewData(
                withdrawal_amount=withdrawal_amount,
                is_early=is_early,
                penalty_amount=penalty,
                net_payout=net,
                penalty_rate=penalty_rate,
            ).model_dump(mode="json"),
        )

    # ── Balance mutation (called by TransactionService, Milestone 3) ──────────

    async def apply_balance_delta(self, account_id: UUID, delta: int) -> Account:
        """
        Apply a signed delta to an account balance atomically.
        Positive = credit (deposit). Negative = debit (withdrawal).
        Caller must be inside a DB transaction — no partial success ever.
        Invalidates Redis cache before the write.
        """
        account = await self._repo.get_by_id(account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ACCOUNT_NOT_FOUND", "message": "Account not found."},
            )

        new_balance = account.balance + delta
        if new_balance < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INSUFFICIENT_BALANCE",
                    "message": f"Insufficient balance. Available: {account.balance} units.",
                },
            )

        if account.account_type == "standard" and new_balance < MIN_STANDARD_BALANCE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "MIN_BALANCE_VIOLATION",
                    "message": (
                        f"Withdrawal would leave {new_balance} units — "
                        f"minimum maintained balance is {MIN_STANDARD_BALANCE} units (1,000 XAF)."
                    ),
                },
            )

        # Invalidate cache BEFORE write — prevents stale reads if flush fails
        await _invalidate_balance_cache(str(account.id))
        account = await self._repo.update(account, balance=new_balance)
        await _set_balance_cache(str(account.id), new_balance)

        return account

    # ── FR-023: Open Term Deposit ─────────────────────────────────────────────

    async def open_term_deposit(
        self, user, payload: CreateTermDepositRequest
    ) -> TerahResponse:
        """
        FR-023: Open a Term Deposit account.
        - Minimum 200,000 XAF (20,000,000 units).
        - Interest rate (FR-024) and early-break rate (FR-026) snapshotted from
          system_config at creation time.
        - Balance = principal for the full term; interest is paid at maturity only.
        - maturity_date computed with proper month arithmetic (end-of-month clamped).
        """
        validate_term_deposit_opening(payload.amount)

        interest_rate = await get_config_decimal(
            self.db, CONFIG_KEY_TERM_DEPOSIT_RATE, default=DEFAULT_TERM_DEPOSIT_RATE
        )
        break_rate = await get_config_decimal(
            self.db, CONFIG_KEY_TERM_DEPOSIT_BREAK_RATE, default=DEFAULT_TERM_DEPOSIT_BREAK_RATE
        )

        today = date.today()
        maturity_date = calculate_term_deposit_maturity_date(today, payload.duration_months)
        projected_interest = calculate_term_deposit_interest(
            payload.amount, interest_rate, payload.duration_months
        )
        days_remaining = calculate_days_to_maturity(maturity_date, today)

        account = Account(
            user_id=user.id,
            account_type="term_deposit",
            account_number=_generate_account_number("TDG"),
            balance=payload.amount,   # balance = principal; interest paid at maturity
            status="active",
            interest_rate=interest_rate,
            penalty_rate=break_rate,  # reuses penalty_rate column for early-break rate
            maturity_date=maturity_date,
        )
        account = await self._repo.create(account)
        await _set_balance_cache(str(account.id), account.balance)

        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="ACCOUNT_OPENED",
            entity_type="account",
            entity_id=account.id,
            metadata={
                "account_type": "term_deposit",
                "principal": payload.amount,
                "duration_months": payload.duration_months,
                "interest_rate": str(interest_rate),
                "early_break_rate": str(break_rate),
                "maturity_date": maturity_date.isoformat(),
                "projected_interest": projected_interest,
                "account_number": account.account_number,
            },
        )

        logger.info(
            "Term deposit opened: user=%s account=%s principal=%d maturity=%s",
            user.id, account.id, payload.amount, maturity_date,
        )

        return TerahResponse(
            success=True,
            data=OpenTermDepositResponseData(
                account_id=str(account.id),
                account_number=account.account_number,
                principal=payload.amount,
                interest_rate=interest_rate,
                early_break_rate=break_rate,
                projected_interest=projected_interest,
                total_at_maturity=payload.amount + projected_interest,
                maturity_date=maturity_date,
                duration_months=payload.duration_months,
                days_to_maturity=days_remaining,
                status=account.status,
            ).model_dump(mode="json"),
            message="Term Deposit opened successfully.",
        )

    # ── FR-025: Term Deposit interest calculator ──────────────────────────────

    async def get_term_deposit_calculator(
        self, amount: int, duration_months: int
    ) -> TerahResponse:
        """
        FR-025: Pre-confirmation interest projection.
        No account is created — purely calculates expected returns.
        Reads current rates from system_config (same defaults as open_term_deposit).
        """
        if amount < MIN_TERM_DEPOSIT_AMOUNT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "TERM_DEPOSIT_MIN_AMOUNT",
                    "message": (
                        f"Minimum is {MIN_TERM_DEPOSIT_AMOUNT} units (200,000 XAF). "
                        f"Got {amount}."
                    ),
                },
            )
        if duration_months < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INVALID_DURATION",
                    "message": "duration_months must be at least 1.",
                },
            )

        interest_rate = await get_config_decimal(
            self.db, CONFIG_KEY_TERM_DEPOSIT_RATE, default=DEFAULT_TERM_DEPOSIT_RATE
        )
        break_rate = await get_config_decimal(
            self.db, CONFIG_KEY_TERM_DEPOSIT_BREAK_RATE, default=DEFAULT_TERM_DEPOSIT_BREAK_RATE
        )

        projected_interest = calculate_term_deposit_interest(amount, interest_rate, duration_months)
        early_break_penalty, _ = divmod(  # reuse formula: penalty = floor(amount × break_rate)
            int(Decimal(amount) * break_rate), 1
        )
        # Simpler: floor already from int()
        early_break_penalty = int(Decimal(amount) * break_rate)
        maturity_date = calculate_term_deposit_maturity_date(date.today(), duration_months)

        return TerahResponse(
            success=True,
            data=TermDepositCalculatorResponseData(
                amount=amount,
                duration_months=duration_months,
                interest_rate=interest_rate,
                projected_interest=projected_interest,
                total_at_maturity=amount + projected_interest,
                early_break_penalty=early_break_penalty,
                net_if_broken_early=amount - early_break_penalty,
                maturity_date=maturity_date,
            ).model_dump(mode="json"),
        )

    # ── Milestone 2.3: Close account ──────────────────────────────────────────

    async def close_account(self, account_id: str, user_id: UUID) -> TerahResponse:
        """
        Close an account (any type). Requires:
        - Account owned by user_id
        - Balance must be exactly 0 (user must withdraw all funds first)

        For term deposits before maturity: the early-break withdrawal must be
        processed (via TransactionService, Milestone 3) before closing.
        """
        try:
            acct_uuid = UUID(account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ACCOUNT_ID", "message": "Invalid account ID format."},
            )

        account = await self._repo.get_user_account(acct_uuid, user_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ACCOUNT_NOT_FOUND", "message": "Account not found."},
            )

        # Read balance from cache (authoritative for real-time balance)
        balance = await _get_cached_balance(str(account.id), account.balance)
        if balance != 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "ACCOUNT_NOT_EMPTY",
                    "message": (
                        f"Account balance must be 0 before closing. "
                        f"Current balance: {balance} units. "
                        f"Please withdraw all funds first."
                    ),
                },
            )

        await _invalidate_balance_cache(str(account.id))
        account = await self._repo.update(account, status="closed")

        await write_audit_log(
            self.db,
            actor_id=user_id,
            action="ACCOUNT_CLOSED",
            entity_type="account",
            entity_id=account.id,
            metadata={"account_type": account.account_type, "account_number": account.account_number},
        )

        logger.info("Account closed: user=%s account=%s type=%s", user_id, account.id, account.account_type)

        return TerahResponse(
            success=True,
            data=CloseAccountResponseData(
                account_id=str(account.id),
                account_number=account.account_number,
                account_type=account.account_type,
                status=account.status,
            ).model_dump(),
            message="Account closed successfully.",
        )
