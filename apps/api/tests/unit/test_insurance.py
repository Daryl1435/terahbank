"""
Unit tests for Milestone 6.1 — Insurance.

Covers:
  - InsuranceService.list_products: Redis cache hit, cache miss → mock catalog, cache write
  - InsuranceService.initiate_enrollment: success (active, redirect_url, audit), product not found
  - InsuranceService.list_user_policies: success, empty list
  - InsuranceService.get_policy: success, not found, invalid UUID
  - InsuranceService.cancel_policy: success (audit, commit), not found, already cancelled, invalid UUID
  - _days_until_expiry helper: future date, today, past date

All DB and Redis calls are mocked.
"""

import json
import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.insurance.service import InsuranceService, MOCK_CATALOG, _days_until_expiry

_SVC = "modules.insurance.service"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


def _make_policy(
    user_id=None,
    status="active",
    policy_type="health",
    partner_id="nsia",
    product_name="NSIA Santé Pro",
    policy_number="NSIA-ABCD1234",
    days_future=180,
):
    p = MagicMock()
    p.id = uuid.uuid4()
    p.user_id = user_id or uuid.uuid4()
    p.partner_id = partner_id
    p.policy_type = policy_type
    p.policy_number = policy_number
    p.product_name = product_name
    p.status = status
    today = date.today()
    p.start_date = today
    p.expiry_date = today + timedelta(days=days_future)
    p.commission_amount = 500
    p.created_at = MagicMock()
    p.created_at.isoformat.return_value = "2026-01-01T00:00:00"
    return p


def _make_user():
    u = MagicMock()
    u.id = uuid.uuid4()
    return u


# ─── _days_until_expiry ───────────────────────────────────────────────────────

class TestDaysUntilExpiry:
    def test_future_date_returns_positive(self):
        future = date.today() + timedelta(days=30)
        assert _days_until_expiry(future) == 30

    def test_today_returns_zero(self):
        assert _days_until_expiry(date.today()) == 0

    def test_past_date_returns_none(self):
        past = date.today() - timedelta(days=1)
        assert _days_until_expiry(past) is None


# ─── list_products ────────────────────────────────────────────────────────────

