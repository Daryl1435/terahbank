# TerahBank — Database Index Strategy

> PostgreSQL indexes must be defined explicitly in Alembic migrations.
> Never rely on implicit indexing. Every query path below has a named index.
> Rule: If a column appears in a WHERE, ORDER BY, or JOIN clause in any service layer — it needs an index.

---

## Table: users

```sql
-- Login lookup (most frequent read)
CREATE UNIQUE INDEX idx_users_phone_number ON users(phone_number);
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- KYC admin queue filter
CREATE INDEX idx_users_kyc_status ON users(kyc_status);

-- Account status filter (suspend/close operations)
CREATE INDEX idx_users_account_status ON users(account_status);

-- Composite: KYC queue sorted by creation (admin queue ordering)
CREATE INDEX idx_users_kyc_created ON users(kyc_status, created_at DESC);
```

---

## Table: accounts

```sql
-- Primary: all accounts for a user (dashboard load)
CREATE INDEX idx_accounts_user_id ON accounts(user_id);

-- Filter by type (open standard, project, term deposit)
CREATE INDEX idx_accounts_user_type ON accounts(user_id, account_type);

-- Active accounts only (most queries exclude closed/locked)
CREATE INDEX idx_accounts_user_status ON accounts(user_id, status);

-- Term deposit maturity notification jobs
CREATE INDEX idx_accounts_maturity_date ON accounts(maturity_date)
  WHERE account_type = 'term_deposit' AND status = 'active';

-- Project account target date jobs
CREATE INDEX idx_accounts_target_date ON accounts(target_date)
  WHERE account_type = 'project' AND status = 'active';

-- Account number lookup (transfer by account number)
CREATE UNIQUE INDEX idx_accounts_account_number ON accounts(account_number);
```

---

## Table: transactions

```sql
-- User transaction history (most frequent: dashboard + history screen)
CREATE INDEX idx_transactions_credit_account ON transactions(credit_account_id, created_at DESC);
CREATE INDEX idx_transactions_debit_account ON transactions(debit_account_id, created_at DESC);

-- Status filter (admin monitoring, pending review queue)
CREATE INDEX idx_transactions_status ON transactions(status);

-- Admin monitoring: all transactions by date (paginated feed)
CREATE INDEX idx_transactions_created_at ON transactions(created_at DESC);

-- Composite: admin filter by status + date range
CREATE INDEX idx_transactions_status_created ON transactions(status, created_at DESC);

-- External reference lookup (webhook callback matching)
CREATE INDEX idx_transactions_external_ref ON transactions(external_reference)
  WHERE external_reference IS NOT NULL;

-- Idempotency key lookup (duplicate prevention — must be instant)
CREATE UNIQUE INDEX idx_transactions_idempotency ON transactions(idempotency_key)
  WHERE idempotency_key IS NOT NULL;

-- Reference lookup (human-readable TXN-XXXXX)
CREATE UNIQUE INDEX idx_transactions_reference ON transactions(reference);

-- Fraud detection: high-frequency rule (10 txns in 10 min per account)
CREATE INDEX idx_transactions_account_time ON transactions(debit_account_id, created_at DESC);

-- Channel + status for provider-specific reconciliation
CREATE INDEX idx_transactions_channel_status ON transactions(channel, status);

-- Transaction type filter (fee, interest, penalty reports)
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
```

---

## Table: cards

```sql
-- All cards for a user
CREATE INDEX idx_cards_user_id ON cards(user_id);

-- Cards linked to a specific account
CREATE INDEX idx_cards_account_id ON cards(account_id);

-- Active cards only (freeze/unfreeze check)
CREATE INDEX idx_cards_status ON cards(user_id, status);

-- Card token lookup (webhook from VISA partner)
CREATE UNIQUE INDEX idx_cards_token ON cards(card_token);
```

---

## Table: kyc_documents

```sql
-- All documents for a user
CREATE INDEX idx_kyc_user_id ON kyc_documents(user_id);

-- Pending queue (admin review)
CREATE INDEX idx_kyc_status ON kyc_documents(status, uploaded_at ASC);

-- Reviewer lookup (audit trail)
CREATE INDEX idx_kyc_reviewed_by ON kyc_documents(reviewed_by)
  WHERE reviewed_by IS NOT NULL;
```

---

## Table: audit_logs

```sql
-- Actor lookup (user activity log)
CREATE INDEX idx_audit_actor ON audit_logs(actor_id, created_at DESC);

-- Entity lookup (what happened to this account/transaction)
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id, created_at DESC);

-- Action filter (e.g. find all LOGIN_FAILED events)
CREATE INDEX idx_audit_action ON audit_logs(action, created_at DESC);

-- Time range queries (compliance export, date range filter)
CREATE INDEX idx_audit_created_at ON audit_logs(created_at DESC);

-- Admin actor filter
CREATE INDEX idx_audit_actor_type ON audit_logs(actor_type, created_at DESC);
```

---

## Table: insurance_policies

```sql
-- All policies for a user
CREATE INDEX idx_insurance_user_id ON insurance_policies(user_id);

-- Expiry notification jobs (30d, 7d before expiry)
CREATE INDEX idx_insurance_expiry ON insurance_policies(expiry_date)
  WHERE status = 'active';

-- Partner reconciliation
CREATE INDEX idx_insurance_partner ON insurance_policies(partner_id);
```

---

## Table: system_config

```sql
-- Key lookup (always PK — already indexed by default)
-- No additional indexes needed (small table, reads cached in Redis)
```

---

## Alembic Migration Convention

Every index gets its own migration file named:
`XXXX_add_indexes_{table_name}.py`

Always use `op.create_index()` with explicit `index_name` — never rely on auto-naming.

```python
# Example
op.create_index(
    'idx_transactions_status_created',
    'transactions',
    ['status', sa.text('created_at DESC')],
    postgresql_where=sa.text("status IN ('pending', 'processing')")
)
```

---

## Query Performance Rules

1. **Never query transactions without a date range** — always add `created_at >= now() - interval '90 days'` as a default filter unless explicitly fetching full history
2. **Pagination:** always cursor-based (using `created_at` + `id` as cursor) — never OFFSET-based. OFFSET scans from row 1 every time.
3. **Balance reads:** serve from Redis cache (`balance:{account_id}`, TTL 30s) — only fall through to PostgreSQL on cache miss
4. **Admin reports:** run on read replica only — never on primary write DB
5. **Audit log queries:** run on S3 archive for date ranges > 90 days old

```python
# Cursor-based pagination pattern (CORRECT)
WHERE created_at < :cursor_timestamp
  AND id < :cursor_id
ORDER BY created_at DESC, id DESC
LIMIT 20

# NEVER use this at scale
OFFSET 500 LIMIT 20  -- full table scan to row 500 every time
```

---

## Index Monitoring

Add this query to your monitoring dashboard (run weekly):
```sql
-- Find missing indexes (sequential scans on large tables)
SELECT schemaname, tablename, seq_scan, idx_scan,
       seq_scan - idx_scan AS diff
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
ORDER BY diff DESC;
```

Alert if `seq_scan > idx_scan` on `transactions`, `accounts`, or `audit_logs`.
