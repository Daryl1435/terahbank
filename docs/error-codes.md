# TerahBank — Error Codes Reference

> All API errors use this standardized format across mobile, web, and admin apps.
> Every client app handles errors by `error.code` — never by HTTP status alone.
> Rule: Never expose stack traces or internal error messages to clients.

---

## Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "You don't have enough funds to complete this transaction.",
    "details": {
      "available": 50000,
      "required": 75000
    }
  },
  "timestamp": "2026-02-21T10:30:00Z"
}
```

- `code` — machine-readable, used by clients for specific handling
- `message` — human-readable, shown directly to users (French/English per locale)
- `details` — optional structured data for debugging or UI display

---

## HTTP Status to Use Per Category

| Category | HTTP Status |
|---|---|
| Validation errors | 422 |
| Authentication errors | 401 |
| Authorization / permission errors | 403 |
| Not found | 404 |
| Business rule violations | 422 |
| Conflict (duplicate, idempotency) | 409 |
| External service failure | 502 |
| Rate limit exceeded | 429 |
| Unexpected server error | 500 |

---

## Auth Error Codes

| Code | HTTP | Message (EN) | When |
|---|---|---|---|
| `INVALID_CREDENTIALS` | 401 | Your phone number or password is incorrect. | Login failed — intentionally vague |
| `ACCOUNT_LOCKED` | 403 | Too many failed attempts. Try again in 30 minutes. | After 5 failed logins |
| `TOKEN_EXPIRED` | 401 | Your session has expired. Please log in again. | JWT access token expired |
| `TOKEN_INVALID` | 401 | Invalid authentication token. | Tampered or malformed JWT |
| `REFRESH_TOKEN_INVALID` | 401 | Session invalid. Please log in again. | Refresh token not found in Redis |
| `OTP_EXPIRED` | 422 | This code has expired. Request a new one. | OTP past 5-min TTL |
| `OTP_INVALID` | 422 | Invalid code. Please try again. | Wrong OTP entered |
| `OTP_MAX_ATTEMPTS` | 429 | Too many attempts. Request a new code. | 5 failed OTP attempts |
| `OTP_MAX_RESEND` | 429 | You've requested too many codes. Wait 30 minutes. | 3 resend limit hit |
| `DEVICE_UNRECOGNIZED` | 403 | New device detected. Check your email to verify. | Unrecognized device login |
| `SESSION_EXPIRED` | 401 | Your session timed out. Please log in again. | 15-min inactivity |
| `2FA_REQUIRED` | 403 | Two-factor authentication is required. | 2FA not completed |

---

## KYC Error Codes

| Code | HTTP | Message (EN) | When |
|---|---|---|---|
| `KYC_REQUIRED` | 403 | Please complete identity verification to use this feature. | Transaction attempted before KYC |
| `KYC_PENDING` | 403 | Your account is under review. We'll notify you within 24 hours. | KYC submitted, not yet approved |
| `KYC_REJECTED` | 403 | Your verification was not approved. Check your email for details. | KYC rejected by admin |
| `KYC_DOCUMENT_INVALID` | 422 | This document type is not accepted. | Wrong doc type uploaded |
| `KYC_DOCUMENT_TOO_LARGE` | 422 | Document file size exceeds the 10MB limit. | File too large for S3 upload |

---

## Account Error Codes

| Code | HTTP | Message (EN) | When |
|---|---|---|---|
| `ACCOUNT_NOT_FOUND` | 404 | Account not found. | Invalid account ID |
| `ACCOUNT_CLOSED` | 422 | This account has been closed. | Operation on closed account |
| `ACCOUNT_LOCKED` | 422 | This account is temporarily locked. Contact support. | Locked by admin |
| `ACCOUNT_ALREADY_EXISTS` | 409 | You already have an account of this type. | Duplicate standard account |
| `MINIMUM_BALANCE_REQUIRED` | 422 | A minimum balance of 1,000 XAF must remain in your account. | Withdrawal would breach min balance |
| `MINIMUM_DEPOSIT_REQUIRED` | 422 | The minimum opening deposit for this account is {amount} XAF. | Below min deposit |
| `MINIMUM_DURATION_REQUIRED` | 422 | Project accounts require a minimum duration of 6 months. | Duration < 6 months |
| `INVALID_TARGET_AMOUNT` | 422 | Target amount must be greater than zero. | Zero or negative target |
| `PROJECT_ACCOUNT_ACTIVE` | 422 | Cannot close an account with an active savings goal. | Close with active vault |

---

## Transaction Error Codes

| Code | HTTP | Message (EN) | When |
|---|---|---|---|
| `INSUFFICIENT_BALANCE` | 422 | Insufficient funds. Available: {available} XAF. | Balance too low for operation |
| `AMOUNT_TOO_LOW` | 422 | The minimum transaction amount is {minimum} XAF. | Below minimum amount |
| `AMOUNT_TOO_HIGH` | 422 | This transaction exceeds your limit of {limit} XAF. | Above spending limit |
| `DUPLICATE_TRANSACTION` | 409 | This transaction has already been processed. | Duplicate idempotency key |
| `TRANSACTION_NOT_FOUND` | 404 | Transaction not found. | Invalid transaction ID |
| `TRANSACTION_PENDING` | 422 | A transaction is already in progress. Please wait. | Concurrent transaction on same account |
| `TRANSFER_SELF` | 422 | You cannot transfer funds to the same account. | Same source + destination |
| `RECIPIENT_NOT_FOUND` | 404 | No TerahBank user found with this phone number. | Transfer to non-existent user |
| `EARLY_WITHDRAWAL_PENALTY` | 422 | Early withdrawal applies a {rate}% penalty of {amount} XAF. | Warning before penalty applied |
| `TRANSACTION_FAILED` | 502 | Payment failed. Please try again or use a different method. | Provider returned failure |
| `PAYMENT_TIMEOUT` | 504 | The payment request timed out. No funds were deducted. | MoMo 120s timeout |
| `PROVIDER_UNAVAILABLE` | 502 | {provider} is temporarily unavailable. Please try again later. | Provider API down |
| `INVALID_CHANNEL` | 422 | This payment channel is not supported. | Invalid channel enum |
| `CARD_FROZEN` | 422 | Your card is frozen. Unfreeze it in Settings to use it. | Transaction on frozen card |
| `CARD_LIMIT_EXCEEDED` | 422 | This transaction exceeds your {type} spending limit. | Over per-txn or daily limit |
| `CARD_NOT_FOUND` | 404 | Card not found. | Invalid card ID |
| `MAX_CARDS_REACHED` | 422 | You've reached the maximum number of virtual cards allowed. | Card issuance limit hit |

---

## PIN / Biometric Error Codes

| Code | HTTP | Message (EN) | When |
|---|---|---|---|
| `PIN_REQUIRED` | 403 | PIN confirmation is required for this action. | No PIN provided for transfer |
| `PIN_INCORRECT` | 403 | Incorrect PIN. {attempts_remaining} attempts remaining. | Wrong PIN |
| `PIN_LOCKED` | 403 | Too many incorrect PIN attempts. Reset your PIN via SMS. | 5 failed PIN attempts |
| `BIOMETRIC_FAILED` | 403 | Biometric verification failed. Use your PIN instead. | Face/fingerprint mismatch |

---

## Admin Error Codes

| Code | HTTP | Message (EN) | When |
|---|---|---|---|
| `INSUFFICIENT_PERMISSIONS` | 403 | You don't have permission to perform this action. | RBAC violation |
| `USER_NOT_FOUND` | 404 | User account not found. | Invalid user ID in admin panel |
| `CONFIG_KEY_INVALID` | 422 | Unknown configuration key: {key}. | Invalid system_config key |
| `CONFIG_VALUE_INVALID` | 422 | Invalid value for {key}. Expected {type}. | Wrong value type for config |
| `REPORT_GENERATION_FAILED` | 500 | Report generation failed. Please try again. | PDF/CSV generation error |

---

## Validation Error Codes (Field-Level)

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Please correct the errors below.",
    "details": {
      "fields": {
        "phone_number": "Must be in international format (e.g. +237600000000)",
        "password": "Must be at least 10 characters with uppercase, number, and special character",
        "amount": "Must be a positive integer in XAF"
      }
    }
  }
}
```