class TestListProducts:
    @pytest.mark.asyncio
    async def test_returns_all_six_products_from_mock(self):
        """Cache miss → falls back to MOCK_CATALOG → returns 6 products."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        with patch("core.redis.get_redis_client", return_value=mock_redis):
            db = _make_db()
            svc = InsuranceService(db)
            resp = await svc.list_products()

        assert resp.success is True
        products = resp.data["products"]
        assert len(products) == 6

    @pytest.mark.asyncio
    async def test_product_fields_correct(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        with patch("core.redis.get_redis_client", return_value=mock_redis):
            db = _make_db()
            svc = InsuranceService(db)
            resp = await svc.list_products()

        first = resp.data["products"][0]
        assert first["product_id"] == MOCK_CATALOG[0]["product_id"]
        assert first["monthly_premium_xaf"] == MOCK_CATALOG[0]["monthly_premium_xaf"]

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_data(self):
        """Redis hit → returns cached products without touching mock."""
        catalog_data = [
            {
                "product_id": "test-prod",
                "partner_id": "test",
                "name": "Test Product",
                "description": "desc",
                "policy_type": "health",
                "monthly_premium_xaf": 1000,
                "max_coverage_xaf": 100000,
                "features": ["Feature A"],
            }
        ]
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(catalog_data))

        with patch("core.redis.get_redis_client", return_value=mock_redis):
            db = _make_db()
            svc = InsuranceService(db)
            resp = await svc.list_products()

        assert resp.success is True
        assert resp.data["products"][0]["product_id"] == "test-prod"

    @pytest.mark.asyncio
    async def test_cache_write_on_miss(self):
        """On cache miss, catalog is written to Redis with 6h TTL."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        with patch("core.redis.get_redis_client", return_value=mock_redis):
            db = _make_db()
            svc = InsuranceService(db)
            await svc.list_products()

        mock_redis.setex.assert_awaited_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == "insurance:catalog"
        assert args[1] == 21_600

    @pytest.mark.asyncio
    async def test_redis_failure_falls_back_to_mock(self):
        """Redis error must not bubble up — catalog served from mock."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis down"))

        with patch("core.redis.get_redis_client", return_value=mock_redis):
            db = _make_db()
            svc = InsuranceService(db)
            resp = await svc.list_products()

        assert resp.success is True
        assert len(resp.data["products"]) == 6


# ─── initiate_enrollment ──────────────────────────────────────────────────────

class TestInitiateEnrollment:
    @pytest.mark.asyncio
    async def test_enrollment_success(self):
        """Enrollment creates policy, writes audit log, commits, returns redirect_url."""
        from modules.insurance.schemas import EnrollmentRequest

        user_id = uuid.uuid4()
        policy = _make_policy(user_id=user_id)

        mock_repo = AsyncMock()
        mock_repo.create_policy = AsyncMock(return_value=policy)

        with (
            patch(f"{_SVC}.InsuranceRepository", return_value=mock_repo),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock) as mock_audit,
        ):
            db = _make_db()
            svc = InsuranceService(db)
            payload = EnrollmentRequest(product_id="nsia-health-pro")
            resp = await svc.initiate_enrollment(payload, user_id)

        assert resp.success is True
        assert "redirect_url" in resp.data
        assert "partners.terahbank.com/enroll/nsia" in resp.data["redirect_url"]
        assert resp.data["status"] == "active"
        mock_audit.assert_awaited_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_enrollment_unknown_product_raises_422(self):
        from fastapi import HTTPException
        from modules.insurance.schemas import EnrollmentRequest

        user_id = uuid.uuid4()

        with patch(f"{_SVC}.InsuranceRepository", return_value=AsyncMock()):
            db = _make_db()
            svc = InsuranceService(db)
            payload = EnrollmentRequest(product_id="nonexistent-product")

            with pytest.raises(HTTPException) as exc_info:
                await svc.initiate_enrollment(payload, user_id)

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "PRODUCT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_policy_number_format(self):
        """Policy number must follow {PARTNER_UPPER}-{HEX8} pattern."""
        import re
        from modules.insurance.schemas import EnrollmentRequest

        user_id = uuid.uuid4()
        policy = _make_policy(user_id=user_id)
        policy.partner_id = "nsia"

        mock_repo = AsyncMock()
        mock_repo.create_policy = AsyncMock(return_value=policy)

        with (
            patch(f"{_SVC}.InsuranceRepository", return_value=mock_repo),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            db = _make_db()
            svc = InsuranceService(db)
            payload = EnrollmentRequest(product_id="nsia-health-pro")
            await svc.initiate_enrollment(payload, user_id)

        # policy_number passed to create_policy
        call_kwargs = mock_repo.create_policy.call_args[1]
        pn = call_kwargs["policy_number"]
        assert re.match(r"^NSIA-[0-9A-F]{8}$", pn), f"Unexpected format: {pn}"

    @pytest.mark.asyncio
    async def test_commission_amount_stored(self):
        """Commission amount from catalog must be passed to create_policy."""
        from modules.insurance.schemas import EnrollmentRequest

        user_id = uuid.uuid4()
        policy = _make_policy(user_id=user_id)

        mock_repo = AsyncMock()
        mock_repo.create_policy = AsyncMock(return_value=policy)

        with (
            patch(f"{_SVC}.InsuranceRepository", return_value=mock_repo),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock),
        ):
            db = _make_db()
            svc = InsuranceService(db)
            payload = EnrollmentRequest(product_id="nsia-health-pro")
            await svc.initiate_enrollment(payload, user_id)

        call_kwargs = mock_repo.create_policy.call_args[1]
        assert call_kwargs["commission_amount"] == 500  # NSIA Santé Pro commission


# ─── list_user_policies ───────────────────────────────────────────────────────

class TestListUserPolicies:
    @pytest.mark.asyncio
    async def test_returns_policies(self):
        user_id = uuid.uuid4()
        policy = _make_policy(user_id=user_id, days_future=90)

        mock_repo = AsyncMock()
        mock_repo.list_policies_for_user = AsyncMock(return_value=[policy])

        with patch(f"{_SVC}.InsuranceRepository", return_value=mock_repo):
            db = _make_db()
            svc = InsuranceService(db)
            resp = await svc.list_user_policies(user_id)

        assert resp.success is True
        assert resp.data["total"] == 1
        policies = resp.data["policies"]
        assert policies[0]["policy_id"] == str(policy.id)
        assert policies[0]["days_until_expiry"] == 90

    @pytest.mark.asyncio
    async def test_empty_list(self):
        user_id = uuid.uuid4()
        mock_repo = AsyncMock()
        mock_repo.list_policies_for_user = AsyncMock(return_value=[])

        with patch(f"{_SVC}.InsuranceRepository", return_value=mock_repo):
            db = _make_db()
            svc = InsuranceService(db)
            resp = await svc.list_user_policies(user_id)

        assert resp.success is True
        assert resp.data["total"] == 0
        assert resp.data["policies"] == []


# ─── get_policy ───────────────────────────────────────────────────────────────

class TestGetPolicy:
    @pytest.mark.asyncio
    async def test_success(self):
        user_id = uuid.uuid4()
        policy = _make_policy(user_id=user_id, days_future=45)

        mock_repo = AsyncMock()
        mock_repo.get_policy = AsyncMock(return_value=policy)

        with patch(f"{_SVC}.InsuranceRepository", return_value=mock_repo):
            db = _make_db()
            svc = InsuranceService(db)
            resp = await svc.get_policy(str(policy.id), user_id)

        assert resp.success is True
        assert resp.data["policy_id"] == str(policy.id)
        assert resp.data["days_until_expiry"] == 45

    @pytest.mark.asyncio
    async def test_not_found_raises_404(self):
        from fastapi import HTTPException

        user_id = uuid.uuid4()
        mock_repo = AsyncMock()
        mock_repo.get_policy = AsyncMock(return_value=None)

        with patch(f"{_SVC}.InsuranceRepository", return_value=mock_repo):
            db = _make_db()
            svc = InsuranceService(db)
            with pytest.raises(HTTPException) as exc_info:
                await svc.get_policy(str(uuid.uuid4()), user_id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["code"] == "POLICY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_invalid_uuid_raises_422(self):
        from fastapi import HTTPException

        user_id = uuid.uuid4()

        with patch(f"{_SVC}.InsuranceRepository", return_value=AsyncMock()):
            db = _make_db()
            svc = InsuranceService(db)
            with pytest.raises(HTTPException) as exc_info:
                await svc.get_policy("not-a-uuid", user_id)

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "INVALID_POLICY_ID"


# ─── cancel_policy ────────────────────────────────────────────────────────────

class TestCancelPolicy:
    @pytest.mark.asyncio
    async def test_cancel_success(self):
        """Cancelling active policy writes audit, updates status, commits."""
        user_id = uuid.uuid4()
        policy = _make_policy(user_id=user_id, status="active")

        mock_repo = AsyncMock()
        mock_repo.get_policy = AsyncMock(return_value=policy)
        mock_repo.update_policy = AsyncMock(return_value=policy)

        with (
            patch(f"{_SVC}.InsuranceRepository", return_value=mock_repo),
            patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock) as mock_audit,
        ):
            db = _make_db()
            svc = InsuranceService(db)
            resp = await svc.cancel_policy(str(policy.id), user_id)

        assert resp.success is True
        assert resp.data["status"] == "cancelled"
        mock_audit.assert_awaited_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cancel_not_found_raises_404(self):
        from fastapi import HTTPException

        user_id = uuid.uuid4()
        mock_repo = AsyncMock()
        mock_repo.get_policy = AsyncMock(return_value=None)

        with patch(f"{_SVC}.InsuranceRepository", return_value=mock_repo):
            db = _make_db()
            svc = InsuranceService(db)
            with pytest.raises(HTTPException) as exc_info:
                await svc.cancel_policy(str(uuid.uuid4()), user_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_raises_422(self):
        from fastapi import HTTPException

        user_id = uuid.uuid4()
        policy = _make_policy(user_id=user_id, status="cancelled")

        mock_repo = AsyncMock()
        mock_repo.get_policy = AsyncMock(return_value=policy)

        with patch(f"{_SVC}.InsuranceRepository", return_value=mock_repo):
            db = _make_db()
            svc = InsuranceService(db)
            with pytest.raises(HTTPException) as exc_info:
                await svc.cancel_policy(str(policy.id), user_id)

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "POLICY_NOT_ACTIVE"

    @pytest.mark.asyncio
    async def test_cancel_expired_policy_raises_422(self):
        from fastapi import HTTPException

        user_id = uuid.uuid4()
        policy = _make_policy(user_id=user_id, status="expired")

        mock_repo = AsyncMock()
        mock_repo.get_policy = AsyncMock(return_value=policy)

        with patch(f"{_SVC}.InsuranceRepository", return_value=mock_repo):
            db = _make_db()
            svc = InsuranceService(db)
            with pytest.raises(HTTPException) as exc_info:
                await svc.cancel_policy(str(policy.id), user_id)

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "POLICY_NOT_ACTIVE"

    @pytest.mark.asyncio
    async def test_cancel_invalid_uuid_raises_422(self):
        from fastapi import HTTPException

        user_id = uuid.uuid4()

        with patch(f"{_SVC}.InsuranceRepository", return_value=AsyncMock()):
            db = _make_db()
            svc = InsuranceService(db)
            with pytest.raises(HTTPException) as exc_info:
                await svc.cancel_policy("bad-uuid", user_id)

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "INVALID_POLICY_ID"
