"""
Unit tests for Milestone 3.3 — Orange Money Integration.

Covers:
  - HMAC-SHA256 signature validation (valid, invalid, empty secret, empty signature,
    uppercase hex, tampered body)
  - TransactionService.deposit() — orange_money channel creates pending txn + enqueues
    Orange job, 409 duplicate key, 503 feature disabled
  - TransactionService.withdraw() — creates pending txn, debits account, enqueues job;
    409 duplicate key, 404 unknown account, 422 locked account, 503 feature disabled
  - handle_orange_webhook() — SUCCESSFUL deposit credits account, SUCCESSFUL withdrawal
    marks success (no balance change), FAILED deposit marks failed, FAILED withdrawal
    compensating credit, PENDING no-op, duplicate ignored, unknown order_id silent
  - Orange deposit timeout handler — resolves SUCCESSFUL, resolves FAILED, skips
    already-resolved txn
  - Orange withdrawal timeout handler — resolves SUCCESSFUL, FAILED triggers compensating
    credit

All DB, Redis, BullMQ, and Orange Money HTTP calls are mocked.
"""

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.orange_money import validate_orange_callback_signature
from modules.transactions.service import TransactionService
from modules.transactions.schemas import DepositRequest, WithdrawRequest

_SVC  = "modules.transactions.service"
_PROC = "modules.jobs.orange_payment_processor"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_user(user_id=None, phone="+237690000001"):
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.kyc_status = "approved"
    u.phone = phone
    return u


def _make_account(account_id=None, user_id=None, balance=5_000_000, status="active"):
    a = MagicMock()
    a.id = account_id or uuid.uuid4()
    a.user_id = user_id or uuid.uuid4()
    a.balance = balance
    a.status = status
    return a


def _make_txn(txn_id=None, status="pending", amount=100_000, channel="orange_money",
              txn_type="deposit"):
    t = MagicMock()
    t.id = txn_id or uuid.uuid4()
    t.reference = f"TXN-20260422-{uuid.uuid4().hex[:8].upper()}"
    t.status = status
    t.amount = amount
    t.channel = channel
    t.transaction_type = txn_type
    t.credit_account_id = uuid.uuid4()
    t.debit_account_id  = uuid.uuid4()
    t.initiated_by = uuid.uuid4()
    t.external_reference = None
    t.created_at = datetime.now(tz=timezone.utc)
    t.completed_at = None
    return t


def _make_service():
    db = AsyncMock()
    db.commit = AsyncMock()
    svc = TransactionService(db)
    svc._repo = AsyncMock()
    return svc, db


def _make_redis():
    r = AsyncMock()
    r.get    = AsyncMock(return_value=None)
    r.setex  = AsyncMock()
    r.delete = AsyncMock()
    return r


