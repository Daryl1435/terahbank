"""
Unit tests for Milestone 3.2 — MTN MoMo Integration.

Covers:
  - HMAC-SHA256 signature validation (valid, invalid, empty secret, empty signature)
  - TransactionService.deposit() — creates pending txn, enqueues job, 409 on duplicate key,
    404 on unknown account, 501 on unsupported channel, 503 on feature flag off
  - handle_mtn_webhook() — SUCCESSFUL (credits account), FAILED (marks failed),
    PENDING (no state change), duplicate callback ignored, txn not found silently ignored
  - Timeout handler — resolves SUCCESSFUL, resolves FAILED, skips already-resolved txn

All DB, Redis, BullMQ, and MTN HTTP calls are mocked — no real external services.
"""

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.mtn_momo import validate_mtn_callback_signature
from modules.transactions.service import TransactionService
from modules.transactions.schemas import DepositRequest

_SVC = "modules.transactions.service"
_PROC = "modules.jobs.momo_payment_processor"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_user(user_id=None, phone="+237600000001"):
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


def _make_txn(txn_id=None, status="pending", amount=100_000, channel="mtn_momo"):
    t = MagicMock()
    t.id = txn_id or uuid.uuid4()
    t.reference = f"TXN-20260422-{uuid.uuid4().hex[:8].upper()}"
    t.status = status
    t.amount = amount
    t.channel = channel
    t.credit_account_id = uuid.uuid4()
    t.debit_account_id = None
    t.initiated_by = uuid.uuid4()
    t.external_reference = None
    t.created_at = datetime.now(tz=timezone.utc)
    t.completed_at = None
    return t


def _make_service():
    """Create TransactionService with mocked db and repo (same pattern as test_transfers.py)."""
    db = AsyncMock()
    db.commit = AsyncMock()
    svc = TransactionService(db)
    svc._repo = AsyncMock()   # Replace the real repo with a mock
    return svc, db


def _make_redis():
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.setex = AsyncMock()
    r.delete = AsyncMock()
    return r


def _hmac_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ─── HMAC signature validation ────────────────────────────────────────────────

class TestValidateMtnCallbackSignature:
    def test_valid_signature(self):
        secret = "super-secret"
        body = b'{"status":"SUCCESSFUL"}'
        sig = _hmac_signature(body, secret)
        assert validate_mtn_callback_signature(body, sig, secret) is True

    def test_invalid_signature(self):
        secret = "super-secret"
        body = b'{"status":"SUCCESSFUL"}'
        assert validate_mtn_callback_signature(body, "wrong-sig", secret) is False

    def test_empty_secret_returns_false(self):
        body = b'{"status":"SUCCESSFUL"}'
        sig = _hmac_signature(body, "any")
        assert validate_mtn_callback_signature(body, sig, "") is False

    def test_empty_signature_returns_false(self):
        body = b'{"status":"SUCCESSFUL"}'
        assert validate_mtn_callback_signature(body, "", "secret") is False

    def test_case_insensitive_hex(self):
        """MTN may send uppercase hex — must still validate."""
        secret = "super-secret"
        body = b'{"status":"FAILED"}'
        sig = _hmac_signature(body, secret).upper()
        assert validate_mtn_callback_signature(body, sig, secret) is True

    def test_tampered_body_rejected(self):
        secret = "super-secret"
        original_body = b'{"status":"SUCCESSFUL","amount":"1000"}'
        tampered_body = b'{"status":"SUCCESSFUL","amount":"9999"}'
        sig = _hmac_signature(original_body, secret)
        assert validate_mtn_callback_signature(tampered_body, sig, secret) is False


# ─── TransactionService.deposit() ─────────────────────────────────────────────

