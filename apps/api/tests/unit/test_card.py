"""
Unit tests for Milestone 3.4 — VISA Card Integration.

Covers:
  - validate_visa_webhook_signature: valid, invalid, empty secret, empty sig,
    tampered body, uppercase hex match
  - CardService.issue_card: success, 503 feature disabled, 422 Standard Account only,
    422 card limit reached, 502 gateway failure
  - CardService.list_cards: returns card list
  - CardService.freeze: success, 422 already frozen, 422 expired
  - CardService.unfreeze: success, 422 not frozen
  - CardService.update_limits: success, 422 inactive card, 400 no changes
  - CardService.handle_visa_deposit_webhook: SUCCESSFUL credits account + marks success,
    FAILED marks failed, PENDING no-op, duplicate ignored, unknown reference silent

All DB, Redis, and HTTP calls are mocked.
"""

import hashlib
import hmac
import uuid
from datetime import datetime, timezone, date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.visa_gateway import validate_visa_webhook_signature
from modules.cards.service import CardService
from modules.cards.schemas import IssueCardRequest, UpdateLimitsRequest

_SVC = "modules.cards.service"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_user(user_id=None, phone="+237690000001", full_name="Alain Dupont"):
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.phone = phone
    u.full_name = full_name
    return u


def _make_account(account_id=None, user_id=None, account_type="standard", status="active"):
    a = MagicMock()
    a.id = account_id or uuid.uuid4()
    a.user_id = user_id or uuid.uuid4()
    a.account_type = account_type
    a.status = status
    return a


def _make_card(card_id=None, user_id=None, account_id=None, status="active",
               last_four="1234", daily_limit=None, per_transaction_limit=None):
    c = MagicMock()
    c.id = card_id or uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    c.account_id = account_id or uuid.uuid4()
    c.card_token = "tok_" + uuid.uuid4().hex[:16]
    c.last_four = last_four
    c.expiry_date = date(2027, 12, 1)
    c.status = status
    c.daily_limit = daily_limit
    c.per_transaction_limit = per_transaction_limit
    c.created_at = datetime.now(tz=timezone.utc)
    return c


def _make_txn(txn_id=None, status="pending", amount=500_000, channel="visa",
              txn_type="deposit", account_id=None):
    t = MagicMock()
    t.id = txn_id or uuid.uuid4()
    t.status = status
    t.amount = amount
    t.channel = channel
    t.transaction_type = txn_type
    t.credit_account_id = account_id or uuid.uuid4()
    t.debit_account_id = None
    t.initiated_by = uuid.uuid4()
    t.external_reference = None
    return t


def _make_svc(db=None):
    """Return a CardService with a mock DB session and mocked repository."""
    db = db or AsyncMock()
    svc = CardService(db)
    svc._repo = MagicMock()
    svc._repo.get_by_id = AsyncMock()
    svc._repo.list_by_user = AsyncMock(return_value=[])
    svc._repo.count_active_by_user = AsyncMock(return_value=0)
    svc._repo.create = AsyncMock(side_effect=lambda card: card)
    svc._repo.update = AsyncMock(side_effect=lambda card, **kw: _apply_updates(card, kw))
    return svc


def _apply_updates(obj, updates):
    for k, v in updates.items():
        setattr(obj, k, v)
    return obj


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ─── validate_visa_webhook_signature ──────────────────────────────────────────

class TestValidateVisaWebhookSignature:
    def test_valid_signature(self):
        body = b'{"status":"SUCCESSFUL"}'
        secret = "test_secret_123"
        sig = _sign(body, secret)
        assert validate_visa_webhook_signature(body, sig, secret) is True

    def test_invalid_signature(self):
        body = b'{"status":"SUCCESSFUL"}'
        secret = "test_secret_123"
        assert validate_visa_webhook_signature(body, "deadbeef", secret) is False

    def test_empty_secret_returns_false(self):
        body = b'{"status":"SUCCESSFUL"}'
        sig = _sign(body, "any_secret")
        assert validate_visa_webhook_signature(body, sig, "") is False

    def test_empty_signature_returns_false(self):
        body = b'{"status":"SUCCESSFUL"}'
        assert validate_visa_webhook_signature(body, "", "any_secret") is False

    def test_tampered_body_fails(self):
        body = b'{"status":"SUCCESSFUL"}'
        secret = "s3cr3t"
        sig = _sign(body, secret)
        assert validate_visa_webhook_signature(b'{"status":"FAILED"}', sig, secret) is False

    def test_uppercase_hex_match(self):
        body = b'{"event":"card.deposit"}'
        secret = "upper_secret"
        sig = _sign(body, secret).upper()
        assert validate_visa_webhook_signature(body, sig, secret) is True


