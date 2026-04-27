"""
Unit tests for Milestone 3.1 — Internal Transfers.

Covers:
  - FR-034: Own-account transfer
  - FR-035: Cross-user transfer (by phone, by account_id, by account_number)
  - FR-036: PIN token validation (single-use, expired, wrong user)
  - Idempotency key enforcement (duplicate → 409)
  - Insufficient balance (422)
  - Self-transfer guard (422)
  - Transaction history list and get (FR-037)
  - Project milestone hook (FR-020) wired through transfer

All DB and Redis calls are mocked — no real DB or Redis required.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.transactions.service import TransactionService
from modules.transactions.schemas import TransferRequest

# ─── Module-level patch paths (all top-level imports in service.py) ───────────
_SVC = "modules.transactions.service"


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_user(user_id=None):
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.kyc_status = "approved"
    u.phone_number = "+237600000001"
    return u


def _make_account(
    account_id=None,
    user_id=None,
    account_type="standard",
    balance=5_000_000,
    status="active",
    account_number=None,
    target_amount=None,
):
    a = MagicMock()
    a.id = account_id or uuid.uuid4()
    a.user_id = user_id or uuid.uuid4()
    a.account_type = account_type
    a.balance = balance
    a.status = status
    a.account_number = account_number or f"STD{uuid.uuid4().hex[:12].upper()}"
    a.target_amount = target_amount
    a.penalty_rate = None
    a.maturity_date = None
    a.interest_rate = None
    return a


def _make_transaction(txn_id=None, status="success"):
    t = MagicMock()
    t.id = txn_id or uuid.uuid4()
    t.reference = "TXN-20260422-ABCD1234"
    t.transaction_type = "transfer"
    t.channel = "internal"
    t.amount = 1_000_000
    t.currency = "XAF"
    t.status = status
    t.debit_account_id = uuid.uuid4()
    t.credit_account_id = uuid.uuid4()
    t.initiated_by = uuid.uuid4()
    t.created_at = datetime.now(tz=timezone.utc)
    t.completed_at = datetime.now(tz=timezone.utc)
    t.idempotency_key = "key-abc"
    return t


def _make_transfer_payload(
    from_account_id=None,
    to_identifier=None,
    amount=500_000,
    pin_token="valid-token",
):
    return TransferRequest(
        from_account_id=from_account_id or str(uuid.uuid4()),
        to_identifier=to_identifier or str(uuid.uuid4()),
        amount=amount,
        pin_token=pin_token,
    )


def _make_service():
    db = AsyncMock()
    db.commit = AsyncMock()
    svc = TransactionService(db)
    svc._repo = AsyncMock()
    return svc


def _make_redis(user_id_str=None):
    """Build a mock Redis that returns user_id_str on .get()."""
    r = AsyncMock()
    r.get = AsyncMock(return_value=user_id_str)
    r.delete = AsyncMock()
    r.setex = AsyncMock()
    return r


# ─── PIN token tests (FR-036) ─────────────────────────────────────────────────


class TestConsumesPINToken:
    @pytest.mark.asyncio
    async def test_valid_token_consumed(self):
        """Valid pin_token is deleted after use."""
        user = _make_user()
        svc = _make_service()
        redis_mock = _make_redis(str(user.id))

        with patch(f"{_SVC}.get_redis_client", return_value=redis_mock):
            await svc._consume_pin_token("valid-token", user.id)

        redis_mock.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_token_raises_401(self):
        """Missing or expired pin_token raises 401."""
        from fastapi import HTTPException

        user = _make_user()
        svc = _make_service()
        redis_mock = _make_redis(None)  # key not found

        with patch(f"{_SVC}.get_redis_client", return_value=redis_mock):
            with pytest.raises(HTTPException) as exc_info:
                await svc._consume_pin_token("expired-token", user.id)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "INVALID_PIN_TOKEN"

    @pytest.mark.asyncio
    async def test_wrong_user_token_raises_401(self):
        """Token belonging to a different user raises 401."""
        from fastapi import HTTPException

        user = _make_user()
        svc = _make_service()
        redis_mock = _make_redis(str(uuid.uuid4()))  # different user's id

        with patch(f"{_SVC}.get_redis_client", return_value=redis_mock):
            with pytest.raises(HTTPException) as exc_info:
                await svc._consume_pin_token("other-user-token", user.id)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "INVALID_PIN_TOKEN"

    @pytest.mark.asyncio
    async def test_token_deleted_on_first_use(self):
        """Token is deleted (consumed) on successful validation."""
        user = _make_user()
        svc = _make_service()
        redis_mock = _make_redis(str(user.id))

        with patch(f"{_SVC}.get_redis_client", return_value=redis_mock):
            await svc._consume_pin_token("token-abc", user.id)

        redis_mock.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_not_reusable(self):
        """After deletion, the same token raises 401 on second use."""
        from fastapi import HTTPException

        user = _make_user()
        svc = _make_service()

        call_count = 0

        async def get_side(key):
            nonlocal call_count
            call_count += 1
            return str(user.id) if call_count == 1 else None

        redis_mock = AsyncMock()
        redis_mock.get = get_side
        redis_mock.delete = AsyncMock()

        with patch(f"{_SVC}.get_redis_client", return_value=redis_mock):
            await svc._consume_pin_token("token-abc", user.id)
            with pytest.raises(HTTPException) as exc_info:
                await svc._consume_pin_token("token-abc", user.id)

        assert exc_info.value.status_code == 401


# ─── Duplicate idempotency key (409) ─────────────────────────────────────────


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_duplicate_key_returns_409(self):
        """Second request with same Idempotency-Key returns 409."""
        from fastapi import HTTPException

        user = _make_user()
        svc = _make_service()
        existing_txn = _make_transaction()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=existing_txn)
        redis_mock = _make_redis(str(user.id))

        with patch(f"{_SVC}.get_redis_client", return_value=redis_mock):
            with pytest.raises(HTTPException) as exc_info:
                await svc.transfer(_make_transfer_payload(), user, "dup-key")

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["code"] == "DUPLICATE_IDEMPOTENCY_KEY"
        assert "transaction_id" in exc_info.value.detail["details"]

    @pytest.mark.asyncio
    async def test_duplicate_response_includes_existing_txn_id(self):
        """409 response body contains the existing transaction_id."""
        from fastapi import HTTPException

        user = _make_user()
        existing_txn = _make_transaction()
        svc = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=existing_txn)
        redis_mock = _make_redis(str(user.id))

        with patch(f"{_SVC}.get_redis_client", return_value=redis_mock):
            with pytest.raises(HTTPException) as exc_info:
                await svc.transfer(_make_transfer_payload(), user, "dup-key")

        assert str(existing_txn.id) in exc_info.value.detail["details"]["transaction_id"]


# ─── Account resolution / validation ─────────────────────────────────────────


class TestTransferValidation:
    @pytest.mark.asyncio
    async def test_invalid_from_account_id_raises_400(self):
        """Non-UUID from_account_id raises 400."""
        from fastapi import HTTPException

        user = _make_user()
        svc = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)
        redis_mock = _make_redis(str(user.id))

        with patch(f"{_SVC}.get_redis_client", return_value=redis_mock):
            payload = _make_transfer_payload(from_account_id="not-a-uuid")
            with pytest.raises(HTTPException) as exc_info:
                await svc.transfer(payload, user, "key-bad-id")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "INVALID_ACCOUNT_ID"

    @pytest.mark.asyncio
    async def test_source_account_not_owned_raises_404(self):
        """From-account not belonging to user raises 404."""
        from fastapi import HTTPException

        user = _make_user()
        svc = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)
        redis_mock = _make_redis(str(user.id))

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
        ):
            MockAcctRepo.return_value.get_user_account = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await svc.transfer(_make_transfer_payload(), user, "key-404")

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["code"] == "ACCOUNT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_locked_source_account_raises_422(self):
        """Locked source account raises 422."""
        from fastapi import HTTPException

        user = _make_user()
        locked_acct = _make_account(user_id=user.id, status="locked")
        svc = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)
        redis_mock = _make_redis(str(user.id))

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
        ):
            MockAcctRepo.return_value.get_user_account = AsyncMock(return_value=locked_acct)
            payload = _make_transfer_payload(from_account_id=str(locked_acct.id))
            with pytest.raises(HTTPException) as exc_info:
                await svc.transfer(payload, user, "key-locked")

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "ACCOUNT_LOCKED"

    @pytest.mark.asyncio
    async def test_self_transfer_raises_422(self):
        """Transferring to the same account raises 422."""
        from fastapi import HTTPException

        user = _make_user()
        acct = _make_account(user_id=user.id)
        svc = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)
        redis_mock = _make_redis(str(user.id))

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=acct)
            mock_repo.get_by_id = AsyncMock(return_value=acct)  # same account

            payload = _make_transfer_payload(
                from_account_id=str(acct.id),
                to_identifier=str(acct.id),
            )
            with pytest.raises(HTTPException) as exc_info:
                await svc.transfer(payload, user, "key-self")

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "SELF_TRANSFER"

    @pytest.mark.asyncio
    async def test_locked_destination_raises_422(self):
        """Locked destination account raises 422."""
        from fastapi import HTTPException

        user = _make_user()
        from_acct = _make_account(user_id=user.id, balance=5_000_000)
        to_acct = _make_account(status="locked")
        svc = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)
        redis_mock = _make_redis(str(user.id))

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_by_id = AsyncMock(return_value=to_acct)

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier=str(to_acct.id),
            )
            with pytest.raises(HTTPException) as exc_info:
                await svc.transfer(payload, user, "key-dest-locked")

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "ACCOUNT_LOCKED"


# ─── Recipient resolution (FR-035) ───────────────────────────────────────────


class TestResolveToAccount:
    @pytest.mark.asyncio
    async def test_phone_lookup_recipient_not_found_raises_404(self):
        """Phone number not matching any user raises 404."""
        from fastapi import HTTPException

        svc = _make_service()
        acct_repo_mock = AsyncMock()

        with patch(f"{_SVC}.AuthRepository") as MockAuth:
            MockAuth.return_value.get_by_phone = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await svc._resolve_to_account("+237600000999", acct_repo_mock)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["code"] == "RECIPIENT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_phone_lookup_no_standard_account_raises_404(self):
        """Recipient has no Standard Account → 404."""
        from fastapi import HTTPException

        svc = _make_service()
        recipient = _make_user()
        acct_repo_mock = AsyncMock()
        acct_repo_mock.get_standard_account_by_user = AsyncMock(return_value=None)

        with patch(f"{_SVC}.AuthRepository") as MockAuth:
            MockAuth.return_value.get_by_phone = AsyncMock(return_value=recipient)
            with pytest.raises(HTTPException) as exc_info:
                await svc._resolve_to_account("+237600000999", acct_repo_mock)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["code"] == "RECIPIENT_NO_ACCOUNT"

    @pytest.mark.asyncio
    async def test_phone_lookup_returns_standard_account(self):
        """Phone number resolves to recipient's Standard Account."""
        svc = _make_service()
        recipient = _make_user()
        std_account = _make_account(user_id=recipient.id)
        acct_repo_mock = AsyncMock()
        acct_repo_mock.get_standard_account_by_user = AsyncMock(return_value=std_account)

        with patch(f"{_SVC}.AuthRepository") as MockAuth:
            MockAuth.return_value.get_by_phone = AsyncMock(return_value=recipient)
            result = await svc._resolve_to_account("+237600000999", acct_repo_mock)

        assert result.id == std_account.id

    @pytest.mark.asyncio
    async def test_uuid_account_id_resolves_directly(self):
        """Valid UUID resolves via get_by_id."""
        svc = _make_service()
        target = _make_account()
        acct_repo_mock = AsyncMock()
        acct_repo_mock.get_by_id = AsyncMock(return_value=target)

        result = await svc._resolve_to_account(str(target.id), acct_repo_mock)
        assert result.id == target.id

    @pytest.mark.asyncio
    async def test_uuid_not_found_raises_404(self):
        """UUID that maps to no account raises 404."""
        from fastapi import HTTPException

        svc = _make_service()
        acct_repo_mock = AsyncMock()
        acct_repo_mock.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await svc._resolve_to_account(str(uuid.uuid4()), acct_repo_mock)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_account_number_resolves(self):
        """Non-UUID, non-phone string treated as account_number."""
        svc = _make_service()
        target = _make_account(account_number="STD1234567890AB")
        acct_repo_mock = AsyncMock()
        acct_repo_mock.get_by_account_number = AsyncMock(return_value=target)

        result = await svc._resolve_to_account("STD1234567890AB", acct_repo_mock)
        assert result.id == target.id

    @pytest.mark.asyncio
    async def test_unknown_account_number_raises_404(self):
        """Account number not found raises 404."""
        from fastapi import HTTPException

        svc = _make_service()
        acct_repo_mock = AsyncMock()
        acct_repo_mock.get_by_account_number = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await svc._resolve_to_account("UNKNOWN123", acct_repo_mock)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_closed_account_by_uuid_raises_404(self):
        """Closed account found by UUID raises 404."""
        from fastapi import HTTPException

        svc = _make_service()
        closed_acct = _make_account(status="closed")
        acct_repo_mock = AsyncMock()
        acct_repo_mock.get_by_id = AsyncMock(return_value=closed_acct)

        with pytest.raises(HTTPException) as exc_info:
            await svc._resolve_to_account(str(closed_acct.id), acct_repo_mock)

        assert exc_info.value.status_code == 404


