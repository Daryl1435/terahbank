"""
MTN MoMo Sandbox End-to-End Tester
====================================
Reads credentials from apps/api/.env and runs four live tests against the
MTN sandbox:

  1. Collections  -- balance check
  2. Collections  -- Request-to-Pay (deposit simulation, polls until resolved)
  3. Disbursements -- balance check
  4. Disbursements -- Transfer (withdrawal simulation, polls until resolved)

NOTE: Sandbox currency is EUR, not XAF. This script sends EUR directly and
bypasses the production XAF conversion.

MTN sandbox test MSISDN: 46733123450 → always resolves SUCCESSFUL

Usage:
    cd apps/api
    venv/Scripts/activate
    python scripts/test_mtn_sandbox.py
"""

import asyncio
import base64
import sys
import time
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

# Load .env from apps/api/
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)

SANDBOX_BASE = "https://sandbox.momodeveloper.mtn.com"
TEST_MSISDN = "46733123450"   # MTN-provided sandbox number → SUCCESSFUL
TEST_AMOUNT = "1"             # 1 EUR (sandbox only accepts EUR)
TEST_CURRENCY = "EUR"
POLL_INTERVAL_S = 3
POLL_TIMEOUT_S = 60


def _basic_auth(user_id: str, api_key: str) -> str:
    return "Basic " + base64.b64encode(f"{user_id}:{api_key}".encode()).decode()


def _env(key: str) -> str:
    val = os.getenv(key, "")
    if not val:
        print(f"  MISSING env var: {key}")
        print(f"  Run provision_mtn_sandbox.py first and paste its output into .env")
        sys.exit(1)
    return val


# -- Token helpers -------------------------------------------------------------