# ─── CardService.issue_card ───────────────────────────────────────────────────

class TestIssueCard:
    @pytest.fixture
    def user(self):
        return _make_user()

    @pytest.mark.asyncio
    @patch(f"{_SVC}.settings")
    @patch(f"{_SVC}.AccountRepository")
    @patch(f"{_SVC}.VisaGatewayClient")
    @patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock)
    async def test_issue_card_success(self, mock_audit, MockGateway, MockAcctRepo, mock_settings, user):
        mock_settings.FEATURE_VIRTUAL_CARD = True
        mock_settings.VISA_MAX_CARDS_PER_USER = 3

        account = _make_account(user_id=user.id, account_type="standard", status="active")
        MockAcctRepo.return_value.get_user_account = AsyncMock(return_value=account)

        gateway_instance = MagicMock()
        gateway_instance.issue_virtual_card = AsyncMock(return_value={
            "card_token": "tok_abc123",
            "last_four": "4242",
            "expiry_date": "2028-06",
        })
        MockGateway.return_value = gateway_instance

        svc = _make_svc()
        svc._repo.count_active_by_user = AsyncMock(return_value=0)

        payload = IssueCardRequest(account_id=str(account.id))
        resp = await svc.issue_card(user, payload)

        assert resp.success is True
        assert resp.data["last_four"] == "4242"
        assert resp.data["status"] == "active"
        mock_audit.assert_called_once()

    @pytest.mark.asyncio
    @patch(f"{_SVC}.settings")
    async def test_feature_disabled_returns_503(self, mock_settings, user):
        mock_settings.FEATURE_VIRTUAL_CARD = False
        svc = _make_svc()
        payload = IssueCardRequest(account_id=str(uuid.uuid4()))

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await svc.issue_card(user, payload)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    @patch(f"{_SVC}.settings")
    @patch(f"{_SVC}.AccountRepository")
    async def test_non_standard_account_returns_422(self, MockAcctRepo, mock_settings, user):
        mock_settings.FEATURE_VIRTUAL_CARD = True
        mock_settings.VISA_MAX_CARDS_PER_USER = 3

        account = _make_account(user_id=user.id, account_type="project", status="active")
        MockAcctRepo.return_value.get_user_account = AsyncMock(return_value=account)

        svc = _make_svc()
        payload = IssueCardRequest(account_id=str(account.id))

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await svc.issue_card(user, payload)
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "INVALID_ACCOUNT_TYPE"

    @pytest.mark.asyncio
    @patch(f"{_SVC}.settings")
    @patch(f"{_SVC}.AccountRepository")
    async def test_card_limit_reached_returns_422(self, MockAcctRepo, mock_settings, user):
        mock_settings.FEATURE_VIRTUAL_CARD = True
        mock_settings.VISA_MAX_CARDS_PER_USER = 3

        account = _make_account(user_id=user.id, account_type="standard", status="active")
        MockAcctRepo.return_value.get_user_account = AsyncMock(return_value=account)

        svc = _make_svc()
        svc._repo.count_active_by_user = AsyncMock(return_value=3)  # at limit

        payload = IssueCardRequest(account_id=str(account.id))

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await svc.issue_card(user, payload)
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "CARD_LIMIT_REACHED"

    @pytest.mark.asyncio
    @patch(f"{_SVC}.settings")
    @patch(f"{_SVC}.AccountRepository")
    @patch(f"{_SVC}.VisaGatewayClient")
    async def test_gateway_failure_returns_502(self, MockGateway, MockAcctRepo, mock_settings, user):
        mock_settings.FEATURE_VIRTUAL_CARD = True
        mock_settings.VISA_MAX_CARDS_PER_USER = 3

        account = _make_account(user_id=user.id, account_type="standard", status="active")
        MockAcctRepo.return_value.get_user_account = AsyncMock(return_value=account)

        gateway_instance = MagicMock()
        gateway_instance.issue_virtual_card = AsyncMock(side_effect=RuntimeError("gateway down"))
        MockGateway.return_value = gateway_instance

        svc = _make_svc()
        svc._repo.count_active_by_user = AsyncMock(return_value=0)

        payload = IssueCardRequest(account_id=str(account.id))

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await svc.issue_card(user, payload)
        assert exc_info.value.status_code == 502
        assert exc_info.value.detail["code"] == "CARD_ISSUANCE_FAILED"