# ─── Happy path — own-account transfer (FR-034) ───────────────────────────────


def _setup_happy_path(user, from_acct, to_acct, svc, amount=500_000):
    """Return patchers for a successful own-account transfer."""
    svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)
    txn = _make_transaction()
    txn.debit_account_id = from_acct.id
    txn.credit_account_id = to_acct.id
    txn.amount = amount
    txn.status = "success"
    svc._repo.create = AsyncMock(return_value=txn)
    svc._repo.update = AsyncMock(return_value=txn)

    updated_to = _make_account(account_id=to_acct.id, user_id=to_acct.user_id,
                               account_type=to_acct.account_type, balance=to_acct.balance + amount)

    redis_mock = _make_redis(str(user.id))

    return txn, updated_to, redis_mock


class TestOwnAccountTransfer:
    @pytest.mark.asyncio
    async def test_own_account_transfer_success(self):
        """FR-034: Standard → Project transfer returns success."""
        user = _make_user()
        from_acct = _make_account(user_id=user.id, account_type="standard", balance=5_000_000)
        to_acct = _make_account(user_id=user.id, account_type="project", balance=0)
        svc = _make_service()

        txn, updated_to, redis_mock = _setup_happy_path(user, from_acct, to_acct, svc)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.notify_project_milestones"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_by_id = AsyncMock(return_value=to_acct)
            MockAcctSvc.return_value.apply_balance_delta = AsyncMock(
                side_effect=[from_acct, updated_to]
            )

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier=str(to_acct.id),
                amount=500_000,
            )
            result = await svc.transfer(payload, user, "key-success-own")

        assert result.success is True
        assert result.data["status"] == "success"
        assert result.data["amount"] == 500_000

    @pytest.mark.asyncio
    async def test_transfer_commits_db_exactly_once(self):
        """Successful transfer calls db.commit() exactly once."""
        user = _make_user()
        from_acct = _make_account(user_id=user.id, balance=5_000_000)
        to_acct = _make_account(user_id=user.id, balance=0)
        svc = _make_service()

        txn, updated_to, redis_mock = _setup_happy_path(user, from_acct, to_acct, svc)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.notify_project_milestones"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_by_id = AsyncMock(return_value=to_acct)
            MockAcctSvc.return_value.apply_balance_delta = AsyncMock(
                side_effect=[from_acct, updated_to]
            )

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier=str(to_acct.id),
            )
            await svc.transfer(payload, user, "key-commit")

        svc.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_insufficient_balance_raises_422(self):
        """apply_balance_delta raises 422 when balance insufficient."""
        from fastapi import HTTPException

        user = _make_user()
        from_acct = _make_account(user_id=user.id, balance=100_000)
        to_acct = _make_account(user_id=user.id, balance=0)
        svc = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)
        svc._repo.create = AsyncMock(return_value=_make_transaction())
        redis_mock = _make_redis(str(user.id))

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_by_id = AsyncMock(return_value=to_acct)
            MockAcctSvc.return_value.apply_balance_delta = AsyncMock(
                side_effect=HTTPException(
                    status_code=422,
                    detail={"code": "INSUFFICIENT_BALANCE", "message": "Insufficient balance."},
                )
            )

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier=str(to_acct.id),
                amount=5_000_000,
            )
            with pytest.raises(HTTPException) as exc_info:
                await svc.transfer(payload, user, "key-insuf")

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "INSUFFICIENT_BALANCE"

    @pytest.mark.asyncio
    async def test_transfer_result_contains_both_account_ids(self):
        """Response data includes from_account_id and to_account_id."""
        user = _make_user()
        from_acct = _make_account(user_id=user.id, balance=5_000_000)
        to_acct = _make_account(user_id=user.id, balance=0)
        svc = _make_service()

        txn, updated_to, redis_mock = _setup_happy_path(user, from_acct, to_acct, svc)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.notify_project_milestones"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_by_id = AsyncMock(return_value=to_acct)
            MockAcctSvc.return_value.apply_balance_delta = AsyncMock(
                side_effect=[from_acct, updated_to]
            )

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier=str(to_acct.id),
                amount=500_000,
            )
            result = await svc.transfer(payload, user, "key-ids")

        assert result.data["from_account_id"] == str(from_acct.id)
        assert result.data["to_account_id"] == str(to_acct.id)

    @pytest.mark.asyncio
    async def test_transfer_stores_idempotency_key_in_redis(self):
        """On success, idempotency key is cached in Redis."""
        user = _make_user()
        from_acct = _make_account(user_id=user.id, balance=5_000_000)
        to_acct = _make_account(user_id=user.id, balance=0)
        svc = _make_service()

        txn, updated_to, redis_mock = _setup_happy_path(user, from_acct, to_acct, svc)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.notify_project_milestones"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_by_id = AsyncMock(return_value=to_acct)
            MockAcctSvc.return_value.apply_balance_delta = AsyncMock(
                side_effect=[from_acct, updated_to]
            )

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier=str(to_acct.id),
            )
            await svc.transfer(payload, user, "key-idempotency")

        # setex should be called at least once (for idempotency key)
        assert redis_mock.setex.call_count >= 1


