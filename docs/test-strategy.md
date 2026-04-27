# TerahBank — Test Strategy

> Financial software has zero tolerance for calculation errors.
> Every monetary operation must be tested with BIGINT edge cases.
> Rule: No PR merges without tests passing. No financial logic without unit tests.

---

## Test Pyramid

```
         /\
        /  \
       / E2E \         ← ~5% — Critical user journeys only
      /--------\
     / Integration\    ← ~25% — Module boundaries + external integrations
    /--------------\
   /   Unit Tests   \  ← ~70% — All business logic, financial calculations, validators
  /------------------\
```

---

## 1. Unit Tests (pytest — `/apps/api/tests/unit/`)

### What gets unit tested
- All financial calculations (interest, penalties, progress percentages)
- All Pydantic validators (password complexity, phone format, amount minimums)
- All business rule enforcement (KYC gate, minimum balance, minimum duration)
- All OTP generation and validation logic
- All idempotency key handling
- All fraud detection rule evaluations
- JWT token generation and validation

### Financial Calculation Tests (CRITICAL)

```python
# tests/unit/test_financial_calculations.py

class TestInterestCalculation:
    def test_term_deposit_2_percent_annual(self):
        # 200,000 XAF × 2.0% = 4,000 XAF interest
        principal = 20000000  # BIGINT: 200,000 XAF in centimes
        rate = Decimal('0.02')
        result = calculate_annual_interest(principal, rate)
        assert result == 400000  # 4,000 XAF — exact BIGINT

    def test_no_float_in_interest_calculation(self):
        # Ensure we never produce a float
        result = calculate_annual_interest(20000000, Decimal('0.02'))
        assert isinstance(result, int)

    def test_interest_rounds_down_not_up(self):
        # 100,001 XAF × 2% = 2,000.02 — must round DOWN (floor)
        result = calculate_annual_interest(10000100, Decimal('0.02'))
        assert result == 200002  # floor, not round

class TestEarlyWithdrawalPenalty:
    def test_project_account_penalty(self):
        # Balance 50,000 XAF, penalty_rate 5% = 2,500 XAF penalty
        balance = 5000000
        penalty_rate = Decimal('0.05')
        net, penalty = calculate_early_withdrawal(balance, penalty_rate)
        assert penalty == 250000
        assert net == 4750000
        assert net + penalty == balance  # must balance exactly

    def test_term_deposit_early_break(self):
        # 200,000 XAF, 1.5% penalty = 3,000 XAF
        principal = 20000000
        penalty_rate = Decimal('0.015')
        _, penalty = calculate_early_withdrawal(principal, penalty_rate)
        assert penalty == 300000

    def test_penalty_never_exceeds_balance(self):
        balance = 100000  # 1,000 XAF
        penalty_rate = Decimal('0.99')  # extreme case
        net, penalty = calculate_early_withdrawal(balance, penalty_rate)
        assert net >= 0
        assert penalty <= balance

class TestProgressCalculation:
    def test_zero_progress(self):
        assert calculate_progress(0, 1000000) == 0

    def test_fifty_percent(self):
        assert calculate_progress(500000, 1000000) == 50

    def test_over_100_percent(self):
        # Overfunded vault — cap at 100
        assert calculate_progress(1500000, 1000000) == 100

    def test_milestone_triggers(self):
        milestones = get_triggered_milestones(old_pct=24, new_pct=26)
        assert 25 in milestones
        milestones = get_triggered_milestones(old_pct=74, new_pct=101)
        assert 75 in milestones
        assert 100 in milestones

class TestMinimumBalance:
    def test_standard_account_min_balance_enforcement(self):
        with pytest.raises(InsufficientBalanceError):
            validate_withdrawal(balance=100000, amount=99100)  # would leave 900 < 1000 XAF min

    def test_term_deposit_minimum_opening(self):
        with pytest.raises(MinimumDepositError):
            validate_term_deposit_opening(amount=19999999)  # < 200,000 XAF
```

### Auth + Security Unit Tests

```python
class TestOTP:
    def test_otp_is_6_digits(self):
        otp = generate_otp()
        assert len(str(otp)) == 6

    def test_otp_single_use(self):
        # After validation, OTP deleted from Redis
        ...

    def test_otp_expires_after_5_minutes(self):
        ...

class TestPasswordValidation:
    def test_min_10_chars(self):
        assert not is_valid_password("Short1!")

    def test_requires_uppercase(self):
        assert not is_valid_password("alllowercase1!")

    def test_requires_number(self):
        assert not is_valid_password("NoNumbers!!")

    def test_requires_special_char(self):
        assert not is_valid_password("NoSpecial123")

    def test_valid_password(self):
        assert is_valid_password("ValidPass1!")
```

---

## 2. Integration Tests (pytest — `/apps/api/tests/integration/`)

### What gets integration tested
- Full request → response cycle for each endpoint
- Database state changes after operations
- Redis state after OTP/session operations
- Module boundary interactions
- Webhook handler end-to-end processing

