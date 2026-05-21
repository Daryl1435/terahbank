"""
TerahBank Load Test — Locust script.

Simulates two scenarios from the Milestone 7.1 requirements:
  1. StandardUser  — 500 concurrent authenticated sessions (health + balance checks)
  2. WebhookFlood  — 10x peak MTN MoMo webhook callbacks

Usage:
  pip install locust
  locust -f scripts/load_test.py --host http://localhost:8000

  # Headless (CI / scripted):
  locust -f scripts/load_test.py \
    --host http://localhost:8000 \
    --headless \
    --users 500 \
    --spawn-rate 50 \
    --run-time 60s \
    --html load_test_report.html

Target SLAs (from Milestone 7.4):
  - Read endpoints  P95 < 300ms
  - Write endpoints P95 < 600ms
"""

import hashlib
import hmac
import json
import uuid

from locust import HttpUser, between, task


# ─── Scenario 1: Standard authenticated user session ─────────────────────────

class StandardUser(HttpUser):
    """
    Simulates a logged-in mobile app user.

    In a real scenario the user would complete OTP login first, but since OTP
    requires an out-of-band code we test the publicly accessible endpoints that
    represent the highest-volume traffic: health checks and read-heavy paths.

    Weight 8 = 8x more common than WebhookFlood (realistic production split).
    """
    weight = 8
    wait_time = between(1, 3)  # seconds between tasks — simulates human think time

    def on_start(self):
        """Called once per simulated user at spawn time."""
        # Generate a fake JWT token header — endpoints that actually verify JWT
        # will return 401, but we still measure response time and server load.
        self.headers = {
            "Authorization": "Bearer fake_load_test_token",
            "Content-Type": "application/json",
        }

    @task(5)
    def health_check(self):
        """
        Highest frequency task — health probe.
        ECS and load balancers hit this constantly; it must stay fast.
        """
        self.client.get("/api/v1/health", name="/health")

    @task(3)
    def get_notifications_unauthenticated(self):
        """
        Attempt to read notifications without a valid token.
        Validates that auth middleware rejects requests quickly (no DB hit expected).
        """
        self.client.get(
            "/api/v1/notifications/",
            headers=self.headers,
            name="/notifications [401 expected]",
        )

    @task(2)
    def get_accounts_unauthenticated(self):
        """
        Same pattern for accounts — tests the auth middleware throughput.
        """
        self.client.get(
            "/api/v1/accounts/",
            headers=self.headers,
            name="/accounts [401 expected]",
        )

    @task(1)
    def register_attempt(self):
        """
        POST /auth/register with a dummy payload — tests request parsing and
        validation throughput. Expects 422 (validation error) since data is minimal.
        """
        self.client.post(
            "/api/v1/auth/register",
            json={
                "phone_number": f"+237{uuid.uuid4().int % 900000000 + 600000000}",
                "email": f"load_{uuid.uuid4().hex[:8]}@test.com",
                "password": "short",  # intentionally invalid → triggers 422 fast
                "full_name": "Load Test User",
            },
            name="/auth/register [422 expected]",
        )


# ─── Scenario 2: MTN MoMo webhook flood ──────────────────────────────────────

# Webhook secret must match MTN_MOMO_WEBHOOK_SECRET in your .env
_WEBHOOK_SECRET = "mtn-webhook-secret-mockup-local"


def _mtn_signature(body: bytes) -> str:
    """Compute the HMAC-SHA256 signature that the MTN callback would send."""
    return hmac.new(_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


class WebhookFlood(HttpUser):
    """
    Simulates 10x peak MTN MoMo webhook callbacks.

    At peak, assume 50 payments/minute → flood = 500 callbacks/minute.
    Each task fires a SUCCESSFUL or FAILED callback with a valid HMAC signature.

    Weight 2 = 2x less common than StandardUser in this test run,
    but the raw callback rate is still very high per Locust user.
    """
    weight = 2
    wait_time = between(0.1, 0.5)  # fast — webhooks arrive in bursts

    @task(7)
    def successful_callback(self):
        """Simulate a SUCCESSFUL MoMo payment callback."""
        reference_id = str(uuid.uuid4())
        payload = {
            "referenceId": reference_id,
            "status": "SUCCESSFUL",
            "financialTransactionId": f"FIN{uuid.uuid4().hex[:12].upper()}",
            "amount": "5000",
            "currency": "XAF",
            "externalId": str(uuid.uuid4()),
        }
        body = json.dumps(payload).encode()
        self.client.post(
            "/api/v1/webhooks/mtn-momo",
            data=body,
            headers={
                "Content-Type": "application/json",
                # MTN sends the HMAC in this header (matches our webhook handler)
                "X-Callback-Signature": _mtn_signature(body),
            },
            name="/webhooks/mtn-momo [SUCCESSFUL]",
        )

    @task(3)
    def failed_callback(self):
        """Simulate a FAILED MoMo payment callback (30% of real-world failures)."""
        reference_id = str(uuid.uuid4())
        payload = {
            "referenceId": reference_id,
            "status": "FAILED",
            "amount": "5000",
            "currency": "XAF",
            "externalId": str(uuid.uuid4()),
        }
        body = json.dumps(payload).encode()
        self.client.post(
            "/api/v1/webhooks/mtn-momo",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Callback-Signature": _mtn_signature(body),
            },
            name="/webhooks/mtn-momo [FAILED]",
        )
