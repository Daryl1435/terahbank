# TerahBank — Security & Compliance Reference

---

## Data Encryption Strategy

| Layer | Implementation |
|---|---|
| Data at rest (DB) | Transparent Data Encryption (TDE) at PostgreSQL engine level |
| Sensitive columns | AES-256-GCM column-level encryption: full_name, phone_number, email, address, kyc_documents.storage_key |
| Key management | AWS KMS — keys never stored in application code or DB |
| Data in transit | TLS 1.3 enforced. TLS 1.2 disabled on load balancer. |
| Web headers | HSTS enforced on all web-facing endpoints |
| Certs | AWS Certificate Manager — automated rotation |

---

## Auth Security

| Mechanism | Implementation |
|---|---|
| JWT Access Tokens | RS256 (asymmetric). 15-min expiry. Private key never leaves auth service. |
| Refresh Tokens | 7-day expiry. Stored in Redis with user-device binding. Invalidated on logout or suspicious activity. |
| OTP | 6-digit codes, cryptographically secure PRNG. Redis, 5-min TTL, single-use (deleted on first validation). |
| Password Hashing | bcrypt, cost factor 12. Never SHA or MD5. NEVER stored in plaintext. |
| Admin MFA | TOTP (RFC 6238) for admin accounts in addition to OTP. |
| API Gateway Auth | Gateway (Kong or AWS API Gateway) validates JWT on every inbound request. Backend trusts gateway validation. |
| Failed login lockout | After 5 failed attempts: account locked for 30 minutes. |
| OTP resend limit | Max 3 resends per session. Session locked 30 min after limit. |

---

## Audit Logging Architecture

**Rule: No application service account has UPDATE or DELETE on audit_logs table — ever.**

Every entry must capture:
- actor_id (user ID)
- ip_address + device fingerprint
- action code (e.g. LOGIN_SUCCESS, KYC_APPROVED, TRANSFER_INITIATED)
- entity_type + entity_id (affected object)
- before + after state (for mutations — redacted of sensitive fields)
- precise UTC timestamp

**Replication:** Audit logs replicated to AWS S3 with Object Lock (Compliance Mode, 7-year retention) within 60 seconds of creation.

**Audit log action code standards:**
- Auth: `LOGIN_SUCCESS`, `LOGIN_FAILED`, `LOGOUT`, `OTP_REQUESTED`, `OTP_VERIFIED`, `DEVICE_REGISTERED`
- Account: `ACCOUNT_OPENED`, `ACCOUNT_CLOSED`, `BALANCE_UPDATED`
- Transaction: `TRANSFER_INITIATED`, `DEPOSIT_SUCCESS`, `WITHDRAWAL_FAILED`, etc.
- Admin: `KYC_APPROVED`, `KYC_REJECTED`, `CONFIG_UPDATED`, `USER_SUSPENDED`

---

## PCI-DSS Alignment

TerahBank is **SAQ-A scope** (lightest tier) because:
- Raw cardholder data (PAN, CVV, expiry) NEVER stored, processed, or transmitted by TerahBank
- All card operations tokenized through a PCI-DSS Level 1 certified VISA issuing partner
- Only `card_token` (opaque reference) and `last_four` stored — not cardholder data under PCI-DSS
- Partner agreement must confirm PCI-DSS certification status in writing

---

## Fraud Detection Rules (Phase 1 — Configurable by Admin)

| Rule | Threshold | Action |
|---|---|---|
| Large single transaction | > 5,000,000 XAF in single deposit or withdrawal | Flag → Pending Review |
| High frequency | > 10 transactions from single account within 10-minute window | Flag → Pending Review |
| New device + large withdrawal | Login from new device followed immediately by large withdrawal | Flag → Pending Review |
| New account recipient | Transaction to an account created within last 24 hours | Flag → Pending Review |

Flagged transactions go to `Pending Review` state and surface in Admin transaction monitoring feed.
Rules engine must be configurable by admins without code changes.

---

## Regulatory Compliance

| Requirement | Implementation |
|---|---|
| KYC before first transaction | `kyc_status != 'approved'` → 403 on all transaction endpoints |
| AML transaction monitoring | Fraud detection rules engine with configurable thresholds and manual review queue |
| Data residency (CEMAC) | AWS `af-south-1` (Cape Town) — confirm COBAC acceptance before go-live |
| 7-year audit retention | S3 with Object Lock (Compliance Mode) |
| User data export | GET /users/me/data-export — downloadable JSON of all user data |
| Account deletion | DELETE /users/me → 'closed' status + PII redacted after mandatory retention period |
| Consent records | Terms acceptance stored with timestamp and app version at registration |
| KYC document handling | S3 presigned URLs with short TTLs — never direct DB storage of documents |

---

## Security Checklist (Pre-Launch)

- [ ] External penetration test completed
- [ ] OWASP Top 10 addressed in CI/CD SAST/DAST scans
- [ ] TLS 1.2 disabled on load balancer — TLS 1.3 only
- [ ] HSTS headers deployed on all web endpoints
- [ ] AWS KMS key rotation enabled
- [ ] S3 KYC bucket: server-side encryption + access logging enabled
- [ ] audit_logs table: UPDATE/DELETE privileges revoked from API service account
- [ ] S3 Object Lock (Compliance Mode, 7-year) configured for audit archive bucket
- [ ] Incident response plan documented and tested
- [ ] Cyber insurance policy obtained
- [ ] Load test completed: 500 concurrent sessions + webhook flood at 10x peak