def _hmac_sig(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ─── HMAC signature validation ────────────────────────────────────────────────

class TestValidateOrangeCallbackSignature:
    def test_valid_signature(self):
        secret = "orange-secret"
        body = b'{"status":"SUCCESSFUL"}'
        sig = _hmac_sig(body, secret)
        assert validate_orange_callback_signature(body, sig, secret) is True

    def test_invalid_signature(self):
        secret = "orange-secret"
        body = b'{"status":"SUCCESSFUL"}'
        assert validate_orange_callback_signature(body, "bad-sig", secret) is False

    def test_empty_secret_returns_false(self):
        body = b'{"status":"SUCCESSFUL"}'
        sig = _hmac_sig(body, "any")
        assert validate_orange_callback_signature(body, sig, "") is False

    def test_empty_signature_returns_false(self):
        body = b'{"status":"SUCCESSFUL"}'
        assert validate_orange_callback_signature(body, "", "secret") is False

    def test_case_insensitive_hex(self):
        secret = "orange-secret"
        body = b'{"status":"FAILED"}'
        sig = _hmac_sig(body, secret).upper()
        assert validate_orange_callback_signature(body, sig, secret) is True

    def test_tampered_body_rejected(self):
        secret = "orange-secret"
        original = b'{"status":"SUCCESSFUL","amount":5000}'
        tampered = b'{"status":"SUCCESSFUL","amount":9999}'
        sig = _hmac_sig(original, secret)
        assert validate_orange_callback_signature(tampered, sig, secret) is False


# ─── TransactionService.deposit() — orange_money channel ─────────────────────

class TestOrangeDepositService:
    @pytest.mark.asyncio
    async def test_deposit_orange_creates_pending_txn_and_enqueues_job(self):
        user    = _make_user()
        account = _make_account(user_id=user.id)
        txn     = _make_txn(channel="orange_money")
        svc, db = _make_service()

        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)
        svc._repo.create = AsyncMock(return_value=txn)

        redis = _make_redis()

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
            patch(f"{_SVC}._enqueue_orange_payment_job", new_callable=AsyncMock) as mock_enqueue,
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_ORANGE_MONEY = True

            acct_repo = AsyncMock()
            acct_repo.get_user_account = AsyncMock(return_value=account)
            MockAcctRepo.return_value = acct_repo

            payload = DepositRequest(account_id=str(account.id), amount=100_000, channel="orange_money")
            result = await svc.deposit(payload, user, "idem-orange-001")

        assert result.success is True
        assert result.data["status"] == "pending"
        assert result.data["channel"] == "orange_money"
        mock_enqueue.assert_called_once()
        call_kwargs = mock_enqueue.call_args.kwargs
        assert call_kwargs["phone_e164"] == user.phone
        assert call_kwargs["amount_units"] == 100_000
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_deposit_orange_returns_503_when_feature_disabled(self):
        from fastapi import HTTPException

        user = _make_user()
        svc, _ = _make_service()

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_ORANGE_MONEY = False

            payload = DepositRequest(account_id=str(uuid.uuid4()), amount=100_000, channel="orange_money")
            with pytest.raises(HTTPException) as exc_info:
                await svc.deposit(payload, user, "key-1")

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["code"] == "FEATURE_DISABLED"

    @pytest.mark.asyncio
    async def test_deposit_orange_returns_409_on_duplicate_key(self):
        from fastapi import HTTPException

        user = _make_user()
        existing = _make_txn(channel="orange_money")
        svc, _ = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=existing)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_ORANGE_MONEY = True

            payload = DepositRequest(account_id=str(uuid.uuid4()), amount=100_000, channel="orange_money")
            with pytest.raises(HTTPException) as exc_info:
                await svc.deposit(payload, user, "dup-key")

        assert exc_info.value.status_code == 409


# ─── TransactionService.withdraw() ───────────────────────────────────────────