# ─── CardService.list_cards ───────────────────────────────────────────────────

class TestListCards:
    @pytest.mark.asyncio
    async def test_list_returns_all_cards(self):
        user_id = uuid.uuid4()
        cards = [_make_card(user_id=user_id), _make_card(user_id=user_id)]

        svc = _make_svc()
        svc._repo.list_by_user = AsyncMock(return_value=cards)

        resp = await svc.list_cards(user_id)
        assert resp.success is True
        assert resp.data["total"] == 2


# ─── CardService.freeze ───────────────────────────────────────────────────────

class TestFreezeCard:
    @pytest.mark.asyncio
    @patch(f"{_SVC}.VisaGatewayClient")
    @patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock)
    async def test_freeze_active_card(self, mock_audit, MockGateway):
        card = _make_card(status="active")
        gateway_instance = MagicMock()
        gateway_instance.update_card_status = AsyncMock(return_value=True)
        MockGateway.return_value = gateway_instance

        svc = _make_svc()
        svc._repo.get_by_id = AsyncMock(return_value=card)

        resp = await svc.freeze(str(card.id), card.user_id)
        assert resp.success is True
        assert resp.data["status"] == "frozen"
        mock_audit.assert_called_once()
        gateway_instance.update_card_status.assert_called_once_with(card.card_token, "freeze")

    @pytest.mark.asyncio
    async def test_freeze_already_frozen_returns_422(self):
        card = _make_card(status="frozen")
        svc = _make_svc()
        svc._repo.get_by_id = AsyncMock(return_value=card)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await svc.freeze(str(card.id), card.user_id)
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "CARD_ALREADY_FROZEN"

    @pytest.mark.asyncio
    async def test_freeze_expired_card_returns_422(self):
        card = _make_card(status="expired")
        svc = _make_svc()
        svc._repo.get_by_id = AsyncMock(return_value=card)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await svc.freeze(str(card.id), card.user_id)
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "CARD_INACTIVE"


# ─── CardService.unfreeze ─────────────────────────────────────────────────────

class TestUnfreezeCard:
    @pytest.mark.asyncio
    @patch(f"{_SVC}.VisaGatewayClient")
    @patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock)
    async def test_unfreeze_frozen_card(self, mock_audit, MockGateway):
        card = _make_card(status="frozen")
        gateway_instance = MagicMock()
        gateway_instance.update_card_status = AsyncMock(return_value=True)
        MockGateway.return_value = gateway_instance

        svc = _make_svc()
        svc._repo.get_by_id = AsyncMock(return_value=card)

        resp = await svc.unfreeze(str(card.id), card.user_id)
        assert resp.success is True
        assert resp.data["status"] == "active"
        gateway_instance.update_card_status.assert_called_once_with(card.card_token, "unfreeze")

    @pytest.mark.asyncio
    async def test_unfreeze_active_card_returns_422(self):
        card = _make_card(status="active")
        svc = _make_svc()
        svc._repo.get_by_id = AsyncMock(return_value=card)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await svc.unfreeze(str(card.id), card.user_id)
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "CARD_NOT_FROZEN"


# ─── CardService.update_limits ────────────────────────────────────────────────

