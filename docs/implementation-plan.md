# TerahBank — Implementation Plan

> Use `ultrathink` when planning complex financial logic.
> Reference this file in Claude Code with @docs/implementation-plan.md
> Check off `[x]` as milestones and tasks are completed.

---

## Phase 0 — Project Setup & Infrastructure (Week 1–2)

### Milestone 0.1 — Monorepo & Dev Environment
- [x] Initialize monorepo structure (apps/api, apps/mobile, apps/web, apps/admin, docs, infrastructure)
- [x] Set up root CLAUDE.md and all sub-CLAUDE.md files
- [x] Configure GitHub repository and branch protection rules (see .github/branch-protection.md — apply manually in GitHub Settings)
- [x] Set up GitHub Actions CI/CD skeleton (.github/workflows/ci.yml, deploy-staging.yml, deploy-production.yml)
- [x] Write unit tests for: all modules covered (auth, accounts, project, term_deposit, transfers, momo, orange, visa/card, admin, kyc, insurance, notifications — 22 test files, 300+ tests)

### Milestone 0.2 — Backend Skeleton
- [x] Initialize FastAPI project in apps/api
- [x] Set up module folder structure (auth, accounts, transactions, cards, admin, insurance, notifications, kyc)
- [x] Configure PostgreSQL connection (SQLAlchemy async + asyncpg, core/database.py)
- [x] Configure Redis connection (core/redis.py — async client, key helpers, lifespan init/close)
- [x] Set up Pydantic v2 base models and settings (core/config.py, core/schemas.py)
- [x] Create base response schema (TerahResponse + TerahErrorResponse in core/schemas.py)
- [x] Set up CORS, middleware, error handlers (RequestIDMiddleware, HTTPException handler, ValidationError handler, 500 catch-all)
- [x] Auto-generate OpenAPI docs available at /docs (confirmed running at http://localhost:8000/docs)

### Milestone 0.3 — Database Bootstrap
- [x] Create initial Alembic migration: users, accounts, transactions, cards, kyc_documents, audit_logs, system_config, insurance_policies tables
- [x] Enforce: NO UPDATE or DELETE privileges on audit_logs for API service account
- [x] Write unit tests for: money arithmetic (BIGINT, XAF, never FLOAT)

### Milestone 0.4 — Frontend Skeletons
- [x] Initialize React Native + Expo project in apps/mobile
- [x] Initialize Next.js project in apps/web (customer portal)
- [x] Initialize Next.js project in apps/admin (back-office)
- [x] Set up TerahBank Design System tokens (colors, typography, spacing) as shared package
- [x] Configure Poppins + Roboto fonts across all apps

---

## Phase 1 — Authentication & Onboarding (Week 3–4)

### Milestone 1.1 — Auth Backend
- [x] FR-001: POST /auth/register — full user creation
- [x] FR-002: OTP generation (crypto secure PRNG) + SMS/email dispatch + Redis storage (5-min TTL)
- [x] FR-003: Password complexity validation (Pydantic)
- [x] FR-004: POST /auth/login — credentials + returns tokens
- [x] FR-005: 2FA OTP enforcement at every login
- [x] FR-007: Device fingerprinting + unrecognized device flagging
- [x] FR-008: 15-min session inactivity auto-termination (JWT 15-min access token + appStore.isSessionExpired() on mobile)
- [x] FR-009: Audit log entries for all auth events
- [x] POST /auth/refresh, /auth/logout, /auth/resend-otp, /auth/change-password
- [x] Write unit tests for: OTP expiry, 5-failed-attempt lockout, session timeout, device recognition

### Milestone 1.2 — KYC Flow
- [x] FR post-registration: KYC document upload (multipart → S3 encrypted, AES256 SSE)
- [x] Account status gating: all transaction routes return 403 if kyc_status != 'approved'
- [x] Admin KYC queue: GET /admin/kyc/queue + POST /admin/kyc/:userId/decision
- [x] Audit log on every KYC decision (with admin ID + timestamp)
- [x] User notification on KYC approval and rejection (with reason) — stub logged; BullMQ dispatch in Milestone 6.2
- [x] Write unit tests for: KYC gate enforcement, rejection reason storage

### Milestone 1.3 — Auth Mobile UI (React Native)
- [x] FR-006: PIN setup screen and biometric authentication flow
- [x] Registration screen (name, phone, email, city, address)
- [x] OTP verification screen (resend timer, max 3 resends)
- [x] Password creation screen (complexity meter)
- [x] KYC document upload screen (camera capture + gallery)
- [x] Login screen (phone/email + password + OTP 2FA)
- [x] Device verification email confirmation flow

---

## Phase 2 — Core Accounts (Week 5–6)

### Milestone 2.1 — Standard Savings Account Backend
- [x] FR-010: POST /accounts/standard — open Standard Account
- [x] FR-011: Enforce min initial deposit 100 XAF + min maintained balance 1,000 XAF
- [x] FR-013: Real-time balance update on deposit/withdrawal (Redis cache — 30s TTL; invalidate-before-write; apply_balance_delta for Milestone 3)
- [x] FR-014: Monthly savings summary job (BullMQ scheduled — cron 0 7 1 * * UTC; notification dispatch stubbed for Milestone 6.2)
- [x] FR-015: Savings insight calculation [Should Have] — calculate_savings_insight() implemented; wired to Milestone 3 transaction data
- [x] Write unit tests for: min balance enforcement, balance update atomicity (47 tests, all passing)

### Milestone 2.2 — Project Account (Vault) Backend
- [x] FR-016: POST /accounts/project — name, target_amount, target_date (min 6 months)
- [x] FR-017: Progress bar calculation (balance / target_amount * 100)
- [x] FR-018 + FR-019: Early withdrawal penalty (admin-configurable rate from system_config; snapshotted at account creation)
- [x] FR-020: Milestone notifications at 25%, 50%, 75%, 100%
- [x] FR-021: Auto-save rule configuration + BullMQ scheduled execution [Should Have]
- [x] FR-022: Multiple active Project Accounts per user
- [x] Write unit tests for: penalty calculation edge cases, milestone trigger logic, minimum duration enforcement (41 tests, all passing)

### Milestone 2.3 — Term Deposit Backend
- [x] FR-023: POST /accounts/term-deposit — min 200,000 XAF
- [x] FR-024: 2.0% per annum interest calculation (pro-rata, BIGINT floor, never float)
- [x] FR-025: GET /accounts/term-deposit/calculator — pre-confirmation interest projection
- [x] FR-026: Early break penalty 1.5% of principal (snapshotted at creation)
- [x] FR-027: Maturity countdown calculation (days_to_maturity in AccountData)
- [x] FR-028: Maturity notification BullMQ job at 14d, 7d, 1d before maturity (daily 07:00 UTC)
- [x] DELETE /accounts/{id}: close account (zero balance required)
- [x] Write unit tests for: interest calculation (BIGINT, no rounding errors), early break penalty, maturity date edge cases (45 tests, all passing)

### Milestone 2.4 — Account UI (Mobile + Web)
- [x] Dashboard: FR-046, FR-047, FR-048, FR-049, FR-050
- [x] Standard Account detail view
- [x] Project Account creation flow + progress bar UI
- [x] Term Deposit creation flow + interest calculator UI
- [x] Maturity countdown timer component

---

## Phase 3 — Transactions & Funding (Week 7–9)

### Milestone 3.1 — Internal Transfers
- [x] FR-034: Transfer between own accounts
- [x] FR-035: Transfer to another TerahBank user (phone or account ID or account number)
- [x] FR-036: PIN confirmation before processing (POST /auth/setup-pin + /auth/verify-pin → single-use pin_token)
- [x] FR-037: Searchable transfer history (account_id, type, status, date_from, date_to, paginated)
- [x] Idempotency key enforcement on all transfer endpoints
- [x] Atomic DB writes (PostgreSQL transactions) — no partial success ever
- [x] Write unit tests for: duplicate idempotency key rejection, insufficient balance, self-transfer edge case (44 tests, all passing)

### Milestone 3.2 — MTN MoMo Integration
- [x] FR-038: POST /transactions/deposit (MTN MoMo channel)
- [x] UC-003: Async queue-based MoMo payment flow
- [x] POST /webhooks/mtn-momo: callback handler with signature validation
- [x] FR-040: Failed payment detection + user notification (stub logged; push/SMS in Milestone 6.2)
- [x] FR-041: Real-time transaction status (pending → processing → success/failed)
- [x] Write unit tests for: webhook signature validation, timeout handling (120s), callback success/failure state transitions (22 tests, all passing)

### Milestone 3.3 — Orange Money Integration ✅
- [x] FR-038: Orange Money deposit (channel=orange_money enabled; OAuth client_credentials auth, Redis token cache)
- [x] FR-039: Orange Money + MTN MoMo withdrawal (3-step mobile UI; debit-first + compensating credit on failure)
- [x] POST /webhooks/orange-money: callback handler with HMAC-SHA256 validation; CANCELLED/EXPIRED → FAILED; withdrawal failure → compensating credit
- [x] Write unit tests: 28 tests — signature validation, deposit/withdraw service, webhook state machine, timeout handlers (28 passing)

### Milestone 3.4 — VISA/MasterCard Integration ✅
- [x] FR-038: Card deposit flow (VISA/MC hosted payment session via VisaGatewayClient); deposit() returns CardDepositSessionData with payment_url
- [x] PCI-DSS SAQ-A: raw card data never reaches TerahBank servers; VISA partner hosts payment page; only card_token + last_four + expiry_date stored
- [x] core/visa_gateway.py: VisaGatewayClient (create_payment_session, issue_virtual_card, update_card_status, get_payment_status) + validate_visa_webhook_signature (HMAC-SHA256)
- [x] POST /webhooks/visa-card: HMAC-SHA256 validation + CardService.handle_visa_deposit_webhook (SUCCESSFUL credits account, FAILED marks failed, duplicate guard, always returns 200)
- [x] FR-029: POST /cards — issue virtual prepaid VISA card (Standard Account only, card limit enforced)
- [x] FR-030: PATCH /cards/:id/freeze and /unfreeze (local DB + best-effort partner notification)
- [x] FR-031: PATCH /cards/:id/limits — per-transaction + daily
- [x] FR-032: GET /cards/:id/transactions (card channel filter)
- [x] FR-033: VISA_MAX_CARDS_PER_USER = 3 (admin-configurable in config/env)
- [x] Mobile: DepositScreen VISA channel enabled, CardPaymentWebViewScreen (react-native-webview, success/cancel URL detection), CardScreen (list, freeze/unfreeze, limits modal, issue card)
- [x] Write unit tests: 25 tests — signature validation (6), issue_card (5), list_cards (1), freeze (3), unfreeze (2), update_limits (3), handle_visa_deposit_webhook (5), deposit visa channel (2)

### Milestone 3.5 — Transaction UI ✅
- [x] Deposit flow: channel selection, amount, confirmation (MTN MoMo + Orange Money active; VISA/MC now active with WebView payment)
- [x] Withdrawal flow: 3-step UI (channel selection, amount + destination phone, PIN confirmation)
- [x] Transfer flow: recipient lookup, amount, PIN confirmation (PINKeypad, verifyPin → pin_token)
- [x] Transaction history list with filters (All | Pending | Successful | Failed, pull-to-refresh)
- [x] Transaction detail view (type, channel, amount, status, date, reference)
- [x] Real-time status polling UI (3s interval, stops at terminal status or 125s timeout)

---

## Phase 4 — Virtual VISA Card (Week 10)

### Milestone 4.1 — Card Backend ✅ (completed in Milestone 3.4)
- [x] FR-029: POST /cards — issue virtual prepaid VISA card
- [x] FR-030: PATCH /cards/:id/freeze and /unfreeze
- [x] FR-031: PATCH /cards/:id/limits — per-transaction + daily
- [x] FR-032: GET /cards/:id/transactions
- [x] FR-033: Multiple cards per user (admin-configured limit, default 3)
- [x] VISA card-issuing partner integration (tokenized — card_token only stored)
- [x] POST /webhooks/visa-card: card transaction notifications with HMAC-SHA256 validation
- [x] Write unit tests for: freeze/unfreeze guards, limit enforcement, token-only storage, webhook state machine

### Milestone 4.2 — Card UI ✅
- [x] Card management screen (CardScreen — tappable list, issue new card FAB, pull-to-refresh)
- [x] Card detail view (CardDetailScreen — card art with chip, masked number, expiry, status badge, frozen overlay)
- [x] Freeze/unfreeze toggle with instant feedback (loading state, optimistic status display)
- [x] Spending limit configuration UI (inline editor in CardDetailScreen — daily + per-transaction)
- [x] Card transaction history (shortcut to TransactionHistory filtered by card's account)
- [x] Dashboard "My Cards" shortcut (between quick actions and accounts list)
- [x] Navigation wired: Dashboard → Cards → CardDetail, CardDetail → TransactionHistory

---

## Phase 5 — Admin Back-Office (Week 11–12)

### Milestone 5.1 — Admin Backend ✅
- [x] FR-051: GET + PATCH /admin/users (paginated, searchable, status management)
- [x] FR-053: GET /admin/transactions (real-time monitoring, full filters)
- [x] FR-054: GET + PATCH /admin/config (Super Admin only for PATCH)
- [x] FR-055: Exportable reports — CSV (transactions, user activity); PDF deferred to post-launch
- [x] FR-056: RBAC — super_admin, operations_staff, read_only_analyst roles (JWT type=admin_access + role claim)
- [x] Fraud detection rules engine (Phase 1 rules: large single transaction, 10 txns in 10min window, new device + large withdrawal, txn to account created < 24h ago)
- [x] Write unit tests for: RBAC enforcement, fraud flag triggers, report generation (33 tests)

### Milestone 5.2 — Admin Web UI (Next.js) ✅
- [x] Login page (admin-only, 2-step: credentials → TOTP; backend TOTP verify endpoint pending)
- [x] Dashboard: KPIs (total users, pending KYC, monthly transactions, fraud alerts, monthly volume)
- [x] User list with search/filter/pagination (search name/email/phone, kyc_status, account_status)
- [x] User detail view with account management actions (suspend/close/reactivate with confirm modal)
- [x] KYC queue (approve/reject with reason dropdown, 30s auto-refresh)
- [x] Transaction monitoring feed (full filters, 15s auto-refresh)
- [x] System config editor (inline edit with validation, super_admin only)
- [x] Report generation + download (CSV — transactions with date range, users)
- [x] RBAC: hide/disable UI elements based on role; /config hidden for non-super_admin; middleware auth guard

---

## Phase 6 — Insurance & Notifications (Week 13)

### Milestone 6.1 — Insurance [Should Have] ✅
- [x] FR-042: GET /insurance/products — partner product catalog
- [x] FR-043: POST /insurance/policies — referral initiation
- [x] FR-044: Policy Dashboard in mobile app
- [x] FR-045: Renewal reminder jobs (BullMQ at 30d and 7d before expiry)
- [x] Insurance commission tracking in admin reports

### Milestone 6.2 — Notifications System ✅
- [x] Push notifications via FCM (all milestone, transaction, maturity events)
- [x] Email notifications via SendGrid (monthly summary, KYC status, maturity alerts)
- [x] SMS notifications (OTP, critical security alerts)
- [x] In-app notification bell with unread count (FR-049)
- [x] Notification preferences management (FR-050)

---

## Phase 7 — QA, Security & Launch Prep (Week 14–16)

### Milestone 7.1 — Security ✅
- [ ] External penetration test — manual: engage an external firm before launch
- [x] OWASP Top 10 audit in CI/CD pipeline — Bandit + Semgrep (p/owasp-top-ten) + pip-audit in security-scan CI job
- [x] Load test: 500 concurrent sessions, webhook callback flood at 10x peak — Locust script at apps/api/scripts/load_test.py
- [x] HSTS headers enforced on all web endpoints — SecurityHeadersMiddleware in main.py (skipped in dev, active in staging/prod)
- [ ] TLS 1.3 — disable TLS 1.2 on load balancer — infra task: set in AWS ALB listener settings before launch

### Milestone 7.2 — Compliance
- [ ] Confirm AWS af-south-1 accepted by COBAC for data residency
- [ ] Audit log S3 replication + Object Lock (Compliance Mode, 7-year) verified
- [ ] KYC gate tested end-to-end (no transaction without approved KYC)
- [ ] User data export endpoint tested
- [ ] Account deletion + PII redaction flow tested

### Milestone 7.3 — Accessibility & UX
- [ ] WCAG 2.1 Level AA audit (mobile + web) — manual audit required before launch
- [ ] All primary flows completable in ≤ 4 taps from dashboard — manual verification required
- [x] French and English language switch working — LanguageScreen on first launch, ProfileScreen toggle, LoginScreen pill, full i18n coverage
- [x] Font size adjustment (small/medium/large) working — ProfileScreen selector, SecureStore persistence, restored on startup
- [x] prefers-reduced-motion respected on all animations — useReducedMotion hook in hooks/useReducedMotion.ts

### Milestone 7.4 — Performance
- [ ] API read P95 < 300ms confirmed under load
- [ ] API write P95 < 600ms confirmed under load
- [ ] Mobile 4G page load < 3s confirmed
- [ ] Redis caching confirmed working (balance cache, config cache, OTP TTL)

### Milestone 7.5 — Launch
- [ ] Production Terraform infrastructure provisioned (AWS af-south-1)
- [ ] GitHub Actions CI/CD pipeline fully functional
- [ ] Monitoring and alerting configured (Datadog or CloudWatch)
- [ ] Incident response plan documented
- [ ] Scheduled maintenance window communicated (02:00–04:00 CAT)
- [ ] Beta testing with target personas (Amina, Jean-Baptiste, Esther)
