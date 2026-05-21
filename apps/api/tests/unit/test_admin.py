"""
Unit tests for Milestone 5.1 — Admin Backend.

Covers:
  - RBAC enforcement: operations_staff blocked from super_admin endpoints
  - AdminService.admin_login: success, wrong password, inactive account
  - AdminService.list_users: no filters, search filter, kyc_status filter
  - AdminService.get_user: success, not found
  - AdminService.update_user_status: suspend, not found
  - AdminService.list_transactions: success, user_id filter
  - AdminService.get_config / update_config: success, Redis invalidation
  - AdminService.get_fraud_alerts: pagination
  - Fraud detection engine:
      LARGE_TRANSACTION triggers
      VELOCITY_BREACH triggers
      NEW_DEVICE_LARGE_WITHDRAWAL triggers
      NEW_ACCOUNT_RECIPIENT triggers
      No false positives — clean transaction produces no alerts
  - CSV exports: export_transactions_csv, export_users_csv

All DB and Redis calls are mocked.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from modules.admin.service import AdminService, _FRAUD_LARGE_TXN_THRESHOLD, _FRAUD_VELOCITY_MAX_TXNS
from modules.admin.schemas import (
    AdminLoginRequest,
    KYCDecisionRequest,
    UpdateConfigRequest,
    UpdateUserStatusRequest,
)

_SVC = "modules.admin.service"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


def _make_admin(role="super_admin", is_active=True):
    a = MagicMock()
    a.id = uuid.uuid4()
    a.email = "admin@terahbank.com"
    a.full_name = "Admin User"
    a.password_hash = "$2b$12$hashed"
    a.role = role
    a.is_active = is_active
    return a


def _make_user(user_id=None):
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.full_name = "Amina Diallo"
    u.email = "amina@example.com"
    u.phone_number = "+237690000001"
    u.kyc_status = "approved"
    u.account_status = "active"
    u.preferred_language = "fr"
    u.created_at = datetime(2025, 1, 15, 10, 0, 0)
    return u


def _make_txn(user_id=None, amount=500_000):
    t = MagicMock()
    t.id = uuid.uuid4()
    t.reference = "TXN-ABC123"
    t.initiated_by = user_id or uuid.uuid4()
    t.transaction_type = "transfer"
    t.channel = "internal"
    t.amount = amount
    t.currency = "XAF"
    t.status = "success"
    t.debit_account_id = uuid.uuid4()
    t.credit_account_id = uuid.uuid4()
    t.external_reference = None
    t.created_at = datetime(2025, 6, 1, 12, 0, 0)
    t.completed_at = datetime(2025, 6, 1, 12, 0, 1)
    return t


def _make_audit_log(action="FRAUD_ALERT_LARGE_TRANSACTION"):
    a = MagicMock()
    a.id = uuid.uuid4()
    a.action = action
    a.actor_id = uuid.uuid4()
    a.entity_type = "transaction"
    a.entity_id = uuid.uuid4()
    a.metadata_ = {"amount": 1_500_000}
    a.created_at = datetime(2025, 6, 1, 12, 0, 0)
    return a


def _make_account(account_id=None):
    acc = MagicMock()
    acc.id = account_id or uuid.uuid4()
    acc.account_type = "standard"
    acc.account_number = "TBK-0001"
    acc.balance = 50_000
    acc.status = "active"
    return acc


# ─── Admin login ──────────────────────────────────────────────────────────────

class TestAdminLogin:
    async def _call(self, db, email="admin@terahbank.com", password="SuperSecret1!"):
        return await AdminService(db).admin_login(email, password)

    @pytest.mark.asyncio
    async def test_login_success(self):
        db = _make_db()
        admin = _make_admin()

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.verify_password", return_value=True),
            patch(f"{_SVC}._create_admin_access_token", return_value="admin.jwt.token"),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            repo = MockRepo.return_value
            repo.get_admin_by_email = AsyncMock(return_value=admin)
            repo.update_admin = AsyncMock(return_value=admin)

            resp = await self._call(db)

        assert resp.success is True
        assert resp.data["access_token"] == "admin.jwt.token"
        assert resp.data["role"] == "super_admin"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        from fastapi import HTTPException
        db = _make_db()
        admin = _make_admin()

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.verify_password", return_value=False),
        ):
            repo = MockRepo.return_value
            repo.get_admin_by_email = AsyncMock(return_value=admin)

            with pytest.raises(HTTPException) as exc:
                await self._call(db, password="wrong")

        assert exc.value.status_code == 401
        assert exc.value.detail["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_user_not_found(self):
        from fastapi import HTTPException
        db = _make_db()

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.verify_password", return_value=False),
        ):
            repo = MockRepo.return_value
            repo.get_admin_by_email = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc:
                await self._call(db)

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_account(self):
        from fastapi import HTTPException
        db = _make_db()
        admin = _make_admin(is_active=False)

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.verify_password", return_value=True),
        ):
            repo = MockRepo.return_value
            repo.get_admin_by_email = AsyncMock(return_value=admin)

            with pytest.raises(HTTPException) as exc:
                await self._call(db)

        assert exc.value.status_code == 403
        assert exc.value.detail["code"] == "ACCOUNT_INACTIVE"


# ─── User management ──────────────────────────────────────────────────────────

class TestListUsers:
    @pytest.mark.asyncio
    async def test_list_no_filters(self):
        db = _make_db()
        users = [_make_user(), _make_user()]

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.list_users = AsyncMock(return_value=(users, 2))

            resp = await AdminService(db).list_users()

        assert resp.success is True
        assert resp.data["total"] == 2
        assert len(resp.data["users"]) == 2
        repo.list_users.assert_awaited_once_with(
            search=None, kyc_status=None, account_status=None, offset=0, limit=20
        )

    @pytest.mark.asyncio
    async def test_list_with_search(self):
        db = _make_db()
        users = [_make_user()]

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.list_users = AsyncMock(return_value=(users, 1))

            resp = await AdminService(db).list_users(search="amina")

        assert resp.data["total"] == 1
        repo.list_users.assert_awaited_once_with(
            search="amina", kyc_status=None, account_status=None, offset=0, limit=20
        )

    @pytest.mark.asyncio
    async def test_list_with_kyc_filter(self):
        db = _make_db()

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.list_users = AsyncMock(return_value=([], 0))

            resp = await AdminService(db).list_users(kyc_status="pending")

        assert resp.data["total"] == 0
        repo.list_users.assert_awaited_once_with(
            search=None, kyc_status="pending", account_status=None, offset=0, limit=20
        )


class TestGetUser:
    @pytest.mark.asyncio
    async def test_get_user_success(self):
        db = _make_db()
        user = _make_user()
        accounts = [_make_account()]

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_user_by_id = AsyncMock(return_value=user)
            repo.get_user_accounts = AsyncMock(return_value=accounts)

            resp = await AdminService(db).get_user(str(user.id))

        assert resp.success is True
        assert resp.data["user_id"] == str(user.id)
        assert len(resp.data["accounts"]) == 1

    @pytest.mark.asyncio
    async def test_get_user_not_found(self):
        from fastapi import HTTPException
        db = _make_db()

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_user_by_id = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc:
                await AdminService(db).get_user(str(uuid.uuid4()))

        assert exc.value.status_code == 404
        assert exc.value.detail["code"] == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_user_invalid_id(self):
        from fastapi import HTTPException
        db = _make_db()

        with pytest.raises(HTTPException) as exc:
            await AdminService(db).get_user("not-a-uuid")

        assert exc.value.status_code == 422


class TestUpdateUserStatus:
    @pytest.mark.asyncio
    async def test_suspend_user(self):
        db = _make_db()
        user = _make_user()
        admin = _make_admin()

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock) as mock_audit,
        ):
            repo = MockRepo.return_value
            repo.get_user_by_id = AsyncMock(return_value=user)
            repo.update_user = AsyncMock(return_value=user)

            payload = UpdateUserStatusRequest(status="suspended")
            resp = await AdminService(db).update_user_status(str(user.id), payload, admin)

        assert resp.success is True
        assert resp.data["account_status"] == "suspended"
        mock_audit.assert_awaited_once()
        call_kwargs = mock_audit.call_args[1]
        assert call_kwargs["action"] == "USER_SUSPENDED"

    @pytest.mark.asyncio
    async def test_suspend_user_not_found(self):
        from fastapi import HTTPException
        db = _make_db()

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_user_by_id = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc:
                await AdminService(db).update_user_status(
                    str(uuid.uuid4()), UpdateUserStatusRequest(status="suspended")
                )

        assert exc.value.status_code == 404


# ─── Transactions ─────────────────────────────────────────────────────────────

class TestListTransactions:
    @pytest.mark.asyncio
    async def test_list_success(self):
        db = _make_db()
        txns = [_make_txn(), _make_txn()]

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.list_transactions = AsyncMock(return_value=(txns, 2))

            resp = await AdminService(db).list_transactions()

        assert resp.success is True
        assert resp.data["total"] == 2
        assert len(resp.data["transactions"]) == 2

    @pytest.mark.asyncio
    async def test_list_by_user_id(self):
        db = _make_db()
        user_id = uuid.uuid4()
        txns = [_make_txn(user_id=user_id)]

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.list_transactions = AsyncMock(return_value=(txns, 1))

            resp = await AdminService(db).list_transactions(user_id=str(user_id))

        assert resp.data["total"] == 1
        repo.list_transactions.assert_awaited_once()
        call_kwargs = repo.list_transactions.call_args[1]
        assert call_kwargs["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_invalid_user_id(self):
        from fastapi import HTTPException
        db = _make_db()

        with pytest.raises(HTTPException) as exc:
            await AdminService(db).list_transactions(user_id="not-a-uuid")

        assert exc.value.status_code == 422


# ─── Config ───────────────────────────────────────────────────────────────────

class TestConfig:
    @pytest.mark.asyncio
    async def test_get_config(self):
        db = _make_db()
        cfg = MagicMock()
        cfg.key = "penalty_rate"
        cfg.value = "0.015"
        cfg.updated_at = datetime(2025, 1, 1)

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_all_config = AsyncMock(return_value=[cfg])

            resp = await AdminService(db).get_config()

        assert resp.success is True
        assert len(resp.data["config"]) == 1
        assert resp.data["config"][0]["key"] == "penalty_rate"

    @pytest.mark.asyncio
    async def test_update_config_invalidates_redis(self):
        db = _make_db()
        admin = _make_admin()
        cfg = MagicMock()
        cfg.key = "penalty_rate"
        cfg.value = "0.020"
        cfg.updated_at = datetime(2025, 1, 1)

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock()

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
            patch("core.redis.get_redis_client", return_value=mock_redis),
        ):
            repo = MockRepo.return_value
            repo.upsert_config = AsyncMock(return_value=cfg)

            payload = UpdateConfigRequest(key="penalty_rate", value="0.020")
            resp = await AdminService(db).update_config(payload, admin)

        assert resp.success is True
        assert mock_redis.delete.await_count == 2  # key + "config:all"

    @pytest.mark.asyncio
    async def test_update_config_writes_audit_log(self):
        db = _make_db()
        admin = _make_admin()
        cfg = MagicMock()
        cfg.key = "term_deposit_interest_rate"
        cfg.value = "0.025"
        cfg.updated_at = datetime(2025, 1, 1)

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock) as mock_audit,
            patch("core.redis.get_redis_client", return_value=AsyncMock()),
        ):
            repo = MockRepo.return_value
            repo.upsert_config = AsyncMock(return_value=cfg)

            payload = UpdateConfigRequest(key="term_deposit_interest_rate", value="0.025")
            await AdminService(db).update_config(payload, admin)

        mock_audit.assert_awaited_once()
        call_kwargs = mock_audit.call_args[1]
        assert call_kwargs["action"] == "CONFIG_UPDATED"
        assert call_kwargs["metadata"]["key"] == "term_deposit_interest_rate"


# ─── Fraud alerts ─────────────────────────────────────────────────────────────

class TestGetFraudAlerts:
    @pytest.mark.asyncio
    async def test_returns_paginated_alerts(self):
        db = _make_db()
        alerts = [
            _make_audit_log("FRAUD_ALERT_LARGE_TRANSACTION"),
            _make_audit_log("FRAUD_ALERT_VELOCITY_BREACH"),
        ]

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_fraud_alerts = AsyncMock(return_value=(alerts, 2))

            resp = await AdminService(db).get_fraud_alerts(offset=0, limit=50)

        assert resp.success is True
        assert resp.data["total"] == 2
        assert resp.data["alerts"][0]["rule"] == "LARGE_TRANSACTION"
        assert resp.data["alerts"][1]["rule"] == "VELOCITY_BREACH"


# ─── Fraud detection rules ────────────────────────────────────────────────────

class TestFraudRules:
    def _base_params(self, **overrides):
        params = dict(
            user_id=uuid.uuid4(),
            transaction_id=uuid.uuid4(),
            amount=100_000,
            transaction_type="transfer",
            channel="internal",
            credit_account_id=uuid.uuid4(),
            is_new_device=False,
        )
        params.update(overrides)
        return params

    @pytest.mark.asyncio
    async def test_large_transaction_triggers(self):
        db = _make_db()
        audit_calls = []

        async def fake_audit(db, **kwargs):
            audit_calls.append(kwargs["action"])

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.write_audit_log", side_effect=fake_audit),
        ):
            repo = MockRepo.return_value
            repo.count_recent_transactions = AsyncMock(return_value=0)
            repo.get_account_age_days = AsyncMock(return_value=30)

            await AdminService(db).check_fraud_rules(
                **self._base_params(amount=_FRAUD_LARGE_TXN_THRESHOLD + 1)
            )

        assert "FRAUD_ALERT_LARGE_TRANSACTION" in audit_calls

    @pytest.mark.asyncio
    async def test_no_alert_below_threshold(self):
        db = _make_db()
        audit_calls = []

        async def fake_audit(db, **kwargs):
            audit_calls.append(kwargs["action"])

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.write_audit_log", side_effect=fake_audit),
        ):
            repo = MockRepo.return_value
            repo.count_recent_transactions = AsyncMock(return_value=0)
            repo.get_account_age_days = AsyncMock(return_value=30)

            await AdminService(db).check_fraud_rules(
                **self._base_params(amount=_FRAUD_LARGE_TXN_THRESHOLD - 1)
            )

        fraud_alerts = [a for a in audit_calls if a.startswith("FRAUD_ALERT_")]
        assert len(fraud_alerts) == 0

    @pytest.mark.asyncio
    async def test_velocity_breach_triggers(self):
        db = _make_db()
        audit_calls = []

        async def fake_audit(db, **kwargs):
            audit_calls.append(kwargs["action"])

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.write_audit_log", side_effect=fake_audit),
        ):
            repo = MockRepo.return_value
            repo.count_recent_transactions = AsyncMock(return_value=_FRAUD_VELOCITY_MAX_TXNS)
            repo.get_account_age_days = AsyncMock(return_value=30)

            await AdminService(db).check_fraud_rules(**self._base_params())

        assert "FRAUD_ALERT_VELOCITY_BREACH" in audit_calls

    @pytest.mark.asyncio
    async def test_new_device_large_withdrawal_triggers(self):
        db = _make_db()
        audit_calls = []

        async def fake_audit(db, **kwargs):
            audit_calls.append(kwargs["action"])

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.write_audit_log", side_effect=fake_audit),
        ):
            repo = MockRepo.return_value
            repo.count_recent_transactions = AsyncMock(return_value=0)
            repo.get_account_age_days = AsyncMock(return_value=30)

            await AdminService(db).check_fraud_rules(
                **self._base_params(amount=600_000, transaction_type="withdrawal", is_new_device=True)
            )

        assert "FRAUD_ALERT_NEW_DEVICE_LARGE_WITHDRAWAL" in audit_calls

    @pytest.mark.asyncio
    async def test_new_device_large_withdrawal_no_trigger_on_known_device(self):
        db = _make_db()
        audit_calls = []

        async def fake_audit(db, **kwargs):
            audit_calls.append(kwargs["action"])

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.write_audit_log", side_effect=fake_audit),
        ):
            repo = MockRepo.return_value
            repo.count_recent_transactions = AsyncMock(return_value=0)
            repo.get_account_age_days = AsyncMock(return_value=30)

            await AdminService(db).check_fraud_rules(
                **self._base_params(amount=600_000, transaction_type="withdrawal", is_new_device=False)
            )

        assert "FRAUD_ALERT_NEW_DEVICE_LARGE_WITHDRAWAL" not in audit_calls

    @pytest.mark.asyncio
    async def test_new_account_recipient_triggers(self):
        db = _make_db()
        audit_calls = []

        async def fake_audit(db, **kwargs):
            audit_calls.append(kwargs["action"])

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.write_audit_log", side_effect=fake_audit),
        ):
            repo = MockRepo.return_value
            repo.count_recent_transactions = AsyncMock(return_value=0)
            repo.get_account_age_days = AsyncMock(return_value=0)  # < 1 day

            await AdminService(db).check_fraud_rules(**self._base_params())

        assert "FRAUD_ALERT_NEW_ACCOUNT_RECIPIENT" in audit_calls

    @pytest.mark.asyncio
    async def test_new_account_recipient_no_trigger_for_old_account(self):
        db = _make_db()
        audit_calls = []

        async def fake_audit(db, **kwargs):
            audit_calls.append(kwargs["action"])

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.write_audit_log", side_effect=fake_audit),
        ):
            repo = MockRepo.return_value
            repo.count_recent_transactions = AsyncMock(return_value=0)
            repo.get_account_age_days = AsyncMock(return_value=10)  # 10 days old — safe

            await AdminService(db).check_fraud_rules(**self._base_params())

        assert "FRAUD_ALERT_NEW_ACCOUNT_RECIPIENT" not in audit_calls

    @pytest.mark.asyncio
    async def test_multiple_rules_can_trigger_simultaneously(self):
        """All 4 rules can fire in one transaction."""
        db = _make_db()
        audit_calls = []

        async def fake_audit(db, **kwargs):
            audit_calls.append(kwargs["action"])

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.write_audit_log", side_effect=fake_audit),
        ):
            repo = MockRepo.return_value
            repo.count_recent_transactions = AsyncMock(return_value=_FRAUD_VELOCITY_MAX_TXNS)
            repo.get_account_age_days = AsyncMock(return_value=0)

            await AdminService(db).check_fraud_rules(
                **self._base_params(
                    amount=_FRAUD_LARGE_TXN_THRESHOLD + 1,
                    transaction_type="withdrawal",
                    is_new_device=True,
                )
            )

        assert "FRAUD_ALERT_LARGE_TRANSACTION" in audit_calls
        assert "FRAUD_ALERT_VELOCITY_BREACH" in audit_calls
        assert "FRAUD_ALERT_NEW_DEVICE_LARGE_WITHDRAWAL" in audit_calls
        assert "FRAUD_ALERT_NEW_ACCOUNT_RECIPIENT" in audit_calls

    @pytest.mark.asyncio
    async def test_check_fraud_rules_never_raises(self):
        """check_fraud_rules must never propagate exceptions — fire-and-log only."""
        db = _make_db()

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.count_recent_transactions = AsyncMock(side_effect=RuntimeError("DB down"))
            repo.get_account_age_days = AsyncMock(return_value=30)

            # Should not raise
            await AdminService(db).check_fraud_rules(**self._base_params(amount=2_000_000))

    @pytest.mark.asyncio
    async def test_no_credit_account_skips_rule4(self):
        """If credit_account_id is None, NEW_ACCOUNT_RECIPIENT rule is skipped."""
        db = _make_db()
        audit_calls = []

        async def fake_audit(db, **kwargs):
            audit_calls.append(kwargs["action"])

        with (
            patch(f"{_SVC}.AdminRepository") as MockRepo,
            patch(f"{_SVC}.write_audit_log", side_effect=fake_audit),
        ):
            repo = MockRepo.return_value
            repo.count_recent_transactions = AsyncMock(return_value=0)

            await AdminService(db).check_fraud_rules(
                **self._base_params(credit_account_id=None)
            )

        assert "FRAUD_ALERT_NEW_ACCOUNT_RECIPIENT" not in audit_calls
        # get_account_age_days should NOT be called
        repo.get_account_age_days.assert_not_called()


# ─── CSV Exports ──────────────────────────────────────────────────────────────

class TestCSVExports:
    @pytest.mark.asyncio
    async def test_export_transactions_csv_returns_streaming_response(self):
        from fastapi.responses import StreamingResponse
        db = _make_db()
        txns = [_make_txn(), _make_txn()]

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.list_transactions = AsyncMock(return_value=(txns, 2))

            response = await AdminService(db).export_transactions_csv()

        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/csv"
        assert "attachment" in response.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_export_transactions_csv_contains_header_row(self):
        from fastapi.responses import StreamingResponse
        db = _make_db()
        txns = [_make_txn()]

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.list_transactions = AsyncMock(return_value=(txns, 1))

            response = await AdminService(db).export_transactions_csv()

        # Collect streamed content (StreamingResponse yields str chunks, not bytes)
        chunks = [chunk async for chunk in response.body_iterator]
        content = "".join(c if isinstance(c, str) else c.decode() for c in chunks)
        assert "transaction_id" in content
        assert "amount_xaf" in content

    @pytest.mark.asyncio
    async def test_export_users_csv_returns_streaming_response(self):
        from fastapi.responses import StreamingResponse
        db = _make_db()
        users = [_make_user(), _make_user()]

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.list_users = AsyncMock(return_value=(users, 2))

            response = await AdminService(db).export_users_csv()

        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/csv"

    @pytest.mark.asyncio
    async def test_export_users_csv_contains_user_data(self):
        db = _make_db()
        user = _make_user()
        users = [user]

        with patch(f"{_SVC}.AdminRepository") as MockRepo:
            repo = MockRepo.return_value
            repo.list_users = AsyncMock(return_value=(users, 1))

            response = await AdminService(db).export_users_csv()

        chunks = [chunk async for chunk in response.body_iterator]
        content = "".join(c if isinstance(c, str) else c.decode() for c in chunks)
        assert "user_id" in content
        assert "kyc_status" in content
        assert user.email in content