class TestDepositService:
    @pytest.mark.asyncio
    async def test_deposit_creates_pending_txn_and_enqueues_job(self):
        user = _make_user()
        account = _make_account(user_id=user.id)
        txn = _make_txn()
        svc, db = _make_service()

        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)
        svc._repo.create = AsyncMock(return_value=txn)

        redis = _make_redis()

        with (
            patch(f"{_SVC}.get_redis_client", return_value=redis),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
            patch(f"{_SVC}._enqueue_momo_payment_job", new_callable=AsyncMock) as mock_enqueue,
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_MTN_MOMO = True

            acct_repo = AsyncMock()
            acct_repo.get_user_account = AsyncMock(return_value=account)
            MockAcctRepo.return_value = acct_repo

            payload = DepositRequest(account_id=str(account.id), amount=100_000, channel="mtn_momo")
            result = await svc.deposit(payload, user, "idem-key-123")

        assert result.success is True
        assert result.data["status"] == "pending"
        mock_enqueue.assert_called_once()
        call_kwargs = mock_enqueue.call_args.kwargs
        assert call_kwargs["phone_e164"] == user.phone
        assert call_kwargs["amount_units"] == 100_000
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_deposit_returns_409_on_duplicate_idempotency_key(self):
        from fastapi import HTTPException

        user = _make_user()
        existing_txn = _make_txn()
        svc, db = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=existing_txn)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_MTN_MOMO = True

            payload = DepositRequest(account_id=str(uuid.uuid4()), amount=100_000, channel="mtn_momo")
            with pytest.raises(HTTPException) as exc_info:
                await svc.deposit(payload, user, "dup-key")

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["code"] == "DUPLICATE_IDEMPOTENCY_KEY"

    @pytest.mark.asyncio
    async def test_deposit_returns_404_on_unknown_account(self):
        from fastapi import HTTPException

        user = _make_user()
        svc, db = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_MTN_MOMO = True

            acct_repo = AsyncMock()
            acct_repo.get_user_account = AsyncMock(return_value=None)
            MockAcctRepo.return_value = acct_repo

            payload = DepositRequest(account_id=str(uuid.uuid4()), amount=100_000, channel="mtn_momo")
            with pytest.raises(HTTPException) as exc_info:
                await svc.deposit(payload, user, "new-key")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_deposit_returns_501_for_unsupported_channel(self):
        from fastapi import HTTPException

        user = _make_user()
        svc, db = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_MTN_MOMO = True

            # visa is not yet supported — should raise 501
            payload = DepositRequest(account_id=str(uuid.uuid4()), amount=100_000, channel="visa")
            with pytest.raises(HTTPException) as exc_info:
                await svc.deposit(payload, user, "key-1")

        assert exc_info.value.status_code == 501
        assert exc_info.value.detail["code"] == "CHANNEL_NOT_SUPPORTED"

    @pytest.mark.asyncio
    async def test_deposit_returns_503_when_feature_disabled(self):
        from fastapi import HTTPException

        user = _make_user()
        svc, db = _make_service()

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_MTN_MOMO = False

            payload = DepositRequest(account_id=str(uuid.uuid4()), amount=100_000, channel="mtn_momo")
            with pytest.raises(HTTPException) as exc_info:
                await svc.deposit(payload, user, "key-1")

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["code"] == "FEATURE_DISABLED"

    @pytest.mark.asyncio
    async def test_deposit_returns_422_for_locked_account(self):
        from fastapi import HTTPException

        user = _make_user()
        account = _make_account(user_id=user.id, status="frozen")
        svc, db = _make_service()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountRepository") as MockAcctRepo,
            patch(f"{_SVC}.settings") as mock_settings,
        ):
            mock_settings.FEATURE_MTN_MOMO = True

            acct_repo = AsyncMock()
            acct_repo.get_user_account = AsyncMock(return_value=account)
            MockAcctRepo.return_value = acct_repo

            payload = DepositRequest(account_id=str(account.id), amount=100_000, channel="mtn_momo")
            with pytest.raises(HTTPException) as exc_info:
                await svc.deposit(payload, user, "key-2")

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "ACCOUNT_LOCKED"


# ─── handle_mtn_webhook() — state machine ─────────────────────────────────────