class TestUpdateLimits:
    @pytest.mark.asyncio
    @patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock)
    async def test_update_daily_limit(self, mock_audit):
        card = _make_card(status="active")
        svc = _make_svc()
        svc._repo.get_by_id = AsyncMock(return_value=card)

        payload = UpdateLimitsRequest(daily_limit=500_000)
        resp = await svc.update_limits(str(card.id), card.user_id, payload)
        assert resp.success is True
        assert resp.data["daily_limit"] == 500_000
        mock_audit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_limits_expired_card_returns_422(self):
        card = _make_card(status="expired")
        svc = _make_svc()
        svc._repo.get_by_id = AsyncMock(return_value=card)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await svc.update_limits(str(card.id), card.user_id, UpdateLimitsRequest())
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_update_limits_no_values_returns_400(self):
        card = _make_card(status="active")
        svc = _make_svc()
        svc._repo.get_by_id = AsyncMock(return_value=card)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await svc.update_limits(str(card.id), card.user_id, UpdateLimitsRequest())
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "NO_CHANGES"


# ─── CardService.handle_visa_deposit_webhook ─────────────────────────────────

class TestHandleVisaDepositWebhook:

    def _make_svc_with_txn_repo(self, txn):
        """CardService with both card repo and a mocked txn repo."""
        db = AsyncMock()
        svc = CardService(db)
        svc._repo = MagicMock()

        # Mock TransactionRepository inside the method
        txn_repo_mock = MagicMock()
        txn_repo_mock.get_by_external_reference = AsyncMock(return_value=txn)
        txn_repo_mock.update = AsyncMock(side_effect=lambda t, **kw: _apply_updates(t, kw))
        return svc, txn_repo_mock

    @pytest.mark.asyncio
    @patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock)
    @patch("modules.cards.service.AccountService")
    @patch("modules.cards.service.TransactionRepository")
    async def test_successful_webhook_credits_account(self, MockTxnRepo, MockAcctService, mock_audit):
        txn = _make_txn(status="pending", channel="visa", txn_type="deposit")
        txn_repo_instance = MagicMock()
        txn_repo_instance.get_by_external_reference = AsyncMock(return_value=txn)
        txn_repo_instance.update = AsyncMock(side_effect=lambda t, **kw: _apply_updates(t, kw))
        MockTxnRepo.return_value = txn_repo_instance

        acct_service_instance = MagicMock()
        acct_service_instance.apply_balance_delta = AsyncMock()
        MockAcctService.return_value = acct_service_instance

        db = AsyncMock()
        svc = CardService(db)
        svc._repo = MagicMock()

        await svc.handle_visa_deposit_webhook("TXN-20260101-ABCD1234", {"status": "SUCCESSFUL"})

        acct_service_instance.apply_balance_delta.assert_called_once_with(txn.credit_account_id, txn.amount)
        assert txn.status == "success"
        mock_audit.assert_called_once()

    @pytest.mark.asyncio
    @patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock)
    @patch("modules.cards.service.TransactionRepository")
    async def test_failed_webhook_marks_failed(self, MockTxnRepo, mock_audit):
        txn = _make_txn(status="pending", channel="visa", txn_type="deposit")
        txn_repo_instance = MagicMock()
        txn_repo_instance.get_by_external_reference = AsyncMock(return_value=txn)
        txn_repo_instance.update = AsyncMock(side_effect=lambda t, **kw: _apply_updates(t, kw))
        MockTxnRepo.return_value = txn_repo_instance

        db = AsyncMock()
        svc = CardService(db)
        svc._repo = MagicMock()

        await svc.handle_visa_deposit_webhook("TXN-20260101-ABCD1234", {"status": "FAILED"})

        assert txn.status == "failed"
        mock_audit.assert_called_once()

    @pytest.mark.asyncio
    @patch("modules.cards.service.TransactionRepository")
    async def test_pending_webhook_no_state_change(self, MockTxnRepo):
        txn = _make_txn(status="pending")
        txn_repo_instance = MagicMock()
        txn_repo_instance.get_by_external_reference = AsyncMock(return_value=txn)
        MockTxnRepo.return_value = txn_repo_instance

        db = AsyncMock()
        svc = CardService(db)
        svc._repo = MagicMock()

        await svc.handle_visa_deposit_webhook("TXN-20260101-ABCD1234", {"status": "PENDING"})

        # update should not have been called
        txn_repo_instance.update.assert_not_called()

    @pytest.mark.asyncio
    @patch("modules.cards.service.TransactionRepository")
    async def test_duplicate_webhook_ignored(self, MockTxnRepo):
        txn = _make_txn(status="success")   # already resolved
        txn_repo_instance = MagicMock()
        txn_repo_instance.get_by_external_reference = AsyncMock(return_value=txn)
        txn_repo_instance.update = AsyncMock()
        MockTxnRepo.return_value = txn_repo_instance

        db = AsyncMock()
        svc = CardService(db)
        svc._repo = MagicMock()

        await svc.handle_visa_deposit_webhook("TXN-20260101-ABCD1234", {"status": "SUCCESSFUL"})

        txn_repo_instance.update.assert_not_called()

    @pytest.mark.asyncio
    @patch("modules.cards.service.TransactionRepository")
    async def test_unknown_reference_silent(self, MockTxnRepo):
        txn_repo_instance = MagicMock()
        txn_repo_instance.get_by_external_reference = AsyncMock(return_value=None)
        txn_repo_instance.update = AsyncMock()
        MockTxnRepo.return_value = txn_repo_instance

        db = AsyncMock()
        svc = CardService(db)
        svc._repo = MagicMock()

        # Should not raise
        await svc.handle_visa_deposit_webhook("TXN-UNKNOWN", {"status": "SUCCESSFUL"})
        txn_repo_instance.update.assert_not_called()