class TestWithdrawService:
    @pytest.mark.asyncio
    async def test_withdraw_creates_pending_txn_debits_account_enqueues_job(self):
        user    = _make_user()
        account = _make_account(user_id=user.id)
        txn     = _make_txn(channel="orange_money", txn_type="withdrawal")
        svc, db = _make_service()

        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)
        svc._repo.create = AsyncMock(return_value=txn)

        redis = _make_redis()
        redis.get = AsyncMock(return_value=str(user.id))  # valid pin_token

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
            patch(f"{_SVC}._enqueue_orange_withdrawal_job", new_callable=AsyncMock) as mock_enqueue,
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_ORANGE_MONEY = True

            acct_repo = AsyncMock()
            acct_repo.get_user_account = AsyncMock(return_value=account)
            MockAcctRepo.return_value = acct_repo

            acct_svc = AsyncMock()
            acct_svc.apply_balance_delta = AsyncMock()
            MockAcctSvc.return_value = acct_svc

            payload = WithdrawRequest(
                account_id=str(account.id),
                amount=100_000,
                channel="orange_money",
                destination_phone="+237690000002",
                pin_token="valid-token",
            )
            result = await svc.withdraw(payload, user, "idem-withdraw-001")

        assert result.success is True
        assert result.data["status"] == "pending"
        assert result.data["channel"] == "orange_money"
        acct_svc.apply_balance_delta.assert_called_once_with(account.id, -100_000)
        mock_enqueue.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_withdraw_returns_503_when_feature_disabled(self):
        from fastapi import HTTPException

        user = _make_user()
        svc, _ = _make_service()
        redis = _make_redis()
        redis.get = AsyncMock(return_value=str(user.id))

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis),
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_ORANGE_MONEY = False

            payload = WithdrawRequest(
                account_id=str(uuid.uuid4()),
                amount=50_000,
                channel="orange_money",
                destination_phone="+237690000002",
                pin_token="valid-token",
            )
            with pytest.raises(HTTPException) as exc_info:
                await svc.withdraw(payload, user, "key-1")

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_withdraw_returns_409_on_duplicate_key(self):
        from fastapi import HTTPException

        user = _make_user()
        existing = _make_txn(channel="orange_money", txn_type="withdrawal")
        svc, _ = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=existing)

        redis = _make_redis()
        redis.get = AsyncMock(return_value=str(user.id))

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis),
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_ORANGE_MONEY = True

            payload = WithdrawRequest(
                account_id=str(uuid.uuid4()),
                amount=50_000,
                channel="orange_money",
                destination_phone="+237690000002",
                pin_token="valid-token",
            )
            with pytest.raises(HTTPException) as exc_info:
                await svc.withdraw(payload, user, "dup-key")

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_withdraw_returns_404_for_unknown_account(self):
        from fastapi import HTTPException

        user = _make_user()
        svc, _ = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)

        redis = _make_redis()
        redis.get = AsyncMock(return_value=str(user.id))

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_ORANGE_MONEY = True

            acct_repo = AsyncMock()
            acct_repo.get_user_account = AsyncMock(return_value=None)
            MockAcctRepo.return_value = acct_repo

            payload = WithdrawRequest(
                account_id=str(uuid.uuid4()),
                amount=50_000,
                channel="orange_money",
                destination_phone="+237690000002",
                pin_token="valid-token",
            )
            with pytest.raises(HTTPException) as exc_info:
                await svc.withdraw(payload, user, "new-key")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_withdraw_returns_422_for_locked_account(self):
        from fastapi import HTTPException

        user    = _make_user()
        account = _make_account(user_id=user.id, status="frozen")
        svc, _  = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)

        redis = _make_redis()
        redis.get = AsyncMock(return_value=str(user.id))

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_ORANGE_MONEY = True

            acct_repo = AsyncMock()
            acct_repo.get_user_account = AsyncMock(return_value=account)
            MockAcctRepo.return_value = acct_repo

            payload = WithdrawRequest(
                account_id=str(account.id),
                amount=50_000,
                channel="orange_money",
                destination_phone="+237690000002",
                pin_token="valid-token",
            )
            with pytest.raises(HTTPException) as exc_info:
                await svc.withdraw(payload, user, "key-locked")

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "ACCOUNT_LOCKED"


# ─── handle_orange_webhook() — state machine ─────────────────────────────────

