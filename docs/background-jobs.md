# TerahBank — Background Jobs Reference

> All async work runs via BullMQ with Redis backing.
> Rule: Never do slow work in a request handler. Queue it and return immediately.
> Every job has: name, trigger, data payload, retry policy, dead-letter behavior.

---

## BullMQ Queue Structure

```
Redis DB 2 (jobs):
├── queue:payments          ← Mobile Money deposit/withdrawal jobs
├── queue:notifications     ← Push, email, SMS jobs
├── queue:scheduled         ← Cron-based recurring jobs
├── queue:reports           ← PDF/CSV generation jobs
└── queue:dead-letter       ← Failed jobs after all retries exhausted
```

---

## Payment Jobs (`queue:payments`)

### `process_momo_payment`
Triggered by: POST /transactions/deposit or /transactions/withdraw (MoMo channels)

```python
{
    "name": "process_momo_payment",
    "data": {
        "transaction_id": "uuid",
        "provider": "mtn_momo",       # or "orange_money"
        "type": "deposit",            # or "withdrawal"
        "amount": 500000,             # BIGINT — XAF centimes
        "phone_number": "+237600000000",
        "account_id": "uuid"
    },
    "opts": {
        "attempts": 1,               # NEVER auto-retry financial jobs
        "timeout": 130000,           # 130 seconds max
        "removeOnComplete": false,   # Keep for audit
        "removeOnFail": false        # Keep for investigation
    }
}
```

### `momo_timeout_check`
Triggered by: Scheduled 125s after payment initiation (delayed job)

```python
{
    "name": "momo_timeout_check",
    "data": {"transaction_id": "uuid"},
    "opts": {
        "delay": 125000,
        "attempts": 1
    }
}
```

### `process_card_payment`
Triggered by: VISA card transaction webhook

```python
{
    "name": "process_card_payment",
    "data": {
        "card_id": "uuid",
        "transaction_id": "uuid",
        "amount": 150000,
        "merchant_name": "Netflix",
        "external_reference": "VISA-REF-123"
    },
    "opts": {"attempts": 1, "timeout": 30000}
}
```

---

## Notification Jobs (`queue:notifications`)

### `send_push_notification`
```python
{
    "name": "send_push_notification",
    "data": {
        "user_id": "uuid",
        "fcm_token": "...",
        "title": "Deposit Successful",
        "body": "5,000 XAF has been added to your account.",
        "data": {"type": "DEPOSIT_SUCCESS", "transaction_id": "uuid"}
    },
    "opts": {"attempts": 3, "backoff": {"type": "exponential", "delay": 2000}}
}
```

### `send_email`
```python
{
    "name": "send_email",
    "data": {
        "to": "user@example.com",
        "template_id": "d-monthly-savings-summary",  # SendGrid template
        "dynamic_data": {
            "user_name": "Amina",
            "total_saved": "25,000 XAF",
            "month": "February 2026"
        }
    },
    "opts": {"attempts": 3, "backoff": {"type": "fixed", "delay": 5000}}
}
```

### `send_sms`
```python
{
    "name": "send_sms",
    "data": {
        "to": "+237600000000",
        "message": "Your TerahBank OTP is 482931. Valid for 5 minutes.",
        "type": "OTP"  # or "ALERT" or "REMINDER"
    },
    "opts": {"attempts": 3, "backoff": {"type": "fixed", "delay": 2000}}
}
```

---

## Scheduled Jobs (`queue:scheduled`)

All cron jobs run via BullMQ's `repeat` option. Cron times in CAT (UTC+1).

### `monthly_savings_summary`
**Schedule:** `0 8 1 * *` — 1st of every month at 08:00 CAT
**Purpose:** FR-014 — generate and send monthly savings summary to all active users

```python
{
    "name": "monthly_savings_summary",
    "data": {"month": "2026-02", "batch_size": 100},
    "opts": {
        "repeat": {"cron": "0 7 1 * *"},  # UTC (CAT = UTC+1)
        "attempts": 1  # Don't retry — next month will resend
    }
}
```

Worker behavior:
1. Query all users with `account_status = 'active'`
2. Process in batches of 100 to avoid DB overload
3. For each user: calculate monthly stats → enqueue `send_email` + `send_push_notification`
4. Write audit log entry per batch completion