class TestHandleMtnWebhook:
    @pytest.mark.asyncio
    async def test_successful_callback_credits_account(self):
        txn = _make_txn(status="processing")
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

            await svc.handle_mtn_webhook("x-ref-123", {"status": "SUCCESSFUL"})

        acct_svc.apply_balance_delta.assert_called_once_with(txn.credit_account_id, txn.amount)
        update_kwargs = svc._repo.update.call_args.kwargs
        assert update_kwargs["status"] == "success"
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_callback_marks_txn_failed(self):
        txn = _make_txn(status="processing")
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=txn)
        svc._repo.update = AsyncMock(return_value=txn)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountService"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            await svc.handle_mtn_webhook("x-ref-456", {"status": "FAILED", "reason": "Insufficient funds"})

        update_kwargs = svc._repo.update.call_args.kwargs
        assert update_kwargs["status"] == "failed"
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_pending_status_no_state_change(self):
        txn = _make_txn(status="processing")
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=txn)
        svc._repo.update = AsyncMock(return_value=txn)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountService"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            await svc.handle_mtn_webhook("x-ref-789", {"status": "PENDING"})

        svc._repo.update.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_callback_on_success_ignored(self):
        """Txn already success — duplicate SUCCESSFUL callback must not re-credit account."""
        txn = _make_txn(status="success")
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=txn)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountService") as MockAcctSvc,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            acct_svc = AsyncMock()
            MockAcctSvc.return_value = acct_svc

            await svc.handle_mtn_webhook("x-ref-dup", {"status": "SUCCESSFUL"})

        acct_svc.apply_balance_delta.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_callback_on_failed_ignored(self):
        txn = _make_txn(status="failed")
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=txn)

        with (
            patch(f"{_SVC}.get_redis_client", return_value=_make_redis()),
            patch(f"{_SVC}.AccountService"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            await svc.handle_mtn_webhook("x-ref-dup2", {"status": "FAILED"})

        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_webhook_for_unknown_txn_is_silent(self):
        """No txn found for X-Reference-Id — must not raise, just log."""
        svc, db = _make_service()
        svc._repo.get_by_external_reference = AsyncMock(return_value=None)

        with patch(f"{_SVC}.get_redis_client", return_value=_make_redis()):
            # Must not raise
            await svc.handle_mtn_webhook("unknown-x-ref", {"status": "SUCCESSFUL"})

        db.commit.assert_not_called()


# ─── Timeout handler ──────────────────────────────────────────────────────────

class TestMomoTimeoutProcessor:
    """
    Tests for momo_payment_processor.process_momo_timeout_check().

    Patch strategy: AsyncSessionLocal, TransactionRepository, AccountService,
    and write_audit_log are lazy imports inside the function body — must be patched
    at their source modules (not at _PROC). MTNMoMoClient is a top-level import
    in the processor module, so it IS patched at _PROC.
    """

    def _job(self, txn_id, x_reference_id):
        job = MagicMock()
        job.data = {"txn_id": str(txn_id), "x_reference_id": x_reference_id}
        return job

    def _mock_db(self):
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db.commit = AsyncMock()
        return mock_db

    @pytest.mark.asyncio
    async def test_timeout_resolves_successful_payment(self):
        txn = _make_txn(status="processing")
        job = self._job(txn.id, "x-ref-timeout")
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
            patch(f"{_PROC}.MTNMoMoClient", return_value=client),
            patch("core.audit.write_audit_log", new_callable=AsyncMock),
        ):
            from modules.jobs.momo_payment_processor import process_momo_timeout_check
            await process_momo_timeout_check(job, "")

        acct_svc.apply_balance_delta.assert_called_once_with(txn.credit_account_id, txn.amount)
        update_kwargs = repo.update.call_args.kwargs
        assert update_kwargs["status"] == "success"

    @pytest.mark.asyncio
    async def test_timeout_resolves_failed_payment(self):
        txn = _make_txn(status="processing")
        job = self._job(txn.id, "x-ref-fail")
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
            patch(f"{_PROC}.MTNMoMoClient", return_value=client),
            patch("core.audit.write_audit_log", new_callable=AsyncMock),
        ):
            from modules.jobs.momo_payment_processor import process_momo_timeout_check
            await process_momo_timeout_check(job, "")

        acct_svc.apply_balance_delta.assert_not_called()
        update_kwargs = repo.update.call_args.kwargs
        assert update_kwargs["status"] == "failed"

    @pytest.mark.asyncio
    async def test_timeout_skips_already_resolved_txn(self):
        """If webhook already succeeded, timeout job does nothing — no MTN poll."""
        txn = _make_txn(status="success")
        job = self._job(txn.id, "x-ref-done")
        mock_db = self._mock_db()

        repo = AsyncMock()
        repo.get_by_id_unchecked = AsyncMock(return_value=txn)

        client = AsyncMock()

        with (
            patch("core.database.AsyncSessionLocal", return_value=mock_db),
            patch("modules.transactions.repository.TransactionRepository", return_value=repo),
            patch(f"{_PROC}.MTNMoMoClient", return_value=client),
        ):
            from modules.jobs.momo_payment_processor import process_momo_timeout_check
            await process_momo_timeout_check(job, "")

        client.get_payment_status.assert_not_called()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_timeout_treats_pending_mtn_status_as_failed(self):
        """MTN still PENDING after 125s → mark our txn as failed."""
        txn = _make_txn(status="processing")
        job = self._job(txn.id, "x-ref-stuck")
        mock_db = self._mock_db()

        repo = AsyncMock()
        repo.get_by_id_unchecked = AsyncMock(return_value=txn)
        repo.update = AsyncMock(return_value=txn)

        acct_svc = AsyncMock()
        client = AsyncMock()
        client.get_payment_status = AsyncMock(return_value="PENDING")

        with (
            patch("core.database.AsyncSessionLocal", return_value=mock_db),
            patch("modules.transactions.repository.TransactionRepository", return_value=repo),
            patch("modules.accounts.service.AccountService", return_value=acct_svc),
            patch(f"{_PROC}.MTNMoMoClient", return_value=client),
            patch("core.audit.write_audit_log", new_callable=AsyncMock),
        ):
            from modules.jobs.momo_payment_processor import process_momo_timeout_check
            await process_momo_timeout_check(job, "")

        update_kwargs = repo.update.call_args.kwargs
        assert update_kwargs["status"] == "failed"
        acct_svc.apply_balance_delta.assert_not_called()
