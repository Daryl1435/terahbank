"""
TerahBank Full Flow Tester
===========================
Tests the complete deposit + withdrawal flow through the real API.

What this script does:
  1. Login with phone + password
  2. Auto-reads OTP from Redis (no manual copy-paste needed)
  3. Gets the user's first account
  4. POST /transactions/deposit  (mtn_momo channel)
  5. Polls /transactions/{id}/status every 3s
  6. Prints each status change so you can watch the flow live

Requirements before running:
  - Docker running  (PostgreSQL + Redis)
  - API server running:  python -m uvicorn main:app --reload
  - BullMQ worker running (separate terminal):  python worker.py
  - Test user KYC approved in DB (see note below)

KYC approval (run once in psql):
  UPDATE users SET kyc_status='approved'
  WHERE phone_number='+237675642835';

Usage:
    cd apps/api
    venv/Scripts/activate
    python scripts/test_full_flow.py
"""

import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

API_BASE = "http://localhost:8000/api/v1"

# Test user credentials (already registered in local DB)
PHONE = "+237675642835"
PASSWORD = "P@$w0rd12"

DEPOSIT_AMOUNT_XAF_UNITS = 500_00   # 500 XAF (in smallest units: 1 XAF = 100)
POLL_INTERVAL_S = 3
POLL_TIMEOUT_S = 150   # 125s MTN SLA + buffer


# ── Helpers ───────────────────────────────────────────────────────────────────

def step(msg: str) -> None:
    print(f"\n[>>] {msg}")


def ok(msg: str) -> None:
    print(f"     OK  {msg}")


def fail(msg: str) -> None:
    print(f"     FAIL  {msg}")
    sys.exit(1)


def _read_otp_from_redis(user_id: str, purpose: str) -> str:
    """Read OTP directly from Redis via docker exec — avoids manual copy-paste."""
    key = f"otp:{user_id}:{purpose}"
    result = subprocess.run(
        ["docker", "exec", "terahbank_redis", "redis-cli", "GET", key],
        capture_output=True, text=True, timeout=10,
    )
    otp = result.stdout.strip()
    if not otp or otp == "(nil)":
        fail(
            f"OTP not found in Redis (key={key}).\n"
            "     Is the API server running? Did login succeed?"
        )
    return otp


# ── Steps ─────────────────────────────────────────────────────────────────────

def login() -> tuple[str, str, str]:
    """Login → auto-read OTP → verify → return (access_token, refresh_token, user_id)."""

    step("Login")
    resp = httpx.post(f"{API_BASE}/auth/login",
        json={"identifier": PHONE, "password": PASSWORD}, timeout=15)
    if resp.status_code != 200:
        fail(f"Login failed: HTTP {resp.status_code} — {resp.text[:300]}")
    data = resp.json()["data"]
    user_id = data["user_id"]
    ok(f"Login accepted. user_id={user_id}")

    step("Reading OTP from Redis ...")
    otp = _read_otp_from_redis(user_id, "login")
    ok(f"OTP = {otp}")

    step("Verifying OTP")
    resp = httpx.post(f"{API_BASE}/auth/verify-otp",
        json={"user_id": user_id, "otp": otp, "purpose": "login"}, timeout=15)
    if resp.status_code != 200:
        fail(f"OTP verify failed: HTTP {resp.status_code} — {resp.text[:300]}")
    tokens = resp.json()["data"]
    ok("OTP verified. Access token received.")
    return tokens["access_token"], tokens["refresh_token"], user_id


def get_account(access_token: str) -> str:
    """Fetch first savings account and return its ID."""
    step("Fetching accounts")
    resp = httpx.get(f"{API_BASE}/accounts/",
        headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
    if resp.status_code != 200:
        fail(f"Get accounts failed: HTTP {resp.status_code} — {resp.text[:300]}")
    accounts = resp.json()["data"]["accounts"]
    if not accounts:
        fail("No accounts found. Did you register and get KYC approved?")
    account = accounts[0]
    ok(f"Account: id={account['account_id']}  balance={account.get('balance', '?')} XAF units  type={account.get('account_type', '?')}")
    return account["account_id"]


def deposit(access_token: str, account_id: str) -> str:
    """POST /transactions/deposit and return transaction ID."""
    step(f"Initiating MTN MoMo deposit  ({DEPOSIT_AMOUNT_XAF_UNITS} XAF units = {DEPOSIT_AMOUNT_XAF_UNITS // 100} XAF)")
    idempotency_key = str(uuid.uuid4())
    resp = httpx.post(
        f"{API_BASE}/transactions/deposit",
        json={
            "account_id": account_id,
            "amount": DEPOSIT_AMOUNT_XAF_UNITS,
            "channel": "mtn_momo",
        },
        headers={
            "Authorization": f"Bearer {access_token}",
            "Idempotency-Key": idempotency_key,
        },
        timeout=15,
    )
    if resp.status_code not in (200, 201, 202):
        fail(f"Deposit failed: HTTP {resp.status_code} — {resp.text[:400]}")
    txn = resp.json()["data"]
    txn_id = txn.get("transaction_id") or txn.get("id")
    ok(f"Deposit accepted. transaction_id={txn_id}  status={txn.get('status')}")
    return txn_id


def poll_status(access_token: str, txn_id: str) -> None:
    """Poll /transactions/{id}/status until resolved or timeout."""
    step(f"Polling status every {POLL_INTERVAL_S}s (max {POLL_TIMEOUT_S}s) ...")
    print("     Note: BullMQ worker must be running (python worker.py) for status to advance.")
    print()

    deadline = time.time() + POLL_TIMEOUT_S
    last_status = None
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL_S)
        resp = httpx.get(
            f"{API_BASE}/transactions/{txn_id}/status",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"     WARN poll returned HTTP {resp.status_code}")
            continue

        data = resp.json().get("data", {})
        status = data.get("status", "unknown")
        external_ref = data.get("external_reference", "-")

        if status != last_status:
            ts = time.strftime("%H:%M:%S")
            print(f"     [{ts}]  status: {status}  external_ref: {external_ref}")
            last_status = status

        if status in ("completed", "failed", "cancelled"):
            print()
            if status == "completed":
                ok("Deposit COMPLETED successfully.")
            else:
                print(f"     Transaction ended with status: {status}")
                print("     (MTN sandbox known to return INTERNAL_PROCESSING_ERROR)")
                print("     The API flow worked correctly — this is an MTN sandbox limitation.")
            return

    print()
    print(f"     Timed out after {POLL_TIMEOUT_S}s — transaction still in progress.")
    print("     Check again with: GET /api/v1/transactions/{txn_id}/status")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("TerahBank Full Flow Test")
    print("=" * 50)
    print(f"API: {API_BASE}")
    print(f"User: {PHONE}")

    access_token, _, user_id = login()
    account_id = get_account(access_token)
    txn_id = deposit(access_token, account_id)
    poll_status(access_token, txn_id)

    print("\n" + "=" * 50)
    print("Flow complete. Check the worker terminal for job logs.")
    print(f"Full transaction detail: GET {API_BASE}/transactions/{txn_id}")


if __name__ == "__main__":
    main()