# ─── Cross-user transfer (FR-035) ────────────────────────────────────────────


class TestCrossUserTransfer:
    @pytest.mark.asyncio
    async def test_cross_user_by_phone_success(self):
        """FR-035: Transfer to another user by phone number."""
        sender = _make_user()
        recipient = _make_user()
        from_acct = _make_account(user_id=sender.id, balance=5_000_000)
        to_acct = _make_account(user_id=recipient.id)
        svc = _make_service()

        txn, updated_to, redis_mock = _setup_happy_path(sender, from_acct, to_acct, svc)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.AuthRepository") as MockAuthRepo,
            patch(f"{_SVC}.notify_project_milestones"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_standard_account_by_user = AsyncMock(return_value=to_acct)
            MockAuthRepo.return_value.get_by_phone = AsyncMock(return_value=recipient)
            MockAcctSvc.return_value.apply_balance_delta = AsyncMock(
                side_effect=[from_acct, updated_to]
            )

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier=recipient.phone_number,
                amount=500_000,
            )
            result = await svc.transfer(payload, sender, "key-cross-phone")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_cross_user_by_account_id_success(self):
        """FR-035: Transfer to another user's account by account_id."""
        sender = _make_user()
        from_acct = _make_account(user_id=sender.id, balance=5_000_000)
        to_acct = _make_account(user_id=uuid.uuid4())  # different user
        svc = _make_service()

        txn, updated_to, redis_mock = _setup_happy_path(sender, from_acct, to_acct, svc)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.notify_project_milestones"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_by_id = AsyncMock(return_value=to_acct)
            MockAcctSvc.return_value.apply_balance_delta = AsyncMock(
                side_effect=[from_acct, updated_to]
            )

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier=str(to_acct.id),
                amount=500_000,
            )
            result = await svc.transfer(payload, sender, "key-cross-id")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_cross_user_by_account_number_success(self):
        """FR-035: Transfer to another user's account by account_number."""
        sender = _make_user()
        from_acct = _make_account(user_id=sender.id, balance=5_000_000)
        to_acct = _make_account(user_id=uuid.uuid4(), account_number="PRJ1234567890AB")
        svc = _make_service()

        txn, updated_to, redis_mock = _setup_happy_path(sender, from_acct, to_acct, svc)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.notify_project_milestones"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_by_account_number = AsyncMock(return_value=to_acct)
            MockAcctSvc.return_value.apply_balance_delta = AsyncMock(
                side_effect=[from_acct, updated_to]
            )

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier="PRJ1234567890AB",
                amount=500_000,
            )
            result = await svc.transfer(payload, sender, "key-cross-num")

        assert result.success is True


