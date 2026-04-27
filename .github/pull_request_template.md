## What does this PR do?

<!-- One paragraph summary. Link the relevant milestone from docs/implementation-plan.md -->

Milestone: <!-- e.g. 1.1 — Auth Backend -->
FR(s): <!-- e.g. FR-001, FR-002 -->

---

## Checklist

### Code
- [ ] Follows module pattern: `router.py` → `service.py` → `repository.py`
- [ ] All new functions have Python type hints / TypeScript types
- [ ] No hardcoded secrets, API keys, or credentials

### Financial rules (skip if no financial code changed)
- [ ] All money is BIGINT — no float, no Decimal in DB columns
- [ ] All financial DB writes are wrapped in a PostgreSQL transaction
- [ ] Transaction endpoints have `Idempotency-Key` header enforcement
- [ ] KYC gate (`require_kyc_approved`) applied to all transaction routes
- [ ] `write_audit_log()` called before returning from every mutation
- [ ] Payment BullMQ jobs use `attempts=1` (never auto-retry)

### Tests
- [ ] Unit tests added / updated (min 80% coverage maintained)
- [ ] Financial calculation tests present if any money math was changed
- [ ] External services (MoMo, SendGrid, S3) mocked in tests

### DB (skip if no schema changes)
- [ ] Alembic migration generated and reviewed
- [ ] Migration has a working `downgrade()` function
- [ ] No `UPDATE` or `DELETE` added to `audit_logs`

### i18n (skip if no user-facing strings added)
- [ ] New strings added to both `fr.json` (source of truth) and `en.json`
- [ ] No hardcoded French or English text in components

---

## How to test this PR locally

```bash
# e.g.
cd apps/api
pytest tests/unit/test_financial_calculations.py -v
```

---

## Screenshots / recordings (if UI changes)

<!-- Drop screenshots or Loom link here -->
