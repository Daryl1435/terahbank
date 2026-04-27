# TerahBank — Functional Requirements Checklist

> Track implementation progress. Claude Code can check off `[x]` as items are completed.
> All items tagged with FR-XXX IDs for traceability to SRS v1.0.

---

## 4.1 Authentication & Onboarding

- [ ] FR-001 — User registration: full name, phone, email, city, address
- [ ] FR-002 — OTP via SMS and/or email for phone/email verification
- [ ] FR-003 — Password complexity: min 10 chars, 1 uppercase, 1 number, 1 special char
- [ ] FR-004 — Login via phone number or email + password
- [ ] FR-005 — 2FA via OTP at every login event
- [ ] FR-006 — Mobile: PIN and biometric (fingerprint/face) auth for subsequent sessions
- [ ] FR-007 — Device recognition + flag unrecognized devices for additional verification
- [ ] FR-008 — Auto session termination after 15 min inactivity
- [ ] FR-009 — Full activity log for every authentication event per user

## 4.2 Standard Savings Account

- [ ] FR-010 — Verified user can open Standard Savings Account at no charge
- [ ] FR-011 — Min initial deposit: 100 XAF · Min maintained balance: 1,000 XAF
- [ ] FR-012 — Deposits/withdrawals at zero transaction fee from/to Mobile Money or card
- [ ] FR-013 — Real-time balance display on deposit and withdrawal
- [ ] FR-014 — Monthly savings summary via in-app notification and email
- [ ] FR-015 — Savings insight message on dashboard (e.g. 'You saved 23% more this month') [Should Have]

## 4.3 Project Account (Vault)

- [ ] FR-016 — Create Project Account: name, target amount, duration (min 6 months)
- [ ] FR-017 — Visual progress bar showing % of target saved
- [ ] FR-018 — Admin-configurable early withdrawal penalty percentage
- [ ] FR-019 — Apply early withdrawal penalty when user withdraws before duration ends
- [ ] FR-020 — Milestone notifications at 25%, 50%, 75%, 100% of target
- [ ] FR-021 — Optional auto-save rule (e.g. 5,000 XAF every Friday) [Should Have]
- [ ] FR-022 — Multiple active Project Accounts simultaneously per user

## 4.4 Term Deposit Account

- [ ] FR-023 — Open Term Deposit: min 200,000 XAF
- [ ] FR-024 — Fixed interest rate: 2.0% per annum on principal
- [ ] FR-025 — Interest calculator shown before user confirms term deposit
- [ ] FR-026 — Early break penalty: 1.5% of principal if withdrawn before maturity
- [ ] FR-027 — Visible countdown timer to maturity date on dashboard
- [ ] FR-028 — Maturity notifications at 14 days, 7 days, 1 day before maturity date

## 4.5 Virtual VISA Card

- [ ] FR-029 — Issue virtual prepaid VISA card linked to Standard Savings Account
- [ ] FR-030 — Freeze and unfreeze card instantly from mobile app
- [ ] FR-031 — Configurable spending limits: per transaction and per day
- [ ] FR-032 — Full transaction history: merchant name, amount, date, status
- [ ] FR-033 — Multiple virtual cards per user (up to admin-defined limit) [Should Have]

## 4.6 Internal Transfers (TerahWallet)

- [ ] FR-034 — Transfer between own accounts instantly (Standard → Project etc.)
- [ ] FR-035 — Transfer to another TerahBank user by phone number or account ID
- [ ] FR-036 — Require PIN or biometric confirmation before any transfer
- [ ] FR-037 — Full, searchable transfer history per user

## 4.7 Funding & Withdrawals

- [ ] FR-038 — Deposits via: MTN MoMo, Orange Money, VISA, MasterCard
- [ ] FR-039 — Withdrawals to: MTN MoMo and Orange Money
- [ ] FR-040 — Auto-detect failed payment attempts → clear actionable error message
- [ ] FR-041 — Real-time transaction status: Pending, Processing, Success, Failed

## 4.8 Insurance Services [All Should Have]

- [ ] FR-042 — Display available insurance products from integrated partners
- [ ] FR-043 — Initiate policy purchase referral to partner system
- [ ] FR-044 — Policy Dashboard showing active policies
- [ ] FR-045 — Renewal reminders at 30 and 7 days before policy expiry

## 4.9 User Dashboard

- [ ] FR-046 — Total balance (aggregate all accounts) displayed prominently
- [ ] FR-047 — Individual account balances with tap-to-expand detail view
- [ ] FR-048 — Quick-action buttons: Deposit, Withdraw, Transfer
- [ ] FR-049 — Notification bell with unread count
- [ ] FR-050 — Profile access and update (name, contact, password, biometric settings)

## 4.10 Admin Back-Office

- [ ] FR-051 — Searchable/paginated user list: view, edit, suspend, close account
- [ ] FR-052 — KYC verification queue: approve or reject with documented reasons
- [ ] FR-053 — Real-time transaction monitoring feed with full filters
- [ ] FR-054 — Configure global parameters: interest rates, penalty %, spending limits
- [ ] FR-055 — Exportable reports: CSV and PDF (transactions, user activity, insurance commissions)
- [ ] FR-056 — RBAC: Super Admin, Operations Staff, Read-Only Analyst

---

## Non-Functional Requirements Checklist

### Performance
- [ ] API read latency P95 < 300ms
- [ ] API write latency P95 < 600ms
- [ ] Page load mobile 4G < 3s first meaningful paint
- [ ] Support 500 concurrent sessions at launch
- [ ] DB query P99 < 100ms for indexed reads

### Security
- [ ] AES-256 encryption for PII at rest (column-level)
- [ ] TLS 1.3 enforced — no HTTP fallback
- [ ] bcrypt cost factor 12 for passwords
- [ ] JWT RS256, 15-min expiry
- [ ] OTP: single-use, 6-digit, 5-min TTL
- [ ] PCI-DSS alignment: no raw card data stored
- [ ] OWASP Top 10 in CI/CD SAST/DAST scans
- [ ] Pre-launch external penetration test

### Compliance
- [ ] COBAC compliance facilitated
- [ ] KYC before any financial transaction (kyc_status gate)
- [ ] AML rules engine (configurable thresholds)
- [ ] Data residency: AWS af-south-1 (Cape Town)
- [ ] Audit log immutable, 7-year retention (S3 Object Lock)
- [ ] User data export endpoint (GDPR-equivalent)
- [ ] Account deletion with PII redaction after retention

### Usability
- [ ] WCAG 2.1 Level AA
- [ ] Primary flows completable in ≤ 4 taps from dashboard
- [ ] French and English at launch
- [ ] Font size adjustable in app (small/medium/large)
