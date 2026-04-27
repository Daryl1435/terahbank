# TerahBank — API Endpoints Reference

> Base path: `/api/v1/`
> All endpoints require `Authorization: Bearer <JWT>` unless marked **[PUBLIC]**
> TLS 1.3 enforced — no HTTP fallback
> JWT: RS256, 15-min access token · 7-day refresh token

## Standard Response Format

```json
{
  "success": true,
  "data": {},
  "message": "Optional human-readable message",
  "timestamp": "2026-02-21T10:30:00Z"
}
```

Error format:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "User-friendly message",
    "details": {}
  },
  "timestamp": "2026-02-21T10:30:00Z"
}
```

---

## Auth Endpoints [PUBLIC]

| Method | Route | Description |
|---|---|---|
| POST | `/auth/register` | Create new user. Triggers OTP dispatch. |
| POST | `/auth/verify-otp` | Verify OTP. Returns JWT tokens. |
| POST | `/auth/login` | Authenticate with credentials. Returns access + refresh tokens. |
| POST | `/auth/refresh` | Exchange valid refresh token for new access token. |
| POST | `/auth/logout` | Invalidate current session's refresh token in Redis. |
| POST | `/auth/resend-otp` | Resend OTP (max 3 times per session, locks 30min after). |
| POST | `/auth/change-password` | Authenticated user changes password. |

---

## User & KYC Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/users/me` | Current user profile. |
| PATCH | `/users/me` | Update name, address, notification preferences. |
| POST | `/users/me/kyc` | Upload KYC documents (multipart/form-data → S3). Triggers admin review. |
| GET | `/users/me/activity-log` | Paginated auth and security activity log. |
| GET | `/users/me/data-export` | GDPR-equivalent: downloadable JSON of all user data. |
| DELETE | `/users/me` | Close account (marks as 'closed', PII redacted after retention period). |

---

## Admin — User & KYC Endpoints [ADMIN ONLY]

| Method | Route | Role Required | Description |
|---|---|---|---|
| GET | `/admin/users` | Operations+ | Paginated user list with search/filter. |
| PATCH | `/admin/users/:id/status` | Operations+ | Set account status (active, suspended, closed). |
| GET | `/admin/kyc/queue` | Operations+ | Pending KYC applications queue. |
| POST | `/admin/kyc/:userId/decision` | Operations+ | Approve or reject KYC with reason. |

---

## Account Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/accounts` | List all accounts for authenticated user. |
| GET | `/accounts/:id` | Detailed account view — balance, settings, progress (if project). |
| POST | `/accounts/standard` | Open Standard Savings Account. |
| POST | `/accounts/project` | Create Project Account (Vault): name, target_amount, target_date. |
| PATCH | `/accounts/project/:id` | Update auto-save rule or project name. |
| POST | `/accounts/term-deposit` | Open Term Deposit: amount (min 200,000 XAF), duration. |
| DELETE | `/accounts/:id` | Request account closure (requires zero balance). |

---

## Transaction Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/transactions` | Paginated history. Filters: date, type, status, account_id, channel. |
| GET | `/transactions/:id` | Full transaction detail including audit metadata. |
| POST | `/transactions/deposit` | Initiate deposit via channel (mtn_momo, orange_money, visa, mastercard). |
| POST | `/transactions/withdraw` | Initiate withdrawal to linked Mobile Money or bank account. |
| POST | `/transactions/transfer` | Internal transfer: between own accounts OR to another TerahBank user. |
| GET | `/transactions/:id/status` | Poll transaction status (for async MoMo webhook callbacks). |

**ALL transaction endpoints require:**
- `idempotency_key` header — reject duplicates
- PIN or biometric confirmation token for transfers and withdrawals
- `kyc_status == 'approved'` — else 403

---

## Card Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/cards` | List all virtual cards for user. |
| POST | `/cards` | Issue new virtual VISA card linked to a Standard Account. |
| PATCH | `/cards/:id/freeze` | Freeze card instantly. |
| PATCH | `/cards/:id/unfreeze` | Unfreeze card. |
| PATCH | `/cards/:id/limits` | Update per-transaction and daily spending limits. |
| GET | `/cards/:id/transactions` | Paginated transaction history for specific card. |

---

## Insurance Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/insurance/products` | List available products from all integrated partners. |
| POST | `/insurance/policies` | Initiate policy purchase referral to partner. |
| GET | `/insurance/policies/me` | List active policies for authenticated user. |
| GET | `/insurance/policies/:id` | Details of a specific policy. |

---

## Admin Utility Endpoints [ADMIN ONLY]

| Method | Route | Role | Description |
|---|---|---|---|
| GET | `/admin/transactions` | Operations+ | System-wide transaction monitoring with full filters. |
| GET | `/admin/reports/transactions` | Operations+ | Exportable report (CSV or PDF). |
| GET | `/admin/reports/users` | Operations+ | User activity report. |
| GET | `/admin/reports/insurance` | Operations+ | Insurance commission report. |
| GET | `/admin/config` | Operations+ | Current system config (rates, limits, penalties). |
| PATCH | `/admin/config` | **Super Admin only** | Update system config parameters. |

---

## Admin RBAC Roles

| Role | Access Level |
|---|---|
| `super_admin` | Full access including config changes and account deletion |
| `operations_staff` | User management, KYC review, transaction monitoring, reports |
| `read_only_analyst` | Read-only access to transactions and reports — no mutations |

---

## Webhook Endpoints (Payment Providers → TerahBank)

| Method | Route | Description |
|---|---|---|
| POST | `/webhooks/mtn-momo` | MTN Mobile Money payment callback |
| POST | `/webhooks/orange-money` | Orange Money payment callback |
| POST | `/webhooks/visa-card` | VISA card transaction notification |

All webhook endpoints validate provider signatures before processing.