# ─── Project milestone hook (FR-020) via transfer ────────────────────────────


class TestProjectMilestoneOnTransfer:
    @pytest.mark.asyncio
    async def test_milestone_notify_called_after_credit(self):
        """notify_project_milestones is called with old and new balance."""
        user = _make_user()
        from_acct = _make_account(user_id=user.id, balance=5_000_000)
        to_acct = _make_account(
            user_id=user.id, account_type="project", balance=0, target_amount=2_000_000
        )
        svc = _make_service()

        txn, updated_to, redis_mock = _setup_happy_path(user, from_acct, to_acct, svc, amount=1_000_000)
        updated_to.balance = 1_000_000

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.notify_project_milestones") as mock_notify,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_by_id = AsyncMock(return_value=to_acct)
            MockAcctSvc.return_value.apply_balance_delta = AsyncMock(
                side_effect=[from_acct, updated_to]
            )

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier=str(to_acct.id),
                amount=1_000_000,
            )
            await svc.transfer(payload, user, "key-milestone")

        mock_notify.assert_called_once()
        args = mock_notify.call_args[0]
        assert args[1] is to_acct     # account arg
        assert args[2] == 0            # old_balance
        assert args[3] == 1_000_000    # new_balance

    @pytest.mark.asyncio
    async def test_milestone_notify_always_called(self):
        """notify_project_milestones is called even for non-project accounts (it guards internally)."""
        user = _make_user()
        from_acct = _make_account(user_id=user.id, balance=5_000_000)
        to_acct = _make_account(user_id=user.id, account_type="standard", balance=0)
        svc = _make_service()

        txn, updated_to, redis_mock = _setup_happy_path(user, from_acct, to_acct, svc)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.notify_project_milestones") as mock_notify,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_by_id = AsyncMock(return_value=to_acct)
            MockAcctSvc.return_value.apply_balance_delta = AsyncMock(
                side_effect=[from_acct, updated_to]
            )

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier=str(to_acct.id),
            )
            await svc.transfer(payload, user, "key-milestone-std")

        mock_notify.assert_called_once()


