"""
Accounts unit tests — Milestone 2.1.
Covers: min balance enforcement, balance update atomicity,
        open standard account (happy + error paths), Redis cache behavior,
        savings insight calculation.
All external deps (DB, Redis) are mocked.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_user(kyc_status: str = "approved", account_status: str = "active"):
    user = MagicMock()
    user.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.kyc_status = kyc_status
    user.account_status = account_status
    user.full_name = "Amina Njoya"
    user.email = "amina@example.com"
    user.phone_number = "+237600000001"
    return user


def _make_account(
    account_type: str = "standard",
    balance: int = 500_000,       # 5,000 XAF default
    status: str = "active",
    account_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    target_amount: int | None = None,
    maturity_date=None,
    interest_rate=None,
    penalty_rate=None,
):
    acct = MagicMock()
    acct.id = account_id or uuid.UUID("00000000-0000-0000-0000-000000000010")
    acct.user_id = user_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
    acct.account_type = account_type
    acct.account_number = f"STD{'A' * 12}"
    acct.balance = balance
    acct.status = status
    acct.created_at = datetime(2026, 4, 1)
    acct.project_name = None
    acct.target_amount = target_amount
    acct.target_date = None
    acct.maturity_date = maturity_date
    acct.interest_rate = interest_rate
    acct.penalty_rate = penalty_rate
    return acct


# ── Pure function: validate_withdrawal ────────────────────────────────────────

class TestValidateWithdrawal:

    def test_withdrawal_leaving_balance_above_min_passes(self):
        from modules.accounts.service import validate_withdrawal
        # 5,000 XAF balance — withdraw 3,900 XAF leaves 1,100 XAF (above 1,000 XAF min)
        validate_withdrawal(balance=500_000, amount=390_000)  # no exception

    def test_withdrawal_exactly_at_min_passes(self):
        from modules.accounts.service import validate_withdrawal
        # leaves exactly 1,000 XAF (100,000 units) — must pass
        validate_withdrawal(balance=200_000, amount=100_000)  # no exception

    def test_withdrawal_below_min_balance_raises(self):
        from modules.accounts.service import validate_withdrawal
        with pytest.raises(HTTPException) as exc:
            # balance 5,000 XAF, withdraw 4,001 XAF → leaves 999 XAF (below 1,000 XAF min)
            validate_withdrawal(balance=500_000, amount=400_100)
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "MIN_BALANCE_VIOLATION"

    def test_withdrawal_leaving_zero_raises(self):
        from modules.accounts.service import validate_withdrawal
        with pytest.raises(HTTPException) as exc:
            validate_withdrawal(balance=500_000, amount=500_000)
        assert exc.value.status_code == 422


# ── Pure function: validate_term_deposit_opening ──────────────────────────────

class TestValidateTermDepositOpening:

    def test_exactly_minimum_passes(self):
        from modules.accounts.service import validate_term_deposit_opening
        validate_term_deposit_opening(20_000_000)  # no exception

    def test_above_minimum_passes(self):
        from modules.accounts.service import validate_term_deposit_opening
        validate_term_deposit_opening(25_000_000)  # no exception

    def test_below_minimum_raises(self):
        from modules.accounts.service import validate_term_deposit_opening
        with pytest.raises(HTTPException) as exc:
            validate_term_deposit_opening(19_999_999)   # 1 unit below 200,000 XAF
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "TERM_DEPOSIT_MIN_AMOUNT"


# ── Pure function: calculate_savings_insight (FR-015) ─────────────────────────

class TestCalculateSavingsInsight:

    def test_positive_growth_returns_message(self):
        from modules.accounts.service import calculate_savings_insight
        result = calculate_savings_insight(
            current_month_savings=1_230_000,
            last_month_savings=1_000_000,
        )
        assert result == "You saved 23% more this month"

    def test_negative_growth_returns_message(self):
        from modules.accounts.service import calculate_savings_insight
        result = calculate_savings_insight(
            current_month_savings=500_000,
            last_month_savings=1_000_000,
        )
        assert result == "You saved 50% less this month"

    def test_no_change_returns_none(self):
        from modules.accounts.service import calculate_savings_insight
        result = calculate_savings_insight(
            current_month_savings=1_000_000,
            last_month_savings=1_000_000,
        )
        assert result is None

    def test_no_last_month_data_returns_none(self):
        from modules.accounts.service import calculate_savings_insight
        result = calculate_savings_insight(
            current_month_savings=500_000,
            last_month_savings=0,
        )
        assert result is None

    def test_result_is_integer_percent_not_float(self):
        """Insight percentage must be computed with integer arithmetic."""
        from modules.accounts.service import calculate_savings_insight
        # 1,100,000 / 1,000,000 = 10% growth
        result = calculate_savings_insight(1_100_000, 1_000_000)
        assert "10%" in result

    def test_insight_uses_floor_division(self):
        """Partial percent is floored — no rounding up."""
        from modules.accounts.service import calculate_savings_insight
        # 1,019 / 1,000 = 1.9% → should say 1%, not 2%
        result = calculate_savings_insight(1_019, 1_000)
        assert "1%" in result
        assert "2%" not in result


# ── Progress calculation ───────────────────────────────────────────────────────

class TestCalculateProgress:

    def test_zero_progress(self):
        from modules.accounts.service import calculate_progress
        assert calculate_progress(0, 1_000_000) == 0

    def test_fifty_percent(self):
        from modules.accounts.service import calculate_progress
        assert calculate_progress(500_000, 1_000_000) == 50

    def test_over_100_capped(self):
        from modules.accounts.service import calculate_progress
        assert calculate_progress(1_500_000, 1_000_000) == 100

    def test_uses_integer_arithmetic(self):
        from modules.accounts.service import calculate_progress
        result = calculate_progress(333_333, 1_000_000)
        assert isinstance(result, int)
        assert result == 33   # floor(33.3333)


# ── Service: open_standard ────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestOpenStandardAccount:

    def _make_service_with_repo(self, repo_mock):
        from modules.accounts.service import AccountService
        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo_mock
        return svc

    async def test_happy_path_creates_account(self):
        from modules.accounts.schemas import CreateStandardAccountRequest
        from modules.accounts.service import AccountService

        user = _make_user()
        created_account = _make_account(balance=50_000)

        repo = AsyncMock()
        repo.get_standard_account_by_user = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created_account)

        svc = self._make_service_with_repo(repo)

        with patch("modules.accounts.service.write_audit_log", new=AsyncMock()), \
             patch("modules.accounts.service._set_balance_cache", new=AsyncMock()):
            result = await svc.open_standard(
                user, CreateStandardAccountRequest(initial_deposit=50_000)
            )

        assert result.success is True
        assert result.data["balance"] == 50_000
        assert result.data["status"] == "active"

    async def test_below_min_initial_deposit_raises_422(self):
        from modules.accounts.schemas import CreateStandardAccountRequest
        from modules.accounts.service import AccountService, MIN_INITIAL_DEPOSIT

        user = _make_user()
        repo = AsyncMock()
        repo.get_standard_account_by_user = AsyncMock(return_value=None)

        svc = self._make_service_with_repo(repo)

        with pytest.raises(HTTPException) as exc:
            await svc.open_standard(
                user,
                CreateStandardAccountRequest(initial_deposit=MIN_INITIAL_DEPOSIT - 1),
            )
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "BELOW_MIN_INITIAL_DEPOSIT"

    async def test_duplicate_standard_account_raises_409(self):
        from modules.accounts.schemas import CreateStandardAccountRequest
        from modules.accounts.service import AccountService

        user = _make_user()
        existing = _make_account()

        repo = AsyncMock()
        repo.get_standard_account_by_user = AsyncMock(return_value=existing)

        svc = self._make_service_with_repo(repo)

        with pytest.raises(HTTPException) as exc:
            await svc.open_standard(
                user,
                CreateStandardAccountRequest(initial_deposit=50_000),
            )
        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "ACCOUNT_ALREADY_EXISTS"

    async def test_audit_log_written_on_open(self):
        from modules.accounts.schemas import CreateStandardAccountRequest
        from modules.accounts.service import AccountService

        user = _make_user()
        created_account = _make_account(balance=50_000)

        repo = AsyncMock()
        repo.get_standard_account_by_user = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created_account)

        svc = self._make_service_with_repo(repo)

        with patch("modules.accounts.service.write_audit_log", new=AsyncMock()) as mock_audit, \
             patch("modules.accounts.service._set_balance_cache", new=AsyncMock()):
            await svc.open_standard(
                user, CreateStandardAccountRequest(initial_deposit=50_000)
            )

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args[1]
        assert call_kwargs["action"] == "ACCOUNT_OPENED"
        assert call_kwargs["entity_type"] == "account"
        assert call_kwargs["metadata"]["account_type"] == "standard"

    async def test_balance_cached_in_redis_after_creation(self):
        from modules.accounts.schemas import CreateStandardAccountRequest
        from modules.accounts.service import AccountService

        user = _make_user()
        created_account = _make_account(balance=50_000)

        repo = AsyncMock()
        repo.get_standard_account_by_user = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created_account)

        svc = self._make_service_with_repo(repo)

        with patch("modules.accounts.service.write_audit_log", new=AsyncMock()), \
             patch("modules.accounts.service._set_balance_cache", new=AsyncMock()) as mock_cache:
            await svc.open_standard(
                user, CreateStandardAccountRequest(initial_deposit=50_000)
            )

        mock_cache.assert_called_once_with(str(created_account.id), 50_000)

    async def test_exactly_min_initial_deposit_passes(self):
        from modules.accounts.schemas import CreateStandardAccountRequest
        from modules.accounts.service import AccountService, MIN_INITIAL_DEPOSIT

        user = _make_user()
        created_account = _make_account(balance=MIN_INITIAL_DEPOSIT)

        repo = AsyncMock()
        repo.get_standard_account_by_user = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created_account)

        svc = self._make_service_with_repo(repo)

        with patch("modules.accounts.service.write_audit_log", new=AsyncMock()), \
             patch("modules.accounts.service._set_balance_cache", new=AsyncMock()):
            result = await svc.open_standard(
                user, CreateStandardAccountRequest(initial_deposit=MIN_INITIAL_DEPOSIT)
            )
        assert result.success is True


# ── Service: list_accounts with balance cache ─────────────────────────────────

@pytest.mark.asyncio
class TestListAccounts:

    async def test_returns_all_active_accounts(self):
        from modules.accounts.service import AccountService

        user = _make_user()
        accts = [_make_account(balance=500_000), _make_account(balance=300_000)]

        repo = AsyncMock()
        repo.list_by_user = AsyncMock(return_value=accts)

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with patch("modules.accounts.service._get_cached_balance", new=AsyncMock(side_effect=lambda aid, db_bal: db_bal)):
            result = await svc.list_accounts(user.id)

        assert result.success is True
        assert len(result.data["accounts"]) == 2

    async def test_total_balance_is_aggregate_of_all_accounts(self):
        from modules.accounts.service import AccountService

        accts = [
            _make_account(balance=500_000),
            _make_account(balance=300_000),
            _make_account(balance=200_000),
        ]

        repo = AsyncMock()
        repo.list_by_user = AsyncMock(return_value=accts)

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with patch("modules.accounts.service._get_cached_balance", new=AsyncMock(side_effect=lambda aid, db_bal: db_bal)):
            result = await svc.list_accounts(uuid.uuid4())

        assert result.data["total_balance"] == 1_000_000

    async def test_balance_served_from_cache_not_db(self):
        """Redis cache should be consulted before the DB balance is used."""
        from modules.accounts.service import AccountService

        acct = _make_account(balance=100_000)  # DB balance
        cached_balance = 999_000               # cache says different value (fresher)

        repo = AsyncMock()
        repo.list_by_user = AsyncMock(return_value=[acct])

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with patch("modules.accounts.service._get_cached_balance", new=AsyncMock(return_value=cached_balance)):
            result = await svc.list_accounts(uuid.uuid4())

        assert result.data["accounts"][0]["balance"] == cached_balance

    async def test_empty_account_list_returns_zero_total(self):
        from modules.accounts.service import AccountService

        repo = AsyncMock()
        repo.list_by_user = AsyncMock(return_value=[])

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        result = await svc.list_accounts(uuid.uuid4())

        assert result.data["total_balance"] == 0
        assert result.data["accounts"] == []


# ── Service: get_account ──────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestGetAccount:

    async def test_returns_account_for_owner(self):
        from modules.accounts.service import AccountService

        acct = _make_account(balance=500_000)
        repo = AsyncMock()
        repo.get_user_account = AsyncMock(return_value=acct)

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with patch("modules.accounts.service._get_cached_balance", new=AsyncMock(return_value=500_000)):
            result = await svc.get_account(str(acct.id), acct.user_id)

        assert result.success is True
        assert result.data["balance"] == 500_000

    async def test_returns_404_for_nonexistent_account(self):
        from modules.accounts.service import AccountService

        repo = AsyncMock()
        repo.get_user_account = AsyncMock(return_value=None)

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with pytest.raises(HTTPException) as exc:
            await svc.get_account(str(uuid.uuid4()), uuid.uuid4())
        assert exc.value.status_code == 404
        assert exc.value.detail["code"] == "ACCOUNT_NOT_FOUND"

    async def test_returns_400_for_invalid_uuid(self):
        from modules.accounts.service import AccountService

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await svc.get_account("not-a-uuid", uuid.uuid4())
        assert exc.value.status_code == 400
        assert exc.value.detail["code"] == "INVALID_ACCOUNT_ID"


# ── Balance atomicity ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestBalanceUpdateAtomicity:

    async def test_apply_balance_delta_credit(self):
        """Positive delta increases balance correctly."""
        from modules.accounts.service import AccountService

        acct = _make_account(balance=500_000)
        updated = _make_account(balance=600_000)

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=acct)
        repo.update = AsyncMock(return_value=updated)

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with patch("modules.accounts.service._invalidate_balance_cache", new=AsyncMock()), \
             patch("modules.accounts.service._set_balance_cache", new=AsyncMock()):
            result = await svc.apply_balance_delta(acct.id, +100_000)

        repo.update.assert_called_once_with(acct, balance=600_000)

    async def test_apply_balance_delta_debit(self):
        """Negative delta decreases balance correctly."""
        from modules.accounts.service import AccountService

        acct = _make_account(balance=500_000)
        updated = _make_account(balance=300_000)

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=acct)
        repo.update = AsyncMock(return_value=updated)

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with patch("modules.accounts.service._invalidate_balance_cache", new=AsyncMock()), \
             patch("modules.accounts.service._set_balance_cache", new=AsyncMock()):
            await svc.apply_balance_delta(acct.id, -200_000)

        repo.update.assert_called_once_with(acct, balance=300_000)

    async def test_debit_below_zero_raises(self):
        """Balance must never go negative."""
        from modules.accounts.service import AccountService

        acct = _make_account(balance=50_000)
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=acct)

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with pytest.raises(HTTPException) as exc:
            await svc.apply_balance_delta(acct.id, -100_000)
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "INSUFFICIENT_BALANCE"

    async def test_standard_account_min_balance_enforced_on_debit(self):
        """Debit that would leave a Standard Account below 1,000 XAF is blocked."""
        from modules.accounts.service import AccountService

        # balance: 1,500 XAF. Debit 600 XAF → leaves 900 XAF (below 1,000 min)
        acct = _make_account(account_type="standard", balance=150_000)
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=acct)

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with pytest.raises(HTTPException) as exc:
            await svc.apply_balance_delta(acct.id, -60_000)
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "MIN_BALANCE_VIOLATION"

    async def test_cache_invalidated_before_balance_write(self):
        """Cache must be invalidated before the DB write — not after."""
        from modules.accounts.service import AccountService

        call_order: list[str] = []
        acct = _make_account(balance=500_000)
        updated = _make_account(balance=600_000)

        async def mock_invalidate(account_id):
            call_order.append("invalidate")

        async def mock_update(account, **fields):
            call_order.append("db_write")
            return updated

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=acct)
        repo.update = mock_update

        db = AsyncMock()
        svc = AccountService(db)
        svc._repo = repo

        with patch("modules.accounts.service._invalidate_balance_cache", new=mock_invalidate), \
             patch("modules.accounts.service._set_balance_cache", new=AsyncMock()):
            await svc.apply_balance_delta(acct.id, +100_000)

        # Invalidation MUST come before the DB write
        assert call_order[0] == "invalidate"
        assert call_order[1] == "db_write"