### External Service Mocking

**Always mock in tests — never call real provider APIs:**

```python
# conftest.py
@pytest.fixture
def mock_mtn_momo(mocker):
    return mocker.patch('modules.transactions.service.mtn_momo_client', MockMTNMoMoClient())

@pytest.fixture
def mock_sendgrid(mocker):
    return mocker.patch('modules.notifications.service.sendgrid_client', MockSendGridClient())

@pytest.fixture
def mock_s3(mocker):
    return mocker.patch('modules.kyc.service.s3_client', MockS3Client())
```

### Key Integration Test Scenarios

```python
class TestDepositFlow:
    async def test_mtn_momo_deposit_success(self, client, mock_mtn_momo, db):
        # 1. Initiate deposit
        # 2. Assert transaction created with status=pending
        # 3. Simulate MTN callback
        # 4. Assert status=success
        # 5. Assert balance incremented by exact amount (BIGINT)
        # 6. Assert audit_log entry created
        ...

    async def test_mtn_momo_deposit_timeout(self, client, mock_mtn_momo, db):
        # Assert status=failed after 120s timeout
        # Assert balance NOT changed
        ...

    async def test_idempotency_duplicate_rejected(self, client, db):
        # Same idempotency_key used twice
        # Second request returns 409 Conflict
        # Only one transaction created in DB
        ...

class TestKYCGate:
    async def test_transaction_blocked_before_kyc(self, client, db):
        user = create_user(kyc_status='pending')
        response = await client.post('/api/v1/transactions/deposit', ...)
        assert response.status_code == 403
        assert response.json()['error']['code'] == 'KYC_REQUIRED'

class TestAtomicTransfer:
    async def test_transfer_atomicity(self, client, db):
        # If credit succeeds but debit fails — both must roll back
        # Assert source balance unchanged
        # Assert destination balance unchanged
        ...
```

---

## 3. End-to-End Tests (Playwright — `/apps/web/tests/e2e/`)

**Run against staging environment only. Never against production.**

### Critical Journeys (must all pass before any release)

```
[ ] UC-001: Full user registration → OTP → KYC upload → admin approval → first login
[ ] UC-002: Create Project Account → deposit → progress bar updates → milestone notification
[ ] UC-003: Deposit via MTN MoMo → USSD approval → balance updates in real-time
[ ] UC-004: Admin KYC verification → approve → user activated
[ ] Freeze virtual card → attempt transaction → transaction blocked
[ ] Term deposit: open → countdown visible → early break penalty shown correctly
[ ] Transfer to another user → PIN confirmation → both balances updated
```

---

## 4. Load Tests (Locust — `/infrastructure/load-tests/`)

**Run before each major release against a staging clone.**

```python
# locustfile.py targets

class TerahBankUser(HttpUser):
    # Scenario 1: 500 concurrent users — dashboard load
    # Target: P95 read < 300ms

    # Scenario 2: 100 concurrent deposits
    # Target: P95 write < 600ms, zero failed transactions

    # Scenario 3: MoMo webhook flood (10x expected peak — payday simulation)
    # Target: All callbacks processed, zero dropped
```

---

## Test Data & Fixtures

```python
# tests/fixtures/users.py
def make_approved_user(**kwargs):
    return User(kyc_status='approved', account_status='active', **kwargs)

def make_pending_kyc_user(**kwargs):
    return User(kyc_status='pending', **kwargs)

# tests/fixtures/accounts.py
def make_standard_account(balance=500000, **kwargs):
    # balance in BIGINT — default 5,000 XAF
    return Account(account_type='standard', balance=balance, status='active', **kwargs)

def make_project_account(target=10000000, current=2500000, **kwargs):
    # 25% progress — should trigger milestone notification
    return Account(account_type='project', target_amount=target, balance=current, **kwargs)
```

---

## CI/CD Test Enforcement (GitHub Actions)

```yaml
# .github/workflows/test.yml
on: [push, pull_request]

jobs:
  test:
    steps:
      - run: pytest tests/unit/ --cov=modules --cov-fail-under=80
      - run: pytest tests/integration/ --cov-fail-under=70
      - run: ruff check .          # linting
      - run: mypy modules/          # type checking
```

**Rules:**
- Unit test coverage < 80% → PR blocked
- Integration test coverage < 70% → PR blocked
- Any financial calculation test failure → PR blocked regardless of coverage
- Type errors → PR blocked

---

## Financial Test Invariants (must hold in every test)

```python
# Invariants that must ALWAYS be true — add as assertions at test teardown

def assert_financial_invariants(db):
    # 1. Sum of all account balances must equal sum of all successful credit transactions
    #    minus sum of all successful debit transactions
    # 2. No account balance below minimum (standard: 1,000 XAF)
    # 3. No FLOAT values in any money column
    # 4. Every successful transaction has an audit_log entry
    # 5. No transaction in 'processing' state older than 10 minutes (stuck payment detector)
```