| Field Code | When |
|---|---|
| `INVALID_PHONE_FORMAT` | Not E.164 format |
| `PHONE_ALREADY_REGISTERED` | Duplicate phone on register |
| `EMAIL_ALREADY_REGISTERED` | Duplicate email on register |
| `INVALID_PASSWORD_COMPLEXITY` | Password fails complexity check |
| `INVALID_AMOUNT` | Non-positive or non-integer amount |
| `INVALID_DATE` | Date in wrong format or in the past |
| `INVALID_ACCOUNT_TYPE` | Unknown account type enum value |

---

## Client-Side Handling Rules

**Mobile (React Native) and Web (Next.js) must:**

1. Always read `error.code` — never rely on HTTP status alone for UI logic
2. For `TOKEN_EXPIRED` → silently attempt token refresh → retry once → redirect to login
3. For `KYC_REQUIRED` / `KYC_PENDING` → show KYC status screen, not generic error
4. For `PROVIDER_UNAVAILABLE` → show retry button with provider name, not generic error
5. For `EARLY_WITHDRAWAL_PENALTY` → show penalty confirmation dialog before user confirms
6. For `DUPLICATE_TRANSACTION` → show success state (transaction already processed)
7. For `VALIDATION_ERROR` → map `details.fields` to inline form field errors

**Never show raw error codes to users.** Always display the `message` field.
**Log the full error object** (including `code` + `details`) to your monitoring system.
