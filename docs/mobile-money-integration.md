# TerahBank — Mobile Money Integration Spec

> Highest-risk integration in the system. Read this before touching transactions/service.py.
> Covers: MTN MoMo, Orange Money — full async flow, state machine, retry logic, sandbox setup.

---

## Why This Is Complex

Mobile Money APIs in CEMAC are:
- **Asynchronous** — you initiate, they callback. Not synchronous request/response.
- **Unreliable** — USSD timeouts, network drops, duplicate callbacks are normal.
- **Inconsistent** — sandbox vs production behavior differs. Test both.
- **Slow** — user must approve on their phone. Can take 5–120 seconds.

**Never block an HTTP request thread waiting for MoMo response.**
**Always use the async queue pattern described below.**

---

## Transaction State Machine

```
                         ┌─────────┐
                         │ PENDING │ ← Transaction created in DB
                         └────┬────┘
                              │ Worker picks up from queue
                         ┌────▼────────┐
                         │ PROCESSING  │ ← API call made to MoMo
                         └────┬────────┘
              ┌───────────────┼──────────────────┐
              │               │                  │
       ┌──────▼──────┐ ┌──────▼──────┐   ┌──────▼──────┐
       │   SUCCESS   │ │   FAILED    │   │  TIMED_OUT  │
       │ (callback)  │ │ (callback)  │   │  (120s max) │
       └──────┬──────┘ └─────────────┘   └─────────────┘
              │
       ┌──────▼──────┐
       │  REVERSED   │ ← Manual admin action only
       └─────────────┘
```

**State transition rules:**
- Only `PENDING` → `PROCESSING` (worker picks up)
- Only `PROCESSING` → `SUCCESS` or `FAILED` (via callback or timeout)
- Only `SUCCESS` → `REVERSED` (manual admin, rare)
- A transaction in `FAILED` or `TIMED_OUT` is terminal — do not retry the same transaction. Create a new one.

---

## MTN Mobile Money (MoMo Collections API)

### API Version: v1\_0 (Collections)

### Environment URLs
```
Sandbox:    https://sandbox.momodeveloper.mtn.com
Production: https://ericssonbasicapi2.azure-api.net  # Confirm with MTN partner team
```

### Authentication Flow
1. Create API User (sandbox only — production user pre-created)
2. Get API Key → exchange for Bearer access token (valid 1 hour)
3. Cache token in Redis: `mtn_momo:access_token` with 55-min TTL (5-min buffer before expiry)
4. Auto-refresh if Redis key missing

### Deposit Flow (Request to Pay)

```python
# Step 1: Initiate payment — POST /collection/v1_0/requesttopay
headers = {
    "Authorization": f"Bearer {access_token}",
    "X-Reference-Id": str(uuid4()),      # Our transaction reference — STORE THIS
    "X-Target-Environment": "sandbox",   # or "production"
    "Ocp-Apim-Subscription-Key": MTN_MOMO_SUBSCRIPTION_KEY,
    "Content-Type": "application/json"
}
body = {
    "amount": str(amount_in_xaf),        # String, NOT int
    "currency": "XAF",
    "externalId": transaction.reference, # Our TXN-XXXXXXXX reference
    "payer": {
        "partyIdType": "MSISDN",
        "partyId": user.phone_number     # E.164 without + (e.g. "237600000000")
    },
    "payerMessage": f"TerahBank deposit - {transaction.reference}",
    "payeeNote": "TerahBank savings deposit"
}
# Response: 202 Accepted (async — not success yet)
# Store X-Reference-Id as external_reference on transaction
```

```python
# Step 2: Wait for callback — POST to our /webhooks/mtn-momo
# OR poll status — GET /collection/v1_0/requesttopay/{X-Reference-Id}
# Polling is fallback only — prefer webhooks
```

```python
# Step 3: Callback validation
def validate_mtn_callback(request_body: dict, signature: str) -> bool:
    # Validate HMAC-SHA256 signature using MTN_MOMO_WEBHOOK_SECRET
    expected = hmac.new(
        MTN_MOMO_WEBHOOK_SECRET.encode(),
        request_body.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
    # If validation fails: return 200 OK anyway (don't let MTN retry forever)
    # But don't process the transaction
```

### MTN Callback Payload
```json
{
  "financialTransactionId": "MTN-INTERNAL-REF",
  "externalId": "TXN-20260221-00001",
  "amount": "5000",
  "currency": "XAF",
  "payer": {"partyIdType": "MSISDN", "partyId": "237600000000"},
  "payerMessage": "TerahBank deposit - TXN-20260221-00001",
  "payeeNote": "TerahBank savings deposit",
  "status": "SUCCESSFUL"  // or "FAILED"
}
```

### MTN Status Codes
| Status | Meaning | Action |
|---|---|---|
| `SUCCESSFUL` | Payment confirmed | Credit account, update status=SUCCESS |
| `FAILED` | User rejected or error | Update status=FAILED, notify user |
| `PENDING` | Still waiting | Continue polling (max 120s) |
| `TIMEOUT` | MTN internal timeout | Update status=TIMED_OUT, notify user |