# ─── Audit log ────────────────────────────────────────────────────────────────


class TestAuditLog:
    @pytest.mark.asyncio
    async def test_transfer_writes_audit_log_with_correct_action(self):
        """TRANSFER_INITIATED audit log is written before commit."""
        user = _make_user()
        from_acct = _make_account(user_id=user.id, balance=5_000_000)
        to_acct = _make_account(user_id=user.id, balance=0)
        svc = _make_service()

        txn, updated_to, redis_mock = _setup_happy_path(user, from_acct, to_acct, svc)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.notify_project_milestones"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock) as mock_audit,
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_by_id = AsyncMock(return_value=to_acct)
            MockAcctSvc.return_value.apply_balance_delta = AsyncMock(
                side_effect=[from_acct, updated_to]
            )

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier=str(to_acct.id),
            )
            await svc.transfer(payload, user, "key-audit")

        mock_audit.assert_called_once()
        _, kwargs = mock_audit.call_args
        assert kwargs["action"] == "TRANSFER_INITIATED"
        assert kwargs["actor_id"] == user.id

    @pytest.mark.asyncio
    async def test_audit_log_includes_amount_and_accounts(self):
        """Audit log metadata includes amount, from_account, to_account."""
        user = _make_user()
        from_acct = _make_account(user_id=user.id, balance=5_000_000)
        to_acct = _make_account(user_id=user.id, balance=0)
        svc = _make_service()

        txn, updated_to, redis_mock = _setup_happy_path(user, from_acct, to_acct, svc, amount=777_000)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis_mock),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.notify_project_milestones"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock) as mock_audit,
        ):
            mock_repo = MockAcctRepo.return_value
            mock_repo.get_user_account = AsyncMock(return_value=from_acct)
            mock_repo.get_by_id = AsyncMock(return_value=to_acct)
            MockAcctSvc.return_value.apply_balance_delta = AsyncMock(
                side_effect=[from_acct, updated_to]
            )

            payload = _make_transfer_payload(
                from_account_id=str(from_acct.id),
                to_identifier=str(to_acct.id),
                amount=777_000,
            )
            await svc.transfer(payload, user, "key-audit-meta")

        _, kwargs = mock_audit.call_args
        meta = kwargs["metadata"]
        assert meta["amount"] == 777_000
        assert "from_account" in meta
        assert "to_account" in meta