class TestHandleOrangeWebhook:
    @pytest.mark.asyncio
    async def test_successful_deposit_credits_account(self):
        txn = _make_txn(status="processing", channel="orange_money", txn_type="deposit")
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=txn)
        svc._repo.update = AsyncMock(return_value=txn)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            acct_svc = AsyncMock()
            acct_svc.apply_balance_delta = AsyncMock()
            MockAcctSvc.return_value = acct_svc

            await svc.handle_orange_webhook("TXN-20260422-ABCD1234", {"status": "SUCCESSFUL"})

        acct_svc.apply_balance_delta.assert_called_once_with(txn.credit_account_id, txn.amount)
        update_kwargs = svc._repo.update.call_args.kwargs
        assert update_kwargs["status"] == "success"
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_withdrawal_marks_success_no_balance_change(self):
        """Withdrawal success: account already debited, no additional balance change."""
        txn = _make_txn(status="processing", channel="orange_money", txn_type="withdrawal")
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=txn)
        svc._repo.update = AsyncMock(return_value=txn)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            acct_svc = AsyncMock()
            acct_svc.apply_balance_delta = AsyncMock()
            MockAcctSvc.return_value = acct_svc

            await svc.handle_orange_webhook("TXN-20260422-WXYZ5678", {"status": "SUCCESSFUL"})

        # No balance change on successful withdrawal — account already debited
        acct_svc.apply_balance_delta.assert_not_called()
        update_kwargs = svc._repo.update.call_args.kwargs
        assert update_kwargs["status"] == "success"
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_deposit_marks_failed(self):
        txn = _make_txn(status="processing", channel="orange_money", txn_type="deposit")
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=txn)
        svc._repo.update = AsyncMock(return_value=txn)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            acct_svc = AsyncMock()
            acct_svc.apply_balance_delta = AsyncMock()
            MockAcctSvc.return_value = acct_svc

            await svc.handle_orange_webhook("TXN-20260422-FAIL", {"status": "FAILED"})

        # No balance change for failed deposit
        acct_svc.apply_balance_delta.assert_not_called()
        update_kwargs = svc._repo.update.call_args.kwargs
        assert update_kwargs["status"] == "failed"
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_withdrawal_issues_compensating_credit(self):
        """Failed withdrawal: compensating credit restores funds to debit account."""
        txn = _make_txn(status="processing", channel="orange_money", txn_type="withdrawal")
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=txn)
        svc._repo.update = AsyncMock(return_value=txn)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            acct_svc = AsyncMock()
            acct_svc.apply_balance_delta = AsyncMock()
            MockAcctSvc.return_value = acct_svc

            await svc.handle_orange_webhook("TXN-20260422-COMP", {"status": "FAILED"})

        # Compensating credit — restores amount to debit_account_id
        acct_svc.apply_balance_delta.assert_called_once_with(txn.debit_account_id, txn.amount)
        update_kwargs = svc._repo.update.call_args.kwargs
        assert update_kwargs["status"] == "failed"
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_pending_status_no_state_change(self):
        txn = _make_txn(status="processing", channel="orange_money")
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=txn)
        svc._repo.update = AsyncMock(return_value=txn)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountService"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            await svc.handle_orange_webhook("TXN-20260422-PEND", {"status": "PENDING"})

        svc._repo.update.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_callback_ignored(self):
        txn = _make_txn(status="success", channel="orange_money")
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=txn)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            acct_svc = AsyncMock()
            MockAcctSvc.return_value = acct_svc

            await svc.handle_orange_webhook("TXN-20260422-DUP", {"status": "SUCCESSFUL"})

        acct_svc.apply_balance_delta.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancelled_status_treated_as_failed(self):
        txn = _make_txn(status="processing", channel="orange_money", txn_type="deposit")
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=txn)
        svc._repo.update = AsyncMock(return_value=txn)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            acct_svc = AsyncMock()
            MockAcctSvc.return_value = acct_svc
            await svc.handle_orange_webhook("TXN-20260422-CANC", {"status": "CANCELLED"})

        update_kwargs = svc._repo.update.call_args.kwargs
        assert update_kwargs["status"] == "failed"

    @pytest.mark.asyncio
    async def test_unknown_order_id_is_silent(self):
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=None)

        with patch(f"{_SVC}.get_redis_client", return_value=_make_redis()):
            await svc.handle_orange_webhook("UNKNOWN-ORDER", {"status": "SUCCESSFUL"})

        db.commit.assert_not_called()


# ─── Orange deposit timeout processor ────────────────────────────────────────