def get_collections_token(sub_key: str, user_id: str, api_key: str) -> str:
    resp = httpx.post(
        f"{SANDBOX_BASE}/collection/token/",
        headers={
            "Authorization": _basic_auth(user_id, api_key),
            "Ocp-Apim-Subscription-Key": sub_key,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  ERROR fetching collections token: HTTP {resp.status_code} -- {resp.text[:300]}")
        sys.exit(1)
    return resp.json()["access_token"]


def get_disbursements_token(sub_key: str, user_id: str, api_key: str) -> str:
    resp = httpx.post(
        f"{SANDBOX_BASE}/disbursement/token/",
        headers={
            "Authorization": _basic_auth(user_id, api_key),
            "Ocp-Apim-Subscription-Key": sub_key,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  ERROR fetching disbursements token: HTTP {resp.status_code} -- {resp.text[:300]}")
        sys.exit(1)
    return resp.json()["access_token"]


# -- Test functions -------------------------------------------------------------

def test_collections_balance(token: str, sub_key: str) -> None:
    print("\n[1/4] Collections balance check ...")
    resp = httpx.get(
        f"{SANDBOX_BASE}/collection/v1_0/account/balance",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Target-Environment": "sandbox",
            "Ocp-Apim-Subscription-Key": sub_key,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  FAIL HTTP {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)
    data = resp.json()
    print(f"  OK  availableBalance={data.get('availableBalance')} currency={data.get('currency')}")


def test_request_to_pay(token: str, sub_key: str) -> None:
    print(f"\n[2/4] Collections Request-to-Pay (payer={TEST_MSISDN}, {TEST_AMOUNT} {TEST_CURRENCY}) ...")
    x_ref = str(uuid.uuid4())
    our_ref = f"SANDBOX-TEST-{int(time.time())}"

    resp = httpx.post(
        f"{SANDBOX_BASE}/collection/v1_0/requesttopay",
        json={
            "amount": TEST_AMOUNT,
            "currency": TEST_CURRENCY,
            "externalId": our_ref,
            "payer": {"partyIdType": "MSISDN", "partyId": TEST_MSISDN},
            "payerMessage": "TerahBank sandbox test",
            "payeeNote": "TerahBank sandbox test",
        },
        headers={
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": x_ref,
            "X-Target-Environment": "sandbox",
            "Ocp-Apim-Subscription-Key": sub_key,
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    if resp.status_code != 202:
        print(f"  FAIL initiating RTP: HTTP {resp.status_code} -- {resp.text[:300]}")
        sys.exit(1)
    print(f"  Initiated. x_ref={x_ref[:8]}... polling every {POLL_INTERVAL_S}s (max {POLL_TIMEOUT_S}s) ...")

    deadline = time.time() + POLL_TIMEOUT_S
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL_S)
        poll = httpx.get(
            f"{SANDBOX_BASE}/collection/v1_0/requesttopay/{x_ref}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Target-Environment": "sandbox",
                "Ocp-Apim-Subscription-Key": sub_key,
            },
            timeout=30,
        )
        if poll.status_code != 200:
            print(f"  WARN poll returned HTTP {poll.status_code}")
            continue
        status = poll.json().get("status", "UNKNOWN")
        print(f"  status: {status}")
        if status != "PENDING":
            if status == "SUCCESSFUL":
                print(f"  OK  Request-to-Pay SUCCESSFUL")
            else:
                print(f"  FAIL  Request-to-Pay ended with status: {status}")
                sys.exit(1)
            return

    print(f"  FAIL  Timed out after {POLL_TIMEOUT_S}s -- still PENDING")
    sys.exit(1)


def test_disbursements_balance(token: str, sub_key: str) -> None:
    print("\n[3/4] Disbursements balance check ...")
    resp = httpx.get(
        f"{SANDBOX_BASE}/disbursement/v1_0/account/balance",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Target-Environment": "sandbox",
            "Ocp-Apim-Subscription-Key": sub_key,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  FAIL HTTP {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)
    data = resp.json()
    print(f"  OK  availableBalance={data.get('availableBalance')} currency={data.get('currency')}")


def test_transfer(token: str, sub_key: str) -> None:
    print(f"\n[4/4] Disbursements Transfer (payee={TEST_MSISDN}, {TEST_AMOUNT} {TEST_CURRENCY}) ...")
    x_ref = str(uuid.uuid4())
    our_ref = f"SANDBOX-DISB-{int(time.time())}"

    resp = httpx.post(
        f"{SANDBOX_BASE}/disbursement/v1_0/transfer",
        json={
            "amount": TEST_AMOUNT,
            "currency": TEST_CURRENCY,
            "externalId": our_ref,
            "payee": {"partyIdType": "MSISDN", "partyId": TEST_MSISDN},
            "payerMessage": "TerahBank sandbox withdrawal test",
            "payeeNote": "TerahBank sandbox withdrawal test",
        },
        headers={
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": x_ref,
            "X-Target-Environment": "sandbox",
            "Ocp-Apim-Subscription-Key": sub_key,
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    if resp.status_code != 202:
        print(f"  FAIL initiating transfer: HTTP {resp.status_code} -- {resp.text[:300]}")
        sys.exit(1)
    print(f"  Initiated. x_ref={x_ref[:8]}... polling every {POLL_INTERVAL_S}s (max {POLL_TIMEOUT_S}s) ...")

    deadline = time.time() + POLL_TIMEOUT_S
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL_S)
        poll = httpx.get(
            f"{SANDBOX_BASE}/disbursement/v1_0/transfer/{x_ref}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Target-Environment": "sandbox",
                "Ocp-Apim-Subscription-Key": sub_key,
            },
            timeout=30,
        )
        if poll.status_code != 200:
            print(f"  WARN poll returned HTTP {poll.status_code}")
            continue
        status = poll.json().get("status", "UNKNOWN")
        print(f"  status: {status}")
        if status != "PENDING":
            if status == "SUCCESSFUL":
                print(f"  OK  Transfer SUCCESSFUL")
            else:
                print(f"  FAIL  Transfer ended with status: {status}")
                sys.exit(1)
            return

    print(f"  FAIL  Timed out after {POLL_TIMEOUT_S}s -- still PENDING")
    sys.exit(1)


# -- Main ----------------------------------------------------------------------

def main() -> None:
    print("MTN MoMo Sandbox -- End-to-End Test")
    print("=" * 50)

    # Load credentials from .env
    col_sub_key  = _env("MTN_MOMO_SUBSCRIPTION_KEY")
    col_user_id  = _env("MTN_MOMO_COLLECTION_USER_ID")
    col_api_key  = _env("MTN_MOMO_API_KEY")
    disb_sub_key = _env("MTN_MOMO_DISBURSEMENT_SUBSCRIPTION_KEY")
    disb_user_id = _env("MTN_MOMO_DISBURSEMENT_USER_ID")
    disb_api_key = _env("MTN_MOMO_DISBURSEMENT_API_KEY")

    print("\nFetching tokens ...")
    col_token  = get_collections_token(col_sub_key, col_user_id, col_api_key)
    disb_token = get_disbursements_token(disb_sub_key, disb_user_id, disb_api_key)
    print("  OK  Collections token OK")
    print("  OK  Disbursements token OK")

    test_collections_balance(col_token, col_sub_key)
    test_request_to_pay(col_token, col_sub_key)
    test_disbursements_balance(disb_token, disb_sub_key)
    test_transfer(disb_token, disb_sub_key)

    print("\n" + "=" * 50)
    print("OK All 4 tests passed. MTN MoMo sandbox is fully operational.")
    print("\nNext step: test via the actual API")
    print("  UPDATE users SET kyc_status='approved' WHERE phone_number='+237675642835';")
    print("  POST /api/v1/transactions/deposit  (with MTN phone number)")
    print("  GET  /api/v1/transactions/{id}/status")


if __name__ == "__main__":
    main()
