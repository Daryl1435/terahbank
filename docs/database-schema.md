# TerahBank — Database Schema

> **Primary DB:** PostgreSQL · **All monetary values: BIGINT (smallest XAF unit) — NEVER FLOAT**
> **All PKs:** UUID auto-generated · **All timestamps:** TIMESTAMPTZ (UTC)

---

## Table: users

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK | Auto-generated |
| full_name | VARCHAR(255) | NOT NULL | Legal name from KYC — column-level AES-256-GCM encrypted |
| phone_number | VARCHAR(20) | UNIQUE NOT NULL | E.164 format — encrypted |
| email | VARCHAR(255) | UNIQUE NOT NULL | Lowercase — encrypted |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt, cost factor 12 — NEVER plaintext |
| city | VARCHAR(100) | | |
| address | TEXT | | Encrypted |
| kyc_status | ENUM | NOT NULL | `pending` · `approved` · `rejected` |
| account_status | ENUM | NOT NULL | `active` · `suspended` · `closed` |
| preferred_language | VARCHAR(10) | DEFAULT 'fr' | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

---

## Table: accounts

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK | |
| user_id | UUID | FK → users | Owning user |
| account_type | ENUM | NOT NULL | `standard` · `project` · `term_deposit` |
| account_number | VARCHAR(20) | UNIQUE NOT NULL | Human-readable, auto-generated |
| balance | BIGINT | NOT NULL DEFAULT 0 | Smallest XAF unit. NEVER FLOAT. |
| status | ENUM | NOT NULL | `active` · `closed` · `locked` |
| project_name | VARCHAR(255) | | Project accounts only |
| target_amount | BIGINT | | Project accounts only |
| target_date | DATE | | Project accounts only |
| penalty_rate | DECIMAL(5,4) | | Early withdrawal penalty rate |
| interest_rate | DECIMAL(5,4) | | Term deposits only |
| maturity_date | DATE | | Term deposits only |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Business Rules:**
- Minimum Standard Account balance: 1,000 XAF
- Minimum initial deposit Standard: 100 XAF
- Minimum Term Deposit: 200,000 XAF
- Minimum Project Account duration: 6 months

---

## Table: transactions

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK | |
| reference | VARCHAR(50) | UNIQUE NOT NULL | e.g. `TXN-20260221-00001` |
| debit_account_id | UUID | FK → accounts, NULLABLE | Null for external deposits |
| credit_account_id | UUID | FK → accounts, NULLABLE | Null for external withdrawals |
| amount | BIGINT | NOT NULL | Smallest XAF unit — NEVER FLOAT |
| currency | VARCHAR(3) | NOT NULL DEFAULT 'XAF' | ISO 4217 |
| transaction_type | ENUM | NOT NULL | `deposit` · `withdrawal` · `transfer` · `fee` · `interest` · `penalty` |
| channel | ENUM | NOT NULL | `mtn_momo` · `orange_money` · `visa` · `mastercard` · `internal` |
| status | ENUM | NOT NULL | `pending` · `processing` · `success` · `failed` · `reversed` |
| external_reference | VARCHAR(255) | | Reference ID from external payment provider |
| metadata | JSONB | | Provider-specific response data — audit only |
| initiated_by | UUID | FK → users | User or admin who triggered |
| idempotency_key | VARCHAR(255) | UNIQUE | Prevents duplicate processing |
| created_at | TIMESTAMPTZ | NOT NULL | |
| completed_at | TIMESTAMPTZ | | Nullable |

**Transaction State Machine:** `pending` → `processing` → `success` OR `failed` · `success` → `reversed`

---

## Table: cards

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK | |
| user_id | UUID | FK → users | |
| account_id | UUID | FK → accounts | Linked Standard Account only |
| card_token | VARCHAR(255) | NOT NULL | Tokenized reference from VISA partner — NEVER raw PAN |
| last_four | CHAR(4) | NOT NULL | Display only |
| expiry_date | DATE | NOT NULL | |
| status | ENUM | NOT NULL | `active` · `frozen` · `expired` · `cancelled` |
| daily_limit | BIGINT | | |
| per_transaction_limit | BIGINT | | |
| created_at | TIMESTAMPTZ | NOT NULL | |

---

## Table: kyc_documents

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK | |
| user_id | UUID | FK → users | |
| document_type | ENUM | NOT NULL | `national_id` · `passport` · `residence_permit` |
| storage_key | VARCHAR(500) | NOT NULL | Encrypted S3 object key — never expose directly |
| status | ENUM | NOT NULL | `pending` · `approved` · `rejected` |
| reviewed_by | UUID | FK → users (admin) | |
| rejection_reason | TEXT | | |
| reviewed_at | TIMESTAMPTZ | | |
| uploaded_at | TIMESTAMPTZ | NOT NULL | |

---

## Table: audit_logs

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | UUID | PK | |
| actor_id | UUID | FK → users | User or admin who performed action |
| actor_type | ENUM | NOT NULL | `user` · `admin` · `system` |
| action | VARCHAR(100) | NOT NULL | e.g. `LOGIN_SUCCESS` · `KYC_APPROVED` · `TRANSFER_INITIATED` |
| entity_type | VARCHAR(50) | | e.g. `account` · `transaction` · `user` |
| entity_id | UUID | | ID of the affected entity |
| ip_address | INET | | |
| user_agent | TEXT | | |
| metadata | JSONB | | Before/after state for mutations — redacted of sensitive fields |
| created_at | TIMESTAMPTZ | NOT NULL | **IMMUTABLE — no UPDATE or DELETE ever** |

**CRITICAL:** No application service account has UPDATE or DELETE on `audit_logs`.
Audit logs replicated to AWS S3 with Object Lock (Compliance Mode, 7-year retention) within 60 seconds.

---

## Table: system_config

| Column | Type | Notes |
|---|---|---|
| key | VARCHAR(100) PK | e.g. `penalty_rate_project` · `term_deposit_interest_rate` · `max_virtual_cards_per_user` |
| value | TEXT | |
| updated_by | UUID FK → users | Super Admin only |
| updated_at | TIMESTAMPTZ | |

---

## Table: insurance_policies

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| partner_id | VARCHAR(100) | External insurance partner reference |
| policy_type | ENUM | `health` · `device` · `micro` |
| policy_number | VARCHAR(255) | From partner system |
| status | ENUM | `active` · `expired` · `cancelled` |
| start_date | DATE | |
| expiry_date | DATE | |
| created_at | TIMESTAMPTZ | |

---

## Key Relationships

| Relationship | Cardinality |
|---|---|
| users → accounts | 1 : MANY |
| users → cards | 1 : MANY |
| accounts → transactions (debit) | 1 : MANY |
| accounts → transactions (credit) | 1 : MANY |
| users → kyc_documents | 1 : MANY |
| users → audit_logs | 1 : MANY |
| users → insurance_policies | 1 : MANY |

## Redis Key Schema

| Key Pattern | TTL | Purpose |
|---|---|---|
| `session:{user_id}:{device_id}` | 7 days | Refresh token storage |
| `otp:{user_id}:{type}` | 5 min | OTP (single-use, deleted on validation) |
| `balance:{account_id}` | 30 sec | Cached account balance |
| `config:{key}` | 1 hr | System config cache |
| `insurance:catalog` | 6 hrs | Insurance products cache |
| `presigned:{document_id}` | 5 min | KYC S3 presigned URL cache |
