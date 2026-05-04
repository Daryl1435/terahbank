"""
MTN MoMo Sandbox Provisioner
=============================
Creates real API users for both Collections and Disbursements products,
retrieves API keys, verifies the credentials work, and prints a ready-to-paste
.env snippet.

Usage:
    cd apps/api
    venv/Scripts/activate
    python scripts/provision_mtn_sandbox.py \
        --collections-key  YOUR_COLLECTIONS_SUBSCRIPTION_KEY \
        --disbursements-key YOUR_DISBURSEMENTS_SUBSCRIPTION_KEY

Where to get subscription keys:
    1. Sign in at https://momodeveloper.mtn.com
    2. Go to your Profile → Subscriptions
    3. Subscribe to "MTN MoMo API Collection" and "MTN MoMo API Disbursement"
    4. Copy the Primary Key for each product
"""

import argparse
import base64
import json
import sys
import uuid

import httpx

SANDBOX_BASE = "https://sandbox.momodeveloper.mtn.com"
CALLBACK_HOST = "localhost"


def _basic_auth(user_id: str, api_key: str) -> str:
    return "Basic " + base64.b64encode(f"{user_id}:{api_key}".encode()).decode()


def create_api_user(subscription_key: str) -> str:
    """POST /v1_0/apiuser — create a new sandbox API user. Returns the user ID."""
    user_id = str(uuid.uuid4())
    url = f"{SANDBOX_BASE}/v1_0/apiuser"
    headers = {
        "X-Reference-Id": user_id,
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/json",
    }
    body = {"providerCallbackHost": CALLBACK_HOST}

    resp = httpx.post(url, headers=headers, json=body, timeout=30)
    if resp.status_code != 201:
        print(f"  ERROR creating API user: HTTP {resp.status_code}")
        print(f"  Response: {resp.text[:400]}")
        sys.exit(1)

    return user_id


def get_api_key(user_id: str, subscription_key: str) -> str:
    """POST /v1_0/apiuser/{id}/apikey — generate and return the API key."""
    url = f"{SANDBOX_BASE}/v1_0/apiuser/{user_id}/apikey"
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}

    resp = httpx.post(url, headers=headers, timeout=30)
    if resp.status_code != 201:
        print(f"  ERROR getting API key: HTTP {resp.status_code}")
        print(f"  Response: {resp.text[:400]}")
        sys.exit(1)

    return resp.json()["apiKey"]


def get_token(product: str, user_id: str, api_key: str, subscription_key: str) -> str:
    """Exchange credentials for a Bearer token to prove they work."""
    url = f"{SANDBOX_BASE}/{product}/token/"
    headers = {
        "Authorization": _basic_auth(user_id, api_key),
        "Ocp-Apim-Subscription-Key": subscription_key,
    }

    resp = httpx.post(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"  ERROR getting token: HTTP {resp.status_code}")
        print(f"  Response: {resp.text[:400]}")
        sys.exit(1)

    return resp.json()["access_token"]


def provision(product_label: str, product_path: str, subscription_key: str) -> dict:
    print(f"\n-- {product_label} ------------------------------")

    print("  [1/3] Creating API user...")
    user_id = create_api_user(subscription_key)
    print(f"        User ID : {user_id}")

    print("  [2/3] Generating API key...")
    api_key = get_api_key(user_id, subscription_key)
    print(f"        API Key : {api_key[:8]}{'*' * (len(api_key) - 8)}")

    print("  [3/3] Verifying credentials (token exchange)...")
    token = get_token(product_path, user_id, api_key, subscription_key)
    print(f"        Token   : {token[:24]}...  OK valid")

    return {"user_id": user_id, "api_key": api_key}


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision MTN MoMo sandbox credentials")
    parser.add_argument("--collections-key",   required=True, help="Collections Primary Subscription Key")
    parser.add_argument("--disbursements-key", required=True, help="Disbursements Primary Subscription Key")
    args = parser.parse_args()

    print("MTN MoMo Sandbox Provisioner")
    print("=" * 50)

    col  = provision("Collections",   "collection",   args.collections_key)
    disb = provision("Disbursements", "disbursement", args.disbursements_key)

    print("\n" + "=" * 50)
    print("OK Both products provisioned successfully.\n")
    print("Paste the following into apps/api/.env:\n")
    print("-" * 50)
    print(f"MTN_MOMO_SUBSCRIPTION_KEY={args.collections_key}")
    print(f"MTN_MOMO_COLLECTION_USER_ID={col['user_id']}")
    print(f"MTN_MOMO_API_KEY={col['api_key']}")
    print(f"MTN_MOMO_DISBURSEMENT_SUBSCRIPTION_KEY={args.disbursements_key}")
    print(f"MTN_MOMO_DISBURSEMENT_USER_ID={disb['user_id']}")
    print(f"MTN_MOMO_DISBURSEMENT_API_KEY={disb['api_key']}")
    print("MTN_MOMO_ENVIRONMENT=sandbox")
    print("-" * 50)
    print("\nNext step: python scripts/test_mtn_sandbox.py")


if __name__ == "__main__":
    main()