# ─── TransactionService.deposit — visa channel ───────────────────────────────

class TestDepositVisaChannel:
    """Smoke tests for the visa/mastercard branch in TransactionService.deposit()."""

    @pytest.mark.asyncio
    @patch("modules.transactions.service.settings")
    @patch("modules.transactions.service.AccountRepository")
    @patch("core.visa_gateway.VisaGatewayClient")
    @patch("modules.transactions.service.write_audit_log", new_callable=AsyncMock)
    async def test_visa_deposit_returns_payment_url(
        self, mock_audit, MockGateway, MockAcctRepo, mock_settings
    ):
        from modules.transactions.service import TransactionService
        from modules.transactions.schemas import DepositRequest

        mock_settings.FEATURE_CARD_DEPOSIT = True
        mock_settings.FEATURE_MTN_MOMO = True
        mock_settings.FEATURE_ORANGE_MONEY = True

        user = _make_user()
        account = _make_account(user_id=user.id, account_type="standard", status="active")
        MockAcctRepo.return_value.get_user_account = AsyncMock(return_value=account)

        gateway_instance = MagicMock()
        gateway_instance.create_payment_session = AsyncMock(return_value="https://pay.partner.com/session/xyz")
        MockGateway.return_value = gateway_instance

        db = AsyncMock()
        svc = TransactionService(db)
        svc._repo = MagicMock()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)

        txn = _make_txn(channel="visa", txn_type="deposit")
        txn.created_at = datetime.now(tz=timezone.utc)
        txn.reference = "TXN-20260101-ABCD1234"
        svc._repo.create = AsyncMock(return_value=txn)

        redis_mock = AsyncMock()
        redis_mock.setex = AsyncMock()
        with patch.object(type(svc), '_redis', new_callable=lambda: property(lambda self: redis_mock)):
            with patch("core.visa_gateway.VisaGatewayClient", return_value=gateway_instance):
                payload = DepositRequest(account_id=str(account.id), amount=500_000, channel="visa")
                resp = await svc.deposit(payload, user, "idem-key-xyz")

        assert resp.success is True
        assert resp.data["payment_url"] == "https://pay.partner.com/session/xyz"
        assert resp.data["status"] == "pending"

    @pytest.mark.asyncio
    @patch("modules.transactions.service.settings")
    async def test_card_deposit_feature_disabled_returns_503(self, mock_settings):
        from modules.transactions.service import TransactionService
        from modules.transactions.schemas import DepositRequest

        mock_settings.FEATURE_CARD_DEPOSIT = False
        mock_settings.FEATURE_MTN_MOMO = True
        mock_settings.FEATURE_ORANGE_MONEY = True

        db = AsyncMock()
        svc = TransactionService(db)
        svc._repo = MagicMock()
        svc._repo.get_by_idempotency_key = AsyncMock(return_value=None)

        user = _make_user()
        payload = DepositRequest(account_id=str(uuid.uuid4()), amount=500_000, channel="mastercard")

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await svc.deposit(payload, user, "idem-key-123")
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["code"] == "FEATURE_DISABLED"
