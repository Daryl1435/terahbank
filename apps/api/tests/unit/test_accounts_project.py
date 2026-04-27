"""
Project Account unit tests — Milestone 2.2.

Covers:
  - Minimum 6-month duration enforcement (FR-016)
  - Multiple project accounts per user (FR-022)
  - Penalty rate snapshot from system_config (FR-018)
  - calculate_project_withdrawal: early vs on-time (FR-018/019)
  - Penalty calculation edge cases (FR-018)
  - Milestone trigger logic (FR-020)
  - Auto-save rule creation and next_execution_at computation (FR-021)
  - Project account happy path
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_user(kyc_status: str = "approved"):
    user = MagicMock()
    user.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.kyc_status = kyc_status
    return user


def _make_project_account(
    balance: int = 0,
    target_amount: int = 10_000_000,   # 100,000 XAF
    target_date: date | None = None,
    penalty_rate: Decimal = Decimal("0.05"),
    account_id: uuid.UUID | None = None,
):
    acct = MagicMock()
    acct.id = account_id or uuid.uuid4()
    acct.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    acct.account_type = "project"
    acct.account_number = "PRJ" + "A" * 12
    acct.balance = balance
    acct.status = "active"
    acct.project_name = "Maison de Yaoundé"
    acct.target_amount = target_amount
    acct.target_date = target_date or (date.today() + timedelta(days=365))
    acct.penalty_rate = penalty_rate
    acct.interest_rate = None
    acct.maturity_date = None
    acct.created_at = datetime(2026, 4, 1)
    return acct


# ── FR-016: validate_project_target_date ──────────────────────────────────────

class TestValidateProjectTargetDate:

    def _today(self):
        return date(2026, 4, 22)

    def test_exactly_6_months_passes(self):
        from modules.accounts.service import validate_project_target_date
        today = self._today()
        target = date(today.year, today.month + 6, today.day)
        validate_project_target_date(target, today=today)  # no exception

    def test_more_than_6_months_passes(self):
        from modules.accounts.service import validate_project_target_date
        today = self._today()
        target = date(today.year + 1, today.month, today.day)
        validate_project_target_date(target, today=today)  # no exception

    def test_5_months_raises(self):
        from modules.accounts.service import validate_project_target_date
        today = self._today()
        target = date(today.year, today.month + 5, today.day)
        with pytest.raises(HTTPException) as exc:
            validate_project_target_date(target, today=today)
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "MIN_PROJECT_DURATION"

    def test_6_months_minus_1_day_raises(self):
        from modules.accounts.service import validate_project_target_date
        today = self._today()
        # Exactly 6 months but one day short
        target = date(today.year, today.month + 6, today.day) - timedelta(days=1)
        with pytest.raises(HTTPException) as exc:
            validate_project_target_date(target, today=today)
        assert exc.value.status_code == 422

    def test_same_day_raises(self):
        from modules.accounts.service import validate_project_target_date
        today = self._today()
        with pytest.raises(HTTPException) as exc:
            validate_project_target_date(today, today=today)
        assert exc.value.status_code == 422

    def test_target_in_past_raises(self):
        from modules.accounts.service import validate_project_target_date
        today = self._today()
        with pytest.raises(HTTPException) as exc:
            validate_project_target_date(date(2020, 1, 1), today=today)
        assert exc.value.status_code == 422

    def test_year_boundary_crossing(self):
        """6 months from October 2026 = April 2027 — year boundary must work."""
        from modules.accounts.service import validate_project_target_date
        today = date(2026, 10, 1)
        target = date(2027, 4, 1)  # exactly 6 months
        validate_project_target_date(target, today=today)  # no exception


# ── FR-018/019: calculate_project_withdrawal ──────────────────────────────────

class TestCalculateProjectWithdrawal:

    def test_early_withdrawal_applies_penalty(self):
        """Withdrawal before target_date incurs penalty."""
        from modules.accounts.service import calculate_project_withdrawal
        acct = _make_project_account(
            balance=5_000_000,
            target_date=date.today() + timedelta(days=180),  # future
            penalty_rate=Decimal("0.05"),
        )
        net, penalty, is_early = calculate_project_withdrawal(acct, 1_000_000)
        assert is_early is True
        assert penalty == 50_000       # 5% of 1,000,000
        assert net == 950_000
        assert net + penalty == 1_000_000  # invariant

    def test_on_time_withdrawal_no_penalty(self):
        """Withdrawal on or after target_date has no penalty."""
        from modules.accounts.service import calculate_project_withdrawal
        acct = _make_project_account(
            balance=5_000_000,
            target_date=date.today() - timedelta(days=1),  # past
            penalty_rate=Decimal("0.05"),
        )
        net, penalty, is_early = calculate_project_withdrawal(acct, 1_000_000)
        assert is_early is False
        assert penalty == 0
        assert net == 1_000_000

    def test_penalty_on_target_date_itself_no_penalty(self):
        """Exactly on the target_date — not early."""
        from modules.accounts.service import calculate_project_withdrawal
        acct = _make_project_account(
            target_date=date.today(),  # today = maturity
            penalty_rate=Decimal("0.05"),
        )
        _, penalty, is_early = calculate_project_withdrawal(acct, 500_000)
        assert is_early is False
        assert penalty == 0

    def test_no_penalty_rate_stored_means_no_penalty(self):
        """Account without penalty_rate should never produce a penalty."""
        from modules.accounts.service import calculate_project_withdrawal
        acct = _make_project_account(
            target_date=date.today() + timedelta(days=90),
            penalty_rate=None,
        )
        acct.penalty_rate = None
        net, penalty, is_early = calculate_project_withdrawal(acct, 500_000)
        assert is_early is True
        assert penalty == 0
        assert net == 500_000

    def test_full_balance_withdrawal_penalty_exact(self):
        """Penalty applied to full balance — net + penalty == balance exactly."""
        from modules.accounts.service import calculate_project_withdrawal
        acct = _make_project_account(
            balance=10_000_000,
            target_date=date.today() + timedelta(days=180),
            penalty_rate=Decimal("0.05"),
        )
        net, penalty, _ = calculate_project_withdrawal(acct, 10_000_000)
        assert net + penalty == 10_000_000
        assert penalty == 500_000

    def test_penalty_floor_not_round(self):
        """Penalty is truncated (floor), never rounded up."""
        from modules.accounts.service import calculate_project_withdrawal
        # 100,001 units × 5% = 5000.05 → floor to 5000
        acct = _make_project_account(
            balance=100_001,
            target_date=date.today() + timedelta(days=180),
            penalty_rate=Decimal("0.05"),
        )
        _, penalty, _ = calculate_project_withdrawal(acct, 100_001)
        assert penalty == 5000   # floor(100001 × 0.05) = floor(5000.05)

    def test_penalty_never_exceeds_withdrawal_amount(self):
        """Safety: penalty capped at withdrawal amount for extreme rates."""
        from modules.accounts.service import calculate_project_withdrawal
        acct = _make_project_account(
            balance=1_000,
            target_date=date.today() + timedelta(days=180),
            penalty_rate=Decimal("0.99"),
        )
        net, penalty, _ = calculate_project_withdrawal(acct, 1_000)
        assert penalty <= 1_000
        assert net >= 0
        assert net + penalty == 1_000

    def test_penalty_uses_account_rate_not_current_config(self):
        """
        FR-018: penalty_rate is snapshotted at account creation.
        Even if system_config changes, the stored rate is used.
        """
        from modules.accounts.service import calculate_project_withdrawal
        # Account was created when penalty was 3%
        acct = _make_project_account(
            balance=1_000_000,
            target_date=date.today() + timedelta(days=180),
            penalty_rate=Decimal("0.03"),  # stored on account — not current config
        )
        _, penalty, _ = calculate_project_withdrawal(acct, 1_000_000)
        assert penalty == 30_000  # 3% — NOT the current system_config rate


# ── FR-020: Milestone notifications ──────────────────────────────────────────

class TestMilestoneNotifications:

    def test_no_milestones_if_not_project_account(self):
        from modules.accounts.service import notify_project_milestones
        acct = _make_project_account()
        acct.account_type = "standard"
        result = notify_project_milestones(uuid.uuid4(), acct, 0, 5_000_000)
        assert result == []

    def test_no_milestones_if_no_target(self):
        from modules.accounts.service import notify_project_milestones
        acct = _make_project_account()
        acct.target_amount = None
        result = notify_project_milestones(uuid.uuid4(), acct, 0, 5_000_000)
        assert result == []

    def test_25_percent_milestone_triggered(self):
        from modules.accounts.service import notify_project_milestones
        acct = _make_project_account(target_amount=10_000_000)
        # Balance moves from 0 → 2,500,000 (0% → 25%)
        result = notify_project_milestones(uuid.uuid4(), acct, 0, 2_500_000)
        assert 25 in result

    def test_50_percent_milestone_triggered(self):
        from modules.accounts.service import notify_project_milestones
        acct = _make_project_account(target_amount=10_000_000)
        # Balance moves from 2,500,000 → 5,000,000 (25% → 50%)
        result = notify_project_milestones(uuid.uuid4(), acct, 2_500_000, 5_000_000)
        assert 50 in result
        assert 25 not in result  # already triggered in a prior deposit

    def test_multiple_milestones_in_one_deposit(self):
        """A large deposit can cross multiple milestones at once."""
        from modules.accounts.service import notify_project_milestones
        acct = _make_project_account(target_amount=10_000_000)
        # Balance jumps from 0 → 8,000,000 (0% → 80%), crossing 25, 50, 75
        result = notify_project_milestones(uuid.uuid4(), acct, 0, 8_000_000)
        assert 25 in result
        assert 50 in result
        assert 75 in result
        assert 100 not in result

    def test_100_percent_milestone_on_full_funding(self):
        from modules.accounts.service import notify_project_milestones
        acct = _make_project_account(target_amount=10_000_000)
        result = notify_project_milestones(uuid.uuid4(), acct, 9_500_000, 10_000_000)
        assert 100 in result

    def test_no_milestone_if_below_threshold(self):
        from modules.accounts.service import notify_project_milestones
        acct = _make_project_account(target_amount=10_000_000)
        # From 0 → 2,000,000 (0% → 20%) — no milestone at 20%
        result = notify_project_milestones(uuid.uuid4(), acct, 0, 2_000_000)
        assert result == []

    def test_already_past_milestone_not_retriggered(self):
        """If old_pct is already above a milestone, that milestone is NOT re-triggered."""
        from modules.accounts.service import notify_project_milestones
        acct = _make_project_account(target_amount=10_000_000)
        # old_pct=25, new_pct=30 — no new milestone crossed
        result = notify_project_milestones(uuid.uuid4(), acct, 2_500_000, 3_000_000)
        assert result == []

    def test_overfunded_triggers_100(self):
        """Even if balance exceeds target, 100% milestone fires once."""
        from modules.accounts.service import notify_project_milestones
        acct = _make_project_account(target_amount=10_000_000)
        # old_pct=90, new_pct=100 (capped)
        result = notify_project_milestones(uuid.uuid4(), acct, 9_000_000, 11_000_000)
        assert 100 in result


# ── FR-021: _compute_next_execution_at ───────────────────────────────────────

class TestComputeNextExecutionAt:

    def _make_dt(self, y, m, d, h=12) -> datetime:
        return datetime(y, m, d, h, 0, 0, tzinfo=timezone.utc)

    def test_daily_is_next_midnight(self):
        from modules.accounts.service import _compute_next_execution_at
        from_dt = self._make_dt(2026, 4, 22, 12)  # Wednesday 12:00 UTC
        result = _compute_next_execution_at("daily", None, from_dt)
        assert result.day == 23
        assert result.hour == 0
        assert result.minute == 0

    def test_weekly_next_monday_from_wednesday(self):
        from modules.accounts.service import _compute_next_execution_at
        # Wednesday 2026-04-22 → next Monday (day_of_week=0) = 2026-04-27
        from_dt = self._make_dt(2026, 4, 22, 12)  # Wednesday
        result = _compute_next_execution_at("weekly", 0, from_dt)
        assert result.weekday() == 0  # Monday
        assert result > from_dt

    def test_weekly_same_day_schedules_next_week(self):
        from modules.accounts.service import _compute_next_execution_at
        from datetime import date
        # Wednesday noon 2026-04-22 → next Wednesday 2026-04-29 midnight (not today)
        from_dt = self._make_dt(2026, 4, 22, 12)  # Wednesday = weekday 2
        result = _compute_next_execution_at("weekly", 2, from_dt)
        assert result.weekday() == 2  # still Wednesday
        assert result.date() == date(2026, 4, 29)  # next week's Wednesday

    def test_monthly_crosses_year_boundary(self):
        from modules.accounts.service import _compute_next_execution_at
        from_dt = self._make_dt(2026, 12, 15, 10)
        result = _compute_next_execution_at("monthly", None, from_dt)
        assert result.year == 2027
        assert result.month == 1
        assert result.day == 1

    def test_monthly_is_first_of_next_month(self):
        from modules.accounts.service import _compute_next_execution_at
        from_dt = self._make_dt(2026, 4, 22, 8)
        result = _compute_next_execution_at("monthly", None, from_dt)
        assert result.year == 2026
        assert result.month == 5
        assert result.day == 1
        assert result.hour == 0


# ── FR-016/022: open_project service ─────────────────────────────────────────

@pytest.mark.asyncio
class TestOpenProjectAccount:

    def _make_service(self, repo):
        from modules.accounts.service import AccountService
        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo
        return svc

    async def test_happy_path_creates_project_account(self):
        from modules.accounts.schemas import CreateProjectAccountRequest
        from modules.accounts.service import AccountService

        user = _make_user()
        today = date.today()
        target_date = date(today.year, today.month + 7, today.day)  # 7 months out

        created = _make_project_account(target_date=target_date)

        repo = AsyncMock()
        repo.create = AsyncMock(return_value=created)

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with patch("modules.accounts.service.get_config_decimal", new=AsyncMock(return_value=Decimal("0.05"))), \
             patch("modules.accounts.service.write_audit_log", new=AsyncMock()), \
             patch("modules.accounts.service._set_balance_cache", new=AsyncMock()):
            result = await svc.open_project(
                user,
                CreateProjectAccountRequest(
                    project_name="Maison de Yaoundé",
                    target_amount=5_000_000,
                    target_date=target_date,
                ),
            )

        assert result.success is True
        assert result.data["project_name"] == "Maison de Yaoundé"
        assert result.data["status"] == "active"
        assert result.data["balance"] == 0   # starts at zero

    async def test_too_short_duration_raises_422(self):
        from modules.accounts.schemas import CreateProjectAccountRequest
        from modules.accounts.service import AccountService

        user = _make_user()
        today = date.today()
        target_date = date(today.year, today.month + 3, today.day)  # only 3 months

        repo = AsyncMock()
        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with pytest.raises(HTTPException) as exc:
            with patch("modules.accounts.service.get_config_decimal", new=AsyncMock(return_value=Decimal("0.05"))):
                await svc.open_project(
                    user,
                    CreateProjectAccountRequest(
                        project_name="Too Short",
                        target_amount=1_000_000,
                        target_date=target_date,
                    ),
                )
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "MIN_PROJECT_DURATION"

    async def test_penalty_rate_from_system_config_is_stored(self):
        """FR-018: penalty_rate from system_config is snapshotted onto the account."""
        from modules.accounts.schemas import CreateProjectAccountRequest
        from modules.accounts.service import AccountService

        user = _make_user()
        today = date.today()
        target_date = date(today.year + 1, today.month, today.day)

        created = _make_project_account(target_date=target_date)
        captured_kwargs: dict = {}

        async def mock_create(account):
            captured_kwargs.update({
                "penalty_rate": account.penalty_rate,
                "balance": account.balance,
            })
            return created

        repo = AsyncMock()
        repo.create = mock_create

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with patch("modules.accounts.service.get_config_decimal", new=AsyncMock(return_value=Decimal("0.0300"))), \
             patch("modules.accounts.service.write_audit_log", new=AsyncMock()), \
             patch("modules.accounts.service._set_balance_cache", new=AsyncMock()):
            await svc.open_project(
                user,
                CreateProjectAccountRequest(
                    project_name="Projet Test",
                    target_amount=1_000_000,
                    target_date=target_date,
                ),
            )

        assert captured_kwargs["penalty_rate"] == Decimal("0.0300")

    async def test_multiple_project_accounts_allowed(self):
        """FR-022: No one-per-user guard on Project Accounts."""
        from modules.accounts.schemas import CreateProjectAccountRequest
        from modules.accounts.service import AccountService

        user = _make_user()
        today = date.today()
        target_date = date(today.year + 1, today.month, today.day)

        # Both calls should succeed — no 409 check
        for i in range(2):
            created = _make_project_account(target_date=target_date)
            repo = AsyncMock()
            repo.create = AsyncMock(return_value=created)
            db = AsyncMock()
            svc = AccountService(db)
            svc._repo = repo

            with patch("modules.accounts.service.get_config_decimal", new=AsyncMock(return_value=Decimal("0.05"))), \
                 patch("modules.accounts.service.write_audit_log", new=AsyncMock()), \
                 patch("modules.accounts.service._set_balance_cache", new=AsyncMock()):
                result = await svc.open_project(
                    user,
                    CreateProjectAccountRequest(
                        project_name=f"Project {i}",
                        target_amount=1_000_000,
                        target_date=target_date,
                    ),
                )
            assert result.success is True  # both succeed

    async def test_audit_log_written_on_project_creation(self):
        from modules.accounts.schemas import CreateProjectAccountRequest
        from modules.accounts.service import AccountService

        user = _make_user()
        today = date.today()
        target_date = date(today.year + 1, today.month, today.day)
        created = _make_project_account(target_date=target_date)

        repo = AsyncMock()
        repo.create = AsyncMock(return_value=created)
        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with patch("modules.accounts.service.get_config_decimal", new=AsyncMock(return_value=Decimal("0.05"))), \
             patch("modules.accounts.service.write_audit_log", new=AsyncMock()) as mock_audit, \
             patch("modules.accounts.service._set_balance_cache", new=AsyncMock()):
            await svc.open_project(
                user,
                CreateProjectAccountRequest(
                    project_name="Maison",
                    target_amount=5_000_000,
                    target_date=target_date,
                ),
            )

        mock_audit.assert_called_once()
        kw = mock_audit.call_args[1]
        assert kw["action"] == "ACCOUNT_OPENED"
        assert kw["metadata"]["account_type"] == "project"
        assert kw["metadata"]["penalty_rate"] == "0.05"

    async def test_balance_starts_at_zero(self):
        """Project Accounts open with zero balance — funded through deposits."""
        from modules.accounts.schemas import CreateProjectAccountRequest
        from modules.accounts.service import AccountService

        user = _make_user()
        today = date.today()
        target_date = date(today.year + 1, today.month, today.day)

        created = _make_project_account(balance=0, target_date=target_date)
        repo = AsyncMock()
        repo.create = AsyncMock(return_value=created)
        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with patch("modules.accounts.service.get_config_decimal", new=AsyncMock(return_value=Decimal("0.05"))), \
             patch("modules.accounts.service.write_audit_log", new=AsyncMock()), \
             patch("modules.accounts.service._set_balance_cache", new=AsyncMock()):
            result = await svc.open_project(
                user,
                CreateProjectAccountRequest(
                    project_name="Zero Balance",
                    target_amount=1_000_000,
                    target_date=target_date,
                ),
            )

        assert result.data["balance"] == 0


# ── FR-017: Progress bar calculation edge cases ───────────────────────────────

class TestProgressCalculationEdgeCases:

    def test_zero_balance_is_zero_percent(self):
        from modules.accounts.service import calculate_progress
        assert calculate_progress(0, 10_000_000) == 0

    def test_exactly_at_target_is_100(self):
        from modules.accounts.service import calculate_progress
        assert calculate_progress(10_000_000, 10_000_000) == 100

    def test_overfunded_capped_at_100(self):
        from modules.accounts.service import calculate_progress
        assert calculate_progress(15_000_000, 10_000_000) == 100

    def test_partial_progress_floor(self):
        from modules.accounts.service import calculate_progress
        # 3,333,333 / 10,000,000 = 33.33% → floor to 33
        assert calculate_progress(3_333_333, 10_000_000) == 33

    def test_zero_target_returns_100(self):
        """Edge case: target_amount=0 means already funded."""
        from modules.accounts.service import calculate_progress
        assert calculate_progress(0, 0) == 100

    def test_result_is_always_int(self):
        from modules.accounts.service import calculate_progress
        result = calculate_progress(1_234_567, 9_999_999)
        assert isinstance(result, int)
