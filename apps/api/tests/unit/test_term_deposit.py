"""
Term Deposit unit tests — Milestone 2.3.
Covers: interest calculation (BIGINT, no rounding errors), maturity date arithmetic,
        days-to-maturity, early-break penalty, open_term_deposit, calculator,
        close_account.
All external deps (DB, Redis) are mocked.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_user(kyc_status: str = "approved"):
    user = MagicMock()
    user.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.kyc_status = kyc_status
    user.full_name = "Amina Njoya"
    return user


def _make_term_deposit(
    balance: int = 20_000_000,
    interest_rate=Decimal("0.0200"),
    penalty_rate=Decimal("0.0150"),
    maturity_date: date | None = None,
    status: str = "active",
    account_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
):
    acct = MagicMock()
    acct.id = account_id or uuid.UUID("00000000-0000-0000-0000-000000000020")
    acct.user_id = user_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
    acct.account_type = "term_deposit"
    acct.account_number = "TDG" + "A" * 12
    acct.balance = balance
    acct.status = status
    acct.created_at = datetime(2026, 4, 1)
    acct.interest_rate = interest_rate
    acct.penalty_rate = penalty_rate
    acct.maturity_date = maturity_date or date(2027, 4, 1)  # 12 months from Apr 2026
    acct.project_name = None
    acct.target_amount = None
    acct.target_date = None
    return acct


def _make_standard_account(balance: int = 1_000_000):
    acct = MagicMock()
    acct.id = uuid.UUID("00000000-0000-0000-0000-000000000010")
    acct.account_type = "standard"
    acct.account_number = "STD" + "A" * 12
    acct.balance = balance
    acct.status = "active"
    acct.penalty_rate = None
    return acct


# ── FR-024: calculate_term_deposit_interest ────────────────────────────────────

class TestCalculateTermDepositInterest:

    def test_annual_rate_12_months(self):
        """200,000 XAF × 2% × 12m / 12 = 4,000 XAF = 400,000 units."""
        from modules.accounts.service import calculate_term_deposit_interest
        result = calculate_term_deposit_interest(20_000_000, Decimal("0.0200"), 12)
        assert result == 400_000

    def test_pro_rata_6_months(self):
        """200,000 XAF × 2% × 6m / 12 = 2,000 XAF = 200,000 units."""
        from modules.accounts.service import calculate_term_deposit_interest
        result = calculate_term_deposit_interest(20_000_000, Decimal("0.0200"), 6)
        assert result == 200_000

    def test_pro_rata_3_months(self):
        """200,000 XAF × 2% × 3m / 12 = 1,000 XAF = 100,000 units."""
        from modules.accounts.service import calculate_term_deposit_interest
        result = calculate_term_deposit_interest(20_000_000, Decimal("0.0200"), 3)
        assert result == 100_000

    def test_floor_not_round(self):
        """
        When interest has a fractional unit, floor is applied.
        principal=1 unit, rate=0.02, term=1 month → 0.02/12 = 0.001666... → floor = 0.
        """
        from modules.accounts.service import calculate_term_deposit_interest
        result = calculate_term_deposit_interest(1, Decimal("0.0200"), 1)
        assert result == 0  # floor of 0.001666...

    def test_always_integer(self):
        from modules.accounts.service import calculate_term_deposit_interest
        result = calculate_term_deposit_interest(20_000_000, Decimal("0.0200"), 7)
        assert isinstance(result, int)

    def test_zero_rate_returns_zero(self):
        from modules.accounts.service import calculate_term_deposit_interest
        result = calculate_term_deposit_interest(20_000_000, Decimal("0"), 12)
        assert result == 0

    def test_large_principal_no_float_error(self):
        """Large sums must remain BIGINT-safe — no float overflow or precision loss."""
        from modules.accounts.service import calculate_term_deposit_interest
        # 1 billion XAF = 100,000,000,000 units
        result = calculate_term_deposit_interest(100_000_000_000, Decimal("0.0200"), 12)
        assert result == 2_000_000_000
        assert isinstance(result, int)

    def test_odd_term_months_is_pro_rata(self):
        """11 months: 200,000 XAF × 2% × 11 / 12 = floor(366,666.6...) = 366,666."""
        from modules.accounts.service import calculate_term_deposit_interest
        result = calculate_term_deposit_interest(20_000_000, Decimal("0.0200"), 11)
        assert result == 366_666


# ── Maturity date arithmetic ───────────────────────────────────────────────────

class TestCalculateTermDepositMaturityDate:

    def test_simple_month_addition(self):
        from modules.accounts.service import calculate_term_deposit_maturity_date
        result = calculate_term_deposit_maturity_date(date(2026, 4, 15), 3)
        assert result == date(2026, 7, 15)

    def test_year_boundary(self):
        """December + 1 month = January next year."""
        from modules.accounts.service import calculate_term_deposit_maturity_date
        result = calculate_term_deposit_maturity_date(date(2026, 12, 10), 1)
        assert result == date(2027, 1, 10)

    def test_year_boundary_multi_month(self):
        """October + 6 months = April next year."""
        from modules.accounts.service import calculate_term_deposit_maturity_date
        result = calculate_term_deposit_maturity_date(date(2026, 10, 22), 6)
        assert result == date(2027, 4, 22)

    def test_end_of_month_clamped_feb(self):
        """Jan 31 + 1 month = Feb 28 (2026 is not a leap year)."""
        from modules.accounts.service import calculate_term_deposit_maturity_date
        result = calculate_term_deposit_maturity_date(date(2026, 1, 31), 1)
        assert result == date(2026, 2, 28)

    def test_leap_year_feb_clamped(self):
        """Jan 31 + 1 month in a leap year = Feb 29."""
        from modules.accounts.service import calculate_term_deposit_maturity_date
        result = calculate_term_deposit_maturity_date(date(2024, 1, 31), 1)
        assert result == date(2024, 2, 29)

    def test_12_months_same_day_next_year(self):
        """12 months is exactly one year, same day."""
        from modules.accounts.service import calculate_term_deposit_maturity_date
        result = calculate_term_deposit_maturity_date(date(2026, 4, 22), 12)
        assert result == date(2027, 4, 22)

    def test_day_within_month_range_unchanged(self):
        """Day 15 is always valid in all months — no clamping needed."""
        from modules.accounts.service import calculate_term_deposit_maturity_date
        result = calculate_term_deposit_maturity_date(date(2026, 1, 15), 1)
        assert result == date(2026, 2, 15)


# ── FR-027: calculate_days_to_maturity ────────────────────────────────────────

class TestCalculateDaysToMaturity:

    def test_future_maturity(self):
        from modules.accounts.service import calculate_days_to_maturity
        result = calculate_days_to_maturity(date(2027, 4, 22), today=date(2026, 4, 22))
        assert result == 365

    def test_maturity_today_is_zero(self):
        from modules.accounts.service import calculate_days_to_maturity
        today = date(2026, 4, 22)
        result = calculate_days_to_maturity(today, today=today)
        assert result == 0

    def test_past_maturity_returns_zero(self):
        """Already matured accounts return 0, never negative."""
        from modules.accounts.service import calculate_days_to_maturity
        result = calculate_days_to_maturity(date(2025, 1, 1), today=date(2026, 4, 22))
        assert result == 0

    def test_14_days_before_maturity(self):
        from modules.accounts.service import calculate_days_to_maturity
        result = calculate_days_to_maturity(date(2026, 5, 6), today=date(2026, 4, 22))
        assert result == 14

    def test_result_is_int(self):
        from modules.accounts.service import calculate_days_to_maturity
        result = calculate_days_to_maturity(date(2027, 4, 22), today=date(2026, 4, 22))
        assert isinstance(result, int)


# ── FR-026: Early break penalty ───────────────────────────────────────────────

class TestTermDepositEarlyBreak:
    """
    calculate_early_withdrawal is reused for term deposits.
    penalty = floor(principal × break_rate); net = principal - penalty.
    """

    def test_1_5_percent_of_principal(self):
        from modules.accounts.service import calculate_early_withdrawal
        # 200,000 XAF = 20,000,000 units, 1.5% = 300,000 units = 3,000 XAF
        net, penalty = calculate_early_withdrawal(20_000_000, Decimal("0.0150"))
        assert penalty == 300_000
        assert net == 19_700_000

    def test_net_plus_penalty_equals_principal(self):
        from modules.accounts.service import calculate_early_withdrawal
        principal = 20_000_000
        net, penalty = calculate_early_withdrawal(principal, Decimal("0.0150"))
        assert net + penalty == principal

    def test_penalty_floor_not_round(self):
        """
        principal=10_000_001, rate=0.015 → 150,000.015 → floor = 150,000.
        net = 10_000_001 - 150_000 = 9_850_001. Invariant holds exactly.
        """
        from modules.accounts.service import calculate_early_withdrawal
        principal = 10_000_001
        net, penalty = calculate_early_withdrawal(principal, Decimal("0.0150"))
        assert penalty == 150_000  # floor of 150_000.015
        assert net + penalty == principal

    def test_zero_break_rate_no_penalty(self):
        from modules.accounts.service import calculate_early_withdrawal
        net, penalty = calculate_early_withdrawal(20_000_000, Decimal("0"))
        assert penalty == 0
        assert net == 20_000_000


# ── FR-023: open_term_deposit ─────────────────────────────────────────────────

class TestOpenTermDeposit:

    def _make_service_with_mocks(self, repo_overrides=None):
        """Return (service, mock_repo, patched_redis, patched_audit, patched_config)."""
        from modules.accounts.service import AccountService

        db = AsyncMock()
        service = AccountService(db)

        mock_repo = AsyncMock()
        mock_repo.create = AsyncMock(side_effect=lambda acct: acct)
        if repo_overrides:
            for k, v in repo_overrides.items():
                setattr(mock_repo, k, v)
        service._repo = mock_repo

        return service, mock_repo

    @patch("modules.accounts.service.write_audit_log", new_callable=AsyncMock)
    @patch("modules.accounts.service._set_balance_cache", new_callable=AsyncMock)
    @patch("modules.accounts.service.get_config_decimal")
    @pytest.mark.asyncio
    async def test_happy_path_creates_account(
        self, mock_cfg, mock_cache, mock_audit
    ):
        from modules.accounts.schemas import CreateTermDepositRequest

        mock_cfg.return_value = Decimal("0.0200")
        service, _ = self._make_service_with_mocks()

        user = _make_user()
        payload = CreateTermDepositRequest(amount=20_000_000, duration_months=12)
        response = await service.open_term_deposit(user, payload)

        assert response.success is True
        data = response.data
        assert data["principal"] == 20_000_000
        assert data["status"] == "active"
        assert data["duration_months"] == 12
        assert data["projected_interest"] == 400_000  # 2% × 12m
        assert data["total_at_maturity"] == 20_400_000

    @patch("modules.accounts.service.write_audit_log", new_callable=AsyncMock)
    @patch("modules.accounts.service._set_balance_cache", new_callable=AsyncMock)
    @patch("modules.accounts.service.get_config_decimal")
    @pytest.mark.asyncio
    async def test_below_min_raises_422(self, mock_cfg, mock_cache, mock_audit):
        from modules.accounts.service import AccountService
        from modules.accounts.schemas import CreateTermDepositRequest

        mock_cfg.return_value = Decimal("0.0200")
        db = AsyncMock()
        service = AccountService(db)
        service._repo = AsyncMock()
        user = _make_user()

        # Schema-level validation catches this first — test via service validator too
        with pytest.raises(HTTPException) as exc:
            await service.open_term_deposit(
                user,
                # Bypass schema by calling validate directly
                type("Payload", (), {"amount": 19_999_999, "duration_months": 12})(),
            )
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "TERM_DEPOSIT_MIN_AMOUNT"

    @patch("modules.accounts.service.write_audit_log", new_callable=AsyncMock)
    @patch("modules.accounts.service._set_balance_cache", new_callable=AsyncMock)
    @patch("modules.accounts.service.get_config_decimal")
    @pytest.mark.asyncio
    async def test_interest_rate_snapshotted_on_account(
        self, mock_cfg, mock_cache, mock_audit
    ):
        """FR-024: The rate stored on the account comes from system_config at creation."""
        from modules.accounts.schemas import CreateTermDepositRequest

        # Simulate admin setting a custom rate
        mock_cfg.return_value = Decimal("0.0300")  # 3% — non-default
        service, mock_repo = self._make_service_with_mocks()
        created_accounts: list = []

        async def capture_create(acct):
            created_accounts.append(acct)
            return acct
        mock_repo.create = capture_create

        user = _make_user()
        payload = CreateTermDepositRequest(amount=20_000_000, duration_months=6)
        await service.open_term_deposit(user, payload)

        account = created_accounts[0]
        assert Decimal(str(account.interest_rate)) == Decimal("0.0300")

    @patch("modules.accounts.service.write_audit_log", new_callable=AsyncMock)
    @patch("modules.accounts.service._set_balance_cache", new_callable=AsyncMock)
    @patch("modules.accounts.service.get_config_decimal")
    @pytest.mark.asyncio
    async def test_early_break_rate_snapshotted_on_account(
        self, mock_cfg, mock_cache, mock_audit
    ):
        """FR-026: The break rate stored on the account is snapshotted at creation."""
        from modules.accounts.schemas import CreateTermDepositRequest

        def cfg_side_effect(db, key, default):
            # Return different rates for different keys
            if "interest" in key:
                return Decimal("0.0200")
            return Decimal("0.0250")  # 2.5% break rate — custom

        mock_cfg.side_effect = cfg_side_effect
        service, mock_repo = self._make_service_with_mocks()
        created_accounts: list = []

        async def capture_create(acct):
            created_accounts.append(acct)
            return acct
        mock_repo.create = capture_create

        user = _make_user()
        payload = CreateTermDepositRequest(amount=20_000_000, duration_months=6)
        await service.open_term_deposit(user, payload)

        account = created_accounts[0]
        assert Decimal(str(account.penalty_rate)) == Decimal("0.0250")

    @patch("modules.accounts.service.write_audit_log", new_callable=AsyncMock)
    @patch("modules.accounts.service._set_balance_cache", new_callable=AsyncMock)
    @patch("modules.accounts.service.get_config_decimal")
    @pytest.mark.asyncio
    async def test_balance_equals_principal_not_including_interest(
        self, mock_cfg, mock_cache, mock_audit
    ):
        """
        Balance at creation = principal only.
        Interest is credited only at maturity — not upfront.
        """
        from modules.accounts.schemas import CreateTermDepositRequest

        mock_cfg.return_value = Decimal("0.0200")
        service, mock_repo = self._make_service_with_mocks()
        created_accounts: list = []

        async def capture_create(acct):
            created_accounts.append(acct)
            return acct
        mock_repo.create = capture_create

        user = _make_user()
        payload = CreateTermDepositRequest(amount=20_000_000, duration_months=12)
        await service.open_term_deposit(user, payload)

        account = created_accounts[0]
        assert account.balance == 20_000_000  # NOT 20_400_000

    @patch("modules.accounts.service.write_audit_log", new_callable=AsyncMock)
    @patch("modules.accounts.service._set_balance_cache", new_callable=AsyncMock)
    @patch("modules.accounts.service.get_config_decimal")
    @pytest.mark.asyncio
    async def test_maturity_date_computed_correctly(
        self, mock_cfg, mock_cache, mock_audit
    ):
        from modules.accounts.schemas import CreateTermDepositRequest

        mock_cfg.return_value = Decimal("0.0200")
        service, mock_repo = self._make_service_with_mocks()
        created_accounts: list = []

        async def capture_create(acct):
            created_accounts.append(acct)
            return acct
        mock_repo.create = capture_create

        user = _make_user()
        payload = CreateTermDepositRequest(amount=20_000_000, duration_months=3)
        await service.open_term_deposit(user, payload)

        account = created_accounts[0]
        today = date.today()
        from modules.accounts.service import calculate_term_deposit_maturity_date
        expected_maturity = calculate_term_deposit_maturity_date(today, 3)
        assert account.maturity_date == expected_maturity

    @patch("modules.accounts.service.write_audit_log", new_callable=AsyncMock)
    @patch("modules.accounts.service._set_balance_cache", new_callable=AsyncMock)
    @patch("modules.accounts.service.get_config_decimal")
    @pytest.mark.asyncio
    async def test_audit_log_written(self, mock_cfg, mock_cache, mock_audit):
        from modules.accounts.schemas import CreateTermDepositRequest

        mock_cfg.return_value = Decimal("0.0200")
        service, _ = self._make_service_with_mocks()

        user = _make_user()
        payload = CreateTermDepositRequest(amount=20_000_000, duration_months=6)
        await service.open_term_deposit(user, payload)

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args
        assert call_kwargs.kwargs["action"] == "ACCOUNT_OPENED"
        assert call_kwargs.kwargs["metadata"]["account_type"] == "term_deposit"


# ── FR-025: get_term_deposit_calculator ───────────────────────────────────────

class TestTermDepositCalculator:

    @patch("modules.accounts.service.get_config_decimal")
    @pytest.mark.asyncio
    async def test_projects_correct_interest(self, mock_cfg):
        from modules.accounts.service import AccountService

        mock_cfg.return_value = Decimal("0.0200")
        db = AsyncMock()
        service = AccountService(db)
        service._repo = AsyncMock()

        response = await service.get_term_deposit_calculator(20_000_000, 12)

        assert response.success is True
        assert response.data["projected_interest"] == 400_000
        assert response.data["total_at_maturity"] == 20_400_000

    @patch("modules.accounts.service.get_config_decimal")
    @pytest.mark.asyncio
    async def test_total_at_maturity_equals_principal_plus_interest(self, mock_cfg):
        from modules.accounts.service import AccountService

        mock_cfg.return_value = Decimal("0.0200")
        db = AsyncMock()
        service = AccountService(db)
        service._repo = AsyncMock()

        response = await service.get_term_deposit_calculator(20_000_000, 6)

        data = response.data
        assert data["total_at_maturity"] == data["amount"] + data["projected_interest"]

    @patch("modules.accounts.service.get_config_decimal")
    @pytest.mark.asyncio
    async def test_early_break_penalty_in_calculator(self, mock_cfg):
        from modules.accounts.service import AccountService

        # Return 0.02 for interest, 0.015 for break rate
        call_count = [0]
        def cfg_side_effect(db, key, default):
            call_count[0] += 1
            if "interest" in key:
                return Decimal("0.0200")
            return Decimal("0.0150")

        mock_cfg.side_effect = cfg_side_effect
        db = AsyncMock()
        service = AccountService(db)
        service._repo = AsyncMock()

        response = await service.get_term_deposit_calculator(20_000_000, 12)

        data = response.data
        # 1.5% of 20,000,000 = 300,000
        assert data["early_break_penalty"] == 300_000
        assert data["net_if_broken_early"] == 19_700_000

    @patch("modules.accounts.service.get_config_decimal")
    @pytest.mark.asyncio
    async def test_below_min_raises_422(self, mock_cfg):
        from modules.accounts.service import AccountService

        mock_cfg.return_value = Decimal("0.0200")
        db = AsyncMock()
        service = AccountService(db)
        service._repo = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await service.get_term_deposit_calculator(19_999_999, 12)
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "TERM_DEPOSIT_MIN_AMOUNT"

    @patch("modules.accounts.service.get_config_decimal")
    @pytest.mark.asyncio
    async def test_zero_duration_raises_422(self, mock_cfg):
        from modules.accounts.service import AccountService

        mock_cfg.return_value = Decimal("0.0200")
        db = AsyncMock()
        service = AccountService(db)
        service._repo = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await service.get_term_deposit_calculator(20_000_000, 0)
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "INVALID_DURATION"


# ── Close account ──────────────────────────────────────────────────────────────

class TestCloseAccount:

    def _make_service(self):
        from modules.accounts.service import AccountService
        db = AsyncMock()
        service = AccountService(db)
        service._repo = AsyncMock()
        return service

    @patch("modules.accounts.service.write_audit_log", new_callable=AsyncMock)
    @patch("modules.accounts.service._invalidate_balance_cache", new_callable=AsyncMock)
    @patch("modules.accounts.service._get_cached_balance", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_happy_path_zero_balance(
        self, mock_balance, mock_invalidate, mock_audit
    ):
        service = self._make_service()
        account = _make_standard_account(balance=0)
        service._repo.get_user_account = AsyncMock(return_value=account)

        async def apply_update(acct, **kw):
            for k, v in kw.items():
                setattr(acct, k, v)
            return acct
        service._repo.update = apply_update

        mock_balance.return_value = 0

        response = await service.close_account(
            str(account.id), uuid.UUID("00000000-0000-0000-0000-000000000001")
        )

        assert response.success is True
        assert response.data["status"] == "closed"
        mock_invalidate.assert_called_once_with(str(account.id))

    @patch("modules.accounts.service._get_cached_balance", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_nonzero_balance_raises_422(self, mock_balance):
        service = self._make_service()
        account = _make_standard_account(balance=500_000)
        service._repo.get_user_account = AsyncMock(return_value=account)
        mock_balance.return_value = 500_000

        with pytest.raises(HTTPException) as exc:
            await service.close_account(
                str(account.id), uuid.UUID("00000000-0000-0000-0000-000000000001")
            )
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "ACCOUNT_NOT_EMPTY"

    @pytest.mark.asyncio
    async def test_wrong_user_or_not_found_raises_404(self):
        service = self._make_service()
        service._repo.get_user_account = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await service.close_account(
                str(uuid.uuid4()), uuid.UUID("00000000-0000-0000-0000-000000000001")
            )
        assert exc.value.status_code == 404
        assert exc.value.detail["code"] == "ACCOUNT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_invalid_uuid_raises_400(self):
        service = self._make_service()

        with pytest.raises(HTTPException) as exc:
            await service.close_account("not-a-uuid", uuid.UUID("00000000-0000-0000-0000-000000000001"))
        assert exc.value.status_code == 400

    @patch("modules.accounts.service.write_audit_log", new_callable=AsyncMock)
    @patch("modules.accounts.service._invalidate_balance_cache", new_callable=AsyncMock)
    @patch("modules.accounts.service._get_cached_balance", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_audit_log_action_is_account_closed(
        self, mock_balance, mock_invalidate, mock_audit
    ):
        service = self._make_service()
        account = _make_standard_account(balance=0)
        service._repo.get_user_account = AsyncMock(return_value=account)

        async def apply_update(acct, **kw):
            for k, v in kw.items():
                setattr(acct, k, v)
            return acct
        service._repo.update = apply_update

        mock_balance.return_value = 0

        await service.close_account(
            str(account.id), uuid.UUID("00000000-0000-0000-0000-000000000001")
        )

        mock_audit.assert_called_once()
        assert mock_audit.call_args.kwargs["action"] == "ACCOUNT_CLOSED"

    @patch("modules.accounts.service.write_audit_log", new_callable=AsyncMock)
    @patch("modules.accounts.service._invalidate_balance_cache", new_callable=AsyncMock)
    @patch("modules.accounts.service._get_cached_balance", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_close_term_deposit_also_works(
        self, mock_balance, mock_invalidate, mock_audit
    ):
        service = self._make_service()
        # A matured term deposit with zero balance (interest already credited and withdrawn)
        account = _make_term_deposit(balance=0)
        service._repo.get_user_account = AsyncMock(return_value=account)

        async def apply_update(acct, **kw):
            for k, v in kw.items():
                setattr(acct, k, v)
            return acct
        service._repo.update = apply_update

        mock_balance.return_value = 0

        response = await service.close_account(
            str(account.id), uuid.UUID("00000000-0000-0000-0000-000000000001")
        )

        assert response.success is True


# ── FR-027: days_to_maturity in AccountData ────────────────────────────────────

class TestDaysToMaturityInAccountData:
    """
    _build_account_data must compute days_to_maturity for term deposits.
    """

    def test_term_deposit_has_days_to_maturity(self):
        from modules.accounts.service import _build_account_data

        today = date.today()
        from datetime import timedelta
        maturity = today + timedelta(days=30)

        account = _make_term_deposit(maturity_date=maturity)
        data = _build_account_data(account, 20_000_000)

        assert data.days_to_maturity == 30

    def test_standard_account_has_no_days_to_maturity(self):
        from modules.accounts.service import _build_account_data

        account = MagicMock()
        account.id = uuid.uuid4()
        account.account_type = "standard"
        account.account_number = "STD" + "A" * 12
        account.balance = 500_000
        account.status = "active"
        account.created_at = datetime(2026, 4, 1)
        account.project_name = None
        account.target_amount = None
        account.target_date = None
        account.maturity_date = None
        account.interest_rate = None
        account.penalty_rate = None

        data = _build_account_data(account, 500_000)

        assert data.days_to_maturity is None

    def test_matured_term_deposit_shows_zero(self):
        from modules.accounts.service import _build_account_data
        from datetime import timedelta

        yesterday = date.today() - timedelta(days=1)
        account = _make_term_deposit(maturity_date=yesterday)
        data = _build_account_data(account, 20_000_000)

        assert data.days_to_maturity == 0