### Timeout Handling
```python
# BullMQ job: after 120s, if status still PROCESSING
async def handle_momo_timeout(transaction_id: str):
    txn = await get_transaction(transaction_id)
    if txn.status == 'processing':
        # Check MTN status one final time via GET /requesttopay/{ref}
        mtn_status = await mtn_client.get_payment_status(txn.external_reference)
        if mtn_status == 'SUCCESSFUL':
            await complete_transaction(txn, 'success')
        else:
            await complete_transaction(txn, 'failed')
            await notify_user(txn.user_id, 'PAYMENT_TIMEOUT')
```

---

## Orange Money (CEMAC Collections)

### Authentication
```python
# POST /oauth/token
body = {
    "grant_type": "client_credentials",
    "client_id": ORANGE_MONEY_CLIENT_ID,
    "client_secret": ORANGE_MONEY_CLIENT_SECRET
}
# Cache token in Redis: `orange_money:access_token`, TTL = expires_in - 60s
```

### Deposit Flow
```python
# POST /omcoreapis/1.0.2/mp/pay
headers = {
    "Authorization": f"Bearer {access_token}",
    "X-AUTH-KEY": ORANGE_MONEY_MERCHANT_KEY
}
body = {
    "merchant": {"id": ORANGE_MONEY_MERCHANT_ID},
    "money": {"amount": amount_in_xaf, "cents": 0},
    "customer": {"key": user.phone_number},
    "order": {"id": transaction.reference},
    "return_url": "https://api.terahbank.com/api/v1/webhooks/orange-money",
    "cancel_url": "https://api.terahbank.com/api/v1/webhooks/orange-money",
    "notif_url": "https://api.terahbank.com/api/v1/webhooks/orange-money"
}
```

---

## Withdrawal Flow (Disbursement)

```python
# MTN MoMo Disbursements API — POST /disbursement/v1_0/transfer
# User confirmed withdrawal → queue job → worker calls API → callback confirms

# Key difference from deposits:
# - Different API endpoint (/disbursement/ not /collection/)
# - Different subscription key (DISBURSEMENT vs COLLECTION)
# - Funds leave TerahBank immediately — must debit account BEFORE API call
#   to prevent race conditions (use DB transaction with rollback on API failure)

async def process_withdrawal(transaction: Transaction):
    async with db.begin():  # DB transaction
        # Debit account first
        await debit_account(transaction.debit_account_id, transaction.amount)
        await update_transaction_status(transaction.id, 'processing')
    # Then call MoMo API outside DB transaction
    # If MoMo API fails → compensating transaction to credit back
```

---

## BullMQ Job Definitions

```python
# Job: process_momo_payment
{
    "name": "process_momo_payment",
    "data": {
        "transaction_id": "uuid",
        "provider": "mtn_momo",  # or "orange_money"
        "type": "deposit"  # or "withdrawal"
    },
    "opts": {
        "attempts": 1,           # DO NOT retry financial jobs automatically
        "timeout": 130000,       # 130s (120s MoMo + 10s buffer)
        "removeOnComplete": false,
        "removeOnFail": false
    }
}

# Job: momo_timeout_check
# Scheduled 125s after payment initiation as fallback if webhook not received
{
    "name": "momo_timeout_check",
    "delay": 125000
}
```

**CRITICAL: Set `attempts: 1` on financial jobs.** Auto-retry on a financial job can cause double charges. Handle retries manually after verifying provider state.

---

## Duplicate Callback Protection

MTN and Orange Money can send the same callback multiple times (network retries).

```python
async def handle_mtn_callback(payload: dict):
    txn = await get_by_external_reference(payload['externalId'])

    # Idempotency check — if already SUCCESS, ignore
    if txn.status in ('success', 'failed', 'reversed'):
        return {"received": True}  # Return 200 OK — don't reprocess

    # Process only if still PENDING or PROCESSING
    if payload['status'] == 'SUCCESSFUL':
        async with db.begin():
            await update_transaction_status(txn.id, 'success')
            await credit_account(txn.credit_account_id, txn.amount)
            await write_audit_log(...)
        await send_success_notification(txn.user_id, txn.amount)
```

---

## Sandbox Testing Checklist

Before touching production credentials:

```
[ ] MTN sandbox account created at momodeveloper.mtn.com
[ ] Sandbox API user and key generated
[ ] Test deposit flow end-to-end in sandbox
[ ] Test deposit timeout (use sandbox phone number that simulates timeout)
[ ] Test deposit failure (use sandbox phone number that simulates failure)
[ ] Test duplicate callback (send same callback payload twice — verify single credit)
[ ] Test withdrawal flow end-to-end
[ ] Webhook signature validation tested with wrong secret (must reject)
[ ] Orange Money sandbox configured and tested
[ ] All tests pass before any production credential is created
```

---

## Monitoring Alerts

Set these up in Datadog/CloudWatch before launch:

| Alert | Threshold | Action |
|---|---|---|
| Transactions stuck in PROCESSING > 5 min | Any | Page on-call engineer |
| MoMo callback failure rate > 5% | 5 min window | Alert team |
| Withdrawal disbursement failure | Any | Immediate alert — money involved |
| Duplicate callback detected | Any | Log + alert (investigation needed) |
| MTN/Orange API error rate > 1% | 5 min window | Alert team |