# ─── Transaction history (FR-037) ────────────────────────────────────────────


class TestListTransactions:
    @pytest.mark.asyncio
    async def test_list_returns_paginated_transactions(self):
        """list_transactions returns wrapped list with total."""
        user = _make_user()
        svc = _make_service()
        txns = [_make_transaction() for _ in range(3)]
        svc._repo.list_by_user = AsyncMock(return_value=(txns, 3))

        result = await svc.list_transactions(user_id=user.id, limit=10, offset=0)

        assert result.success is True
        assert result.data["total"] == 3
        assert len(result.data["transactions"]) == 3

    @pytest.mark.asyncio
    async def test_list_passes_all_filters_to_repo(self):
        """All query params forwarded to repo."""
        user = _make_user()
        svc = _make_service()
        svc._repo.list_by_user = AsyncMock(return_value=([], 0))

        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 12, 31, tzinfo=timezone.utc)

        await svc.list_transactions(
            user_id=user.id,
            transaction_type="transfer",
            txn_status="success",
            date_from=date_from,
            date_to=date_to,
            limit=5,
            offset=10,
        )

        svc._repo.list_by_user.assert_called_once_with(
            user_id=user.id,
            account_id=None,
            transaction_type="transfer",
            txn_status="success",
            date_from=date_from,
            date_to=date_to,
            limit=5,
            offset=10,
        )

    @pytest.mark.asyncio
    async def test_list_invalid_account_id_raises_400(self):
        """Malformed account_id filter raises 400."""
        from fastapi import HTTPException

        user = _make_user()
        svc = _make_service()

        with pytest.raises(HTTPException) as exc_info:
            await svc.list_transactions(user_id=user.id, account_id="not-a-uuid")

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_list_empty_returns_zero_total(self):
        """Empty result returns total=0 and empty list."""
        user = _make_user()
        svc = _make_service()
        svc._repo.list_by_user = AsyncMock(return_value=([], 0))

        result = await svc.list_transactions(user_id=user.id)

        assert result.data["total"] == 0
        assert result.data["transactions"] == []

    @pytest.mark.asyncio
    async def test_list_limit_and_offset_in_response(self):
        """limit and offset are reflected back in response data."""
        user = _make_user()
        svc = _make_service()
        svc._repo.list_by_user = AsyncMock(return_value=([], 100))

        result = await svc.list_transactions(user_id=user.id, limit=25, offset=50)

        assert result.data["limit"] == 25
        assert result.data["offset"] == 50