### `term_deposit_maturity_reminder`
**Schedule:** `0 9 * * *` — daily at 09:00 CAT
**Purpose:** FR-028 — notify users at 14d, 7d, 1d before maturity

```python
{
    "name": "term_deposit_maturity_reminder",
    "data": {},
    "opts": {"repeat": {"cron": "0 8 * * *"}}
}
```

Worker behavior:
1. Query accounts WHERE `account_type = 'term_deposit'` AND `status = 'active'`
   AND `maturity_date IN (today + 14, today + 7, today + 1)`
2. Enqueue `send_push_notification` + `send_email` per matching account

### `insurance_policy_renewal_reminder`
**Schedule:** `0 10 * * *` — daily at 10:00 CAT
**Purpose:** FR-045 — notify users at 30d, 7d before policy expiry

```python
{
    "name": "insurance_policy_renewal_reminder",
    "data": {},
    "opts": {"repeat": {"cron": "0 9 * * *"}}
}
```

### `auto_save_executor`
**Schedule:** `0 * * * *` — every hour on the hour
**Purpose:** FR-021 — execute configured auto-save rules

```python
{
    "name": "auto_save_executor",
    "data": {},
    "opts": {"repeat": {"cron": "0 * * * *"}}
}
```

Worker behavior:
1. Query all `auto_save_rules` WHERE `next_execution_at <= now()`
2. For each rule: validate source account has sufficient balance
3. If yes → enqueue internal transfer job → update `next_execution_at`
4. If no → send low-balance notification → skip this cycle (not an error)

### `session_cleanup`
**Schedule:** `*/15 * * * *` — every 15 minutes
**Purpose:** Clean expired sessions from Redis (belt-and-suspenders beyond Redis TTL)

### `fraud_pattern_daily_digest`
**Schedule:** `0 6 * * *` — daily at 06:00 CAT (before business hours)
**Purpose:** Compile previous day's flagged transactions into admin digest email

---

## Report Jobs (`queue:reports`)

### `generate_transaction_report`
Triggered by: GET /admin/reports/transactions with format=pdf or format=csv

```python
{
    "name": "generate_transaction_report",
    "data": {
        "requested_by": "admin_user_id",
        "filters": {
            "date_from": "2026-02-01",
            "date_to": "2026-02-28",
            "status": "success",
            "channel": "mtn_momo"
        },
        "format": "pdf",           # or "csv"
        "delivery": "download"     # or "email"
    },
    "opts": {
        "attempts": 2,
        "timeout": 60000           # 60s max for large reports
    }
}
```

Worker behavior:
1. Query read replica (never primary) with filters
2. Generate PDF (WeasyPrint) or CSV (csv module)
3. Upload to S3 with 1-hour presigned URL
4. Return download URL to admin (via webhook or polling endpoint)

---

## Dead Letter Queue (`queue:dead-letter`)

Jobs land here when all retry attempts are exhausted.

**For payment jobs:** Alert immediately — these need manual review.
**For notification jobs:** Log and move on — non-critical.
**For report jobs:** Notify the requesting admin — "Report generation failed, please retry."

```python
# BullMQ dead letter handler
async def on_failed(job: Job, error: Exception):
    if job.queue_name == 'payments':
        # CRITICAL — alert on-call engineer
        await send_critical_alert(
            f"Payment job {job.id} failed permanently: {error}",
            transaction_id=job.data.get('transaction_id')
        )
        await write_audit_log(
            action='PAYMENT_JOB_DEAD_LETTER',
            metadata={'job_id': job.id, 'error': str(error)}
        )
    else:
        # Non-critical — log only
        logger.error(f"Job {job.name} ({job.id}) moved to dead letter: {error}")
```

---

## Job Monitoring Dashboard

Expose BullMQ metrics to Datadog:

| Metric | Alert Threshold |
|---|---|
| `payments` queue depth > 100 | Immediate alert |
| `payments` job processing time > 130s | Immediate alert |
| `notifications` queue depth > 1000 | Warning |
| Dead letter queue new job (any) | Log + Slack notification |
| Scheduled job missed by > 5 min | Warning |

**Bull Board** (dev/staging only — never expose in production):
`npm install @bull-board/express` — provides a visual queue dashboard at `/admin/queues`