class TestOrangeDepositTimeoutProcessor:
    """
    Patch strategy (same as MTN MoMo tests):
    Lazy imports inside the function body → patch at source modules.
    OrangeMoneyClient is a top-level import → patch at _PROC.
    """

    def _job(self, txn_id, order_id):
        job = MagicMock()
        job.data = {"txn_id": str(txn_id), "order_id": order_id}
        return job

    def _mock_db(self):
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db.commit = AsyncMock()
        return mock_db

    @pytest.mark.asyncio
    async def test_timeout_resolves_successful_deposit(self):
        txn = _make_txn(status="processing", txn_type="deposit")
        job = self._job(txn.id, "TXN-20260422-TOUT1")
        mock_db = self._mock_db()

        repo = AsyncMock()
        repo.get_by_id_unchecked = AsyncMock(return_value=txn)
        repo.update = AsyncMock(return_value=txn)

        acct_svc = AsyncMock()
        acct_svc.apply_balance_delta = AsyncMock()

        client = AsyncMock()
        client.get_payment_status = AsyncMock(return_value="SUCCESSFUL")

        with (
            patch("core.database.AsyncSessionLocal", return_value=mock_db),
            patch("modules.transactions.repository.TransactionRepository", return_value=repo),
            patch("modules.accounts.service.AccountService", return_value=acct_svc),
            patch(f"{_PROC}.OrangeMoneyClient", return_value=client),
            patch("core.audit.write_audit_log", new_callable=AsyncMock),
        ):
            from modules.jobs.orange_payment_processor import process_orange_deposit_timeout_check
            await process_orange_deposit_timeout_check(job, "")

        acct_svc.apply_balance_delta.assert_called_once_with(txn.credit_account_id, txn.amount)
        assert repo.update.call_args.kwargs["status"] == "success"

    @pytest.mark.asyncio
    async def test_timeout_resolves_failed_deposit(self):
        txn = _make_txn(status="processing", txn_type="deposit")
        job = self._job(txn.id, "TXN-20260422-TOUT2")
        mock_db = self._mock_db()

        repo = AsyncMock()
        repo.get_by_id_unchecked = AsyncMock(return_value=txn)
        repo.update = AsyncMock(return_value=txn)

        acct_svc = AsyncMock()
        client = AsyncMock()
        client.get_payment_status = AsyncMock(return_value="FAILED")

        with (
            patch("core.database.AsyncSessionLocal", return_value=mock_db),
            patch("modules.transactions.repository.TransactionRepository", return_value=repo),
            patch("modules.accounts.service.AccountService", return_value=acct_svc),
            patch(f"{_PROC}.OrangeMoneyClient", return_value=client),
            patch("core.audit.write_audit_log", new_callable=AsyncMock),
        ):
            from modules.jobs.orange_payment_processor import process_orange_deposit_timeout_check
            await process_orange_deposit_timeout_check(job, "")

        acct_svc.apply_balance_delta.assert_not_called()
        assert repo.update.call_args.kwargs["status"] == "failed"

    @pytest.mark.asyncio
    async def test_timeout_skips_already_resolved_txn(self):
        txn = _make_txn(status="success")
        job = self._job(txn.id, "TXN-20260422-DONE")
        mock_db = self._mock_db()

        repo = AsyncMock()
        repo.get_by_id_unchecked = AsyncMock(return_value=txn)
        client = AsyncMock()

        with (
            patch("core.database.AsyncSessionLocal", return_value=mock_db),
            patch("modules.transactions.repository.TransactionRepository", return_value=repo),
            patch(f"{_PROC}.OrangeMoneyClient", return_value=client),
        ):
            from modules.jobs.orange_payment_processor import process_orange_deposit_timeout_check
            await process_orange_deposit_timeout_check(job, "")

        client.get_payment_status.assert_not_called()
        mock_db.commit.assert_not_called()


# ─── Orange withdrawal timeout processor ─────────────────────────────────────

