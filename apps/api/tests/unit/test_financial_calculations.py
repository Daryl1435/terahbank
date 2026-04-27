"""
Financial calculation tests — MANDATORY. No PR merges without these passing.
All amounts in BIGINT (smallest XAF unit). Never FLOAT. Never round up.
"""
from decimal import Decimal
import pytest


class TestInterestCalculation:
    def test_term_deposit_2_percent_annual(self):
        # 200,000 XAF × 2.0% = 4,000 XAF interest
        # In smallest unit: 20000000 × 0.02 = 400000
        from modules.accounts.service import calculate_annual_interest
        result = calculate_annual_interest(20000000, Decimal("0.02"))
        assert result == 400000

    def test_result_is_int_not_float(self):
        from modules.accounts.service import calculate_annual_interest
        result = calculate_annual_interest(20000000, Decimal("0.02"))
        assert isinstance(result, int)

    def test_interest_rounds_down(self):
        # 100,001 smallest units × 2% = 2000.02 → must floor to 2000
        from modules.accounts.service import calculate_annual_interest
        result = calculate_annual_interest(100001, Decimal("0.02"))
        assert result == 2000   # floor, not round


class TestEarlyWithdrawalPenalty:
    def test_project_account_penalty(self):
        # Balance 50,000 XAF (5000000 units), penalty 5% = 2,500 XAF (250000 units)
        from modules.accounts.service import calculate_early_withdrawal
        balance = 5000000
        penalty_rate = Decimal("0.05")
        net, penalty = calculate_early_withdrawal(balance, penalty_rate)
        assert penalty == 250000
        assert net == 4750000
        assert net + penalty == balance   # must balance exactly

    def test_term_deposit_early_break(self):
        # 200,000 XAF (20000000 units), 1.5% penalty = 3,000 XAF (300000 units)
        from modules.accounts.service import calculate_early_withdrawal
        _, penalty = calculate_early_withdrawal(20000000, Decimal("0.015"))
        assert penalty == 300000

    def test_penalty_never_exceeds_balance(self):
        from modules.accounts.service import calculate_early_withdrawal
        balance = 100000
        net, penalty = calculate_early_withdrawal(balance, Decimal("0.99"))
        assert net >= 0
        assert penalty <= balance


class TestProgressCalculation:
    def test_zero_progress(self):
        from modules.accounts.service import calculate_progress
        assert calculate_progress(0, 1000000) == 0

    def test_fifty_percent(self):
        from modules.accounts.service import calculate_progress
        assert calculate_progress(500000, 1000000) == 50

    def test_over_100_capped(self):
        from modules.accounts.service import calculate_progress
        assert calculate_progress(1500000, 1000000) == 100

    def test_milestone_triggers(self):
        from modules.accounts.service import get_triggered_milestones
        assert 25 in get_triggered_milestones(old_pct=24, new_pct=26)
        milestones = get_triggered_milestones(old_pct=74, new_pct=101)
        assert 75 in milestones
        assert 100 in milestones


class TestMinimumBalance:
    def test_standard_account_min_balance_enforcement(self):
        from modules.accounts.service import validate_withdrawal
        with pytest.raises(Exception):
            # Withdrawal that would leave 900 XAF (90000 units) — below 1000 XAF min
            validate_withdrawal(balance=1000000, amount=910000)

    def test_term_deposit_minimum_opening(self):
        from modules.accounts.service import validate_term_deposit_opening
        with pytest.raises(Exception):
            validate_term_deposit_opening(amount=19999999)  # below 200,000 XAF
