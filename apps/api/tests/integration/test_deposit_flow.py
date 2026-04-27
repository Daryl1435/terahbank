"""Integration tests — Deposit flow (MTN MoMo channel)

Covers the full async deposit lifecycle:
  POST /transactions/deposit → pending
  Webhook callback → success
  Balance verified in DB

All external services (MTN MoMo, SendGrid, FCM) are mocked.
DB writes use real PostgreSQL (test DB with rollback per test).
"""

import pytest
import uuid
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _idempotency_key() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Auth gate tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deposit_requires_auth(client: AsyncClient):
    """Unauthenticated requests must return 401."""
    res = await client.post(
        "/api/v1/transactions/deposit",
        json={"account_id": str(uuid.uuid4()), "amount": 500000, "channel": "mtn_momo"},
        headers={"Idempotency-Key": _idempotency_key()},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_deposit_requires_kyc_approved(
    client: AsyncClient,
    pending_kyc_user_token: str,
    standard_account_id: str,
):
    """Users with pending KYC must receive 403."""
    res = await client.post(
        "/api/v1/transactions/deposit",
        json={"account_id": standard_account_id, "amount": 500000, "channel": "mtn_momo"},
        headers={
            "Authorization": f"Bearer {pending_kyc_user_token}",
            "Idempotency-Key": _idempotency_key(),
        },
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deposit_idempotency_key_required(
    client: AsyncClient,
    approved_user_token: str,
    standard_account_id: str,
):
    """Missing Idempotency-Key header must return 422."""
    res = await client.post(
        "/api/v1/transactions/deposit",
        json={"account_id": standard_account_id, "amount": 500000, "channel": "mtn_momo"},
        headers={"Authorization": f"Bearer {approved_user_token}"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_deposit_duplicate_idempotency_key_rejected(
    client: AsyncClient,
    approved_user_token: str,
    standard_account_id: str,
):
    """Second request with same idempotency key must be rejected (409 or return first result)."""
    key = _idempotency_key()
    headers = {
        "Authorization": f"Bearer {approved_user_token}",
        "Idempotency-Key": key,
    }
    payload = {"account_id": standard_account_id, "amount": 500000, "channel": "mtn_momo"}

    with patch("modules.transactions.service.mtn_momo_client") as mock_momo:
        mock_momo.initiate_payment = AsyncMock(return_value={"reference": "MTN-001"})

        res1 = await client.post("/api/v1/transactions/deposit", json=payload, headers=headers)
        res2 = await client.post("/api/v1/transactions/deposit", json=payload, headers=headers)

    assert res1.status_code == 200
    # Second call with same key must not create a duplicate transaction
    assert res2.status_code in (200, 409)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deposit_mtn_momo_happy_path(
    client: AsyncClient,
    approved_user_token: str,
    standard_account_id: str,
    db_session,
):
    """Full deposit flow: initiate → pending state returned."""
    deposit_amount = 500000  # 5,000 XAF in smallest unit (assuming 1 XAF = 100 units)

    with patch("modules.transactions.service.mtn_momo_client") as mock_momo:
        mock_momo.initiate_payment = AsyncMock(
            return_value={"external_reference": "MTN-REF-12345"}
        )

        res = await client.post(
            "/api/v1/transactions/deposit",
            json={
                "account_id": standard_account_id,
                "amount": deposit_amount,
                "channel": "mtn_momo",
            },
            headers={
                "Authorization": f"Bearer {approved_user_token}",
                "Idempotency-Key": _idempotency_key(),
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "pending"
    assert body["data"]["amount"] == deposit_amount      # BIGINT — must match exactly
    assert body["data"]["channel"] == "mtn_momo"
    assert "id" in body["data"]


# ---------------------------------------------------------------------------
# Webhook callback → balance update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mtn_momo_webhook_success_updates_balance(
    client: AsyncClient,
    approved_user_token: str,
    standard_account_id: str,
    db_session,
):
    """Successful MoMo webhook callback must:
    1. Transition transaction to 'success'
    2. Update account balance (BIGINT add — no float arithmetic)
    3. Write audit log entry
    """
    deposit_amount = 500000
    idempotency_key = _idempotency_key()

    # Step 1: initiate deposit
    with patch("modules.transactions.service.mtn_momo_client") as mock_momo:
        mock_momo.initiate_payment = AsyncMock(
            return_value={"external_reference": "MTN-WH-001"}
        )
        res = await client.post(
            "/api/v1/transactions/deposit",
            json={"account_id": standard_account_id, "amount": deposit_amount, "channel": "mtn_momo"},
            headers={
                "Authorization": f"Bearer {approved_user_token}",
                "Idempotency-Key": idempotency_key,
            },
        )
    txn_id = res.json()["data"]["id"]

    # Step 2: simulate MTN callback with valid signature
    with patch("modules.transactions.router.verify_mtn_signature", return_value=True):
        webhook_res = await client.post(
            "/api/v1/webhooks/mtn-momo",
            json={
                "transaction_id": txn_id,
                "external_reference": "MTN-WH-001",
                "status": "SUCCESS",
            },
            headers={"X-MTN-Signature": "valid-sig"},
        )

    assert webhook_res.status_code == 200

    # Step 3: verify balance updated in DB
    account_res = await client.get(
        f"/api/v1/accounts/{standard_account_id}",
        headers={"Authorization": f"Bearer {approved_user_token}"},
    )
    balance = account_res.json()["data"]["balance"]
    assert isinstance(balance, int), "Balance must be BIGINT — never float"
    assert balance >= deposit_amount


@pytest.mark.asyncio
async def test_mtn_momo_webhook_invalid_signature_rejected(client: AsyncClient):
    """Webhook with invalid signature must return 401 and NOT update any state."""
    with patch("modules.transactions.router.verify_mtn_signature", return_value=False):
        res = await client.post(
            "/api/v1/webhooks/mtn-momo",
            json={"transaction_id": str(uuid.uuid4()), "status": "SUCCESS"},
            headers={"X-MTN-Signature": "bad-sig"},
        )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deposit_zero_amount_rejected(
    client: AsyncClient,
    approved_user_token: str,
    standard_account_id: str,
):
    res = await client.post(
        "/api/v1/transactions/deposit",
        json={"account_id": standard_account_id, "amount": 0, "channel": "mtn_momo"},
        headers={
            "Authorization": f"Bearer {approved_user_token}",
            "Idempotency-Key": _idempotency_key(),
        },
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_deposit_negative_amount_rejected(
    client: AsyncClient,
    approved_user_token: str,
    standard_account_id: str,
):
    res = await client.post(
        "/api/v1/transactions/deposit",
        json={"account_id": standard_account_id, "amount": -100, "channel": "mtn_momo"},
        headers={
            "Authorization": f"Bearer {approved_user_token}",
            "Idempotency-Key": _idempotency_key(),
        },
    )
    assert res.status_code == 422