class TestOrangeWithdrawalTimeoutProcessor:
    def _job(self, txn_id, order_id):
        job = MagicMock()
        job.data = {"txn_id": str(txn_id), "order_id": order_id}
        return job

    def _mock_db(self):
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db.commit = AsyncMock()
        return mock_db

    @pytest.mark.asyncio
    async def test_timeout_resolves_successful_withdrawal(self):
        txn = _make_txn(status="processing", txn_type="withdrawal")
        job = self._job(txn.id, "TXN-20260422-WTOUT1")
        mock_db = self._mock_db()

        repo = AsyncMock()
        repo.get_by_id_unchecked = AsyncMock(return_value=txn)
        repo.update = AsyncMock(return_value=txn)

        acct_svc = AsyncMock()
        acct_svc.apply_balance_delta = AsyncMock()

        client = AsyncMock()
        client.get_payment_status = AsyncMock(return_value="SUCCESSFUL")

        with (
            patch("core.database.AsyncSessionLocal", return_value=mock_db),
            patch("modules.transactions.repository.TransactionRepository", return_value=repo),
            patch("modules.accounts.service.AccountService", return_value=acct_svc),
            patch(f"{_PROC}.OrangeMoneyClient", return_value=client),
            patch("core.audit.write_audit_log", new_callable=AsyncMock),
        ):
            from modules.jobs.orange_payment_processor import process_orange_withdrawal_timeout_check
            await process_orange_withdrawal_timeout_check(job, "")

        # Success: no compensating credit
        acct_svc.apply_balance_delta.assert_not_called()
        assert repo.update.call_args.kwargs["status"] == "success"

    @pytest.mark.asyncio
    async def test_timeout_failed_withdrawal_issues_compensating_credit(self):
        txn = _make_txn(status="processing", txn_type="withdrawal")
        job = self._job(txn.id, "TXN-20260422-WTOUT2")
        mock_db = self._mock_db()

        repo = AsyncMock()
        repo.get_by_id_unchecked = AsyncMock(return_value=txn)
        repo.update = AsyncMock(return_value=txn)

        acct_svc = AsyncMock()
        acct_svc.apply_balance_delta = AsyncMock()

        client = AsyncMock()
        client.get_payment_status = AsyncMock(return_value="FAILED")

        with (
            patch("core.database.AsyncSessionLocal", return_value=mock_db),
            patch("modules.transactions.repository.TransactionRepository", return_value=repo),
            patch("modules.accounts.service.AccountService", return_value=acct_svc),
            patch(f"{_PROC}.OrangeMoneyClient", return_value=client),
            patch("core.audit.write_audit_log", new_callable=AsyncMock),
        ):
            from modules.jobs.orange_payment_processor import process_orange_withdrawal_timeout_check
            await process_orange_withdrawal_timeout_check(job, "")

        # Compensating credit issued
        acct_svc.apply_balance_delta.assert_called_once_with(txn.debit_account_id, txn.amount)
        assert repo.update.call_args.kwargs["status"] == "failed"

    @pytest.mark.asyncio
    async def test_timeout_treats_pending_as_failed_with_compensating_credit(self):
        txn = _make_txn(status="processing", txn_type="withdrawal")
        job = self._job(txn.id, "TXN-20260422-WPEND")
        mock_db = self._mock_db()

        repo = AsyncMock()
        repo.get_by_id_unchecked = AsyncMock(return_value=txn)
        repo.update = AsyncMock(return_value=txn)

        acct_svc = AsyncMock()
        acct_svc.apply_balance_delta = AsyncMock()

        client = AsyncMock()
        client.get_payment_status = AsyncMock(return_value="PENDING")

        with (
            patch("core.database.AsyncSessionLocal", return_value=mock_db),
            patch("modules.transactions.repository.TransactionRepository", return_value=repo),
            patch("modules.accounts.service.AccountService", return_value=acct_svc),
            patch(f"{_PROC}.OrangeMoneyClient", return_value=client),
            patch("core.audit.write_audit_log", new_callable=AsyncMock),
        ):
            from modules.jobs.orange_payment_processor import process_orange_withdrawal_timeout_check
            await process_orange_withdrawal_timeout_check(job, "")

        # Still PENDING after 125s → treated as failed
        acct_svc.apply_balance_delta.assert_called_once_with(txn.debit_account_id, txn.amount)
        assert repo.update.call_args.kwargs["status"] == "failed"