# ─── Get single transaction ────────────────────────────────────────────────────


class TestGetTransaction:
    @pytest.mark.asyncio
    async def test_get_existing_transaction(self):
        """Returns transaction data for an existing record."""
        user = _make_user()
        txn = _make_transaction()
        svc = _make_service()
        svc._repo.get_by_id = AsyncMock(return_value=txn)

        result = await svc.get_transaction(str(txn.id), user.id)

        assert result.success is True
        assert result.data["reference"] == txn.reference
        assert result.data["transaction_id"] == str(txn.id)

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises_404(self):
        """Transaction not found returns 404."""
        from fastapi import HTTPException

        user = _make_user()
        svc = _make_service()
        svc._repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_transaction(str(uuid.uuid4()), user.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["code"] == "TRANSACTION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_invalid_id_raises_400(self):
        """Non-UUID transaction_id raises 400."""
        from fastapi import HTTPException

        user = _make_user()
        svc = _make_service()

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_transaction("not-a-uuid", user.id)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "INVALID_TRANSACTION_ID"

    @pytest.mark.asyncio
    async def test_get_includes_all_required_fields(self):
        """Transaction data includes all TransactionData fields."""
        user = _make_user()
        txn = _make_transaction()
        svc = _make_service()
        svc._repo.get_by_id = AsyncMock(return_value=txn)

        result = await svc.get_transaction(str(txn.id), user.id)
        data = result.data

        assert "transaction_id" in data
        assert "reference" in data
        assert "transaction_type" in data
        assert "channel" in data
        assert "amount" in data
        assert "status" in data
        assert "created_at" in data


# ─── Reference format ────────────────────────────────────────────────────────


class TestGenerateReference:
    def test_reference_format(self):
        """Reference follows TXN-YYYYMMDD-XXXXXXXX format."""
        from modules.transactions.service import _generate_reference

        ref = _generate_reference()
        assert ref.startswith("TXN-")
        parts = ref.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8   # YYYYMMDD
        assert len(parts[2]) == 8   # 8 hex chars
        assert parts[2] == parts[2].upper()

    def test_references_are_unique(self):
        """100 references are all distinct."""
        from modules.transactions.service import _generate_reference

        refs = {_generate_reference() for _ in range(100)}
        assert len(refs) == 100

    def test_reference_date_part_is_current_date(self):
        """Date part of reference matches today."""
        from modules.transactions.service import _generate_reference

        today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
        ref = _generate_reference()
        assert ref.split("-")[1] == today
