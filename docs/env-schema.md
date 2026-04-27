# TerahBank — Environment Variables Schema

> Every secret and config value is documented here.
> Rule: NOTHING sensitive in code. NOTHING in git. All secrets from AWS KMS or GitHub Secrets.
> Use python-dotenv for local dev. AWS Secrets Manager for staging/production.

---

## Loading Strategy by Environment

| Environment | Secret Source | Config Source |
|---|---|---|
| Local dev | `.env` file (gitignored) | `.env` file |
| CI/CD (GitHub Actions) | GitHub Actions Secrets | GitHub Actions Variables |
| Staging (AWS ECS) | AWS Secrets Manager | AWS SSM Parameter Store |
| Production (AWS ECS) | AWS Secrets Manager | AWS SSM Parameter Store |

**Rule:** `.env` is gitignored. `.env.example` (no real values) is committed and kept up to date.

---

## Backend API — `/apps/api/.env`

### Application
```env
APP_ENV=development                    # development | staging | production
APP_NAME=TerahBank API
APP_VERSION=1.0.0
DEBUG=true                             # MUST be false in production
PORT=8000
```

### Database
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/terahbank
DATABASE_URL_READ=postgresql+asyncpg://user:password@localhost:5432/terahbank  # Read replica in prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

### Redis
```env
REDIS_URL=redis://localhost:6379/0
REDIS_SESSION_DB=0                     # Sessions + OTPs
REDIS_CACHE_DB=1                       # Balance cache, config cache
REDIS_JOBS_DB=2                        # BullMQ job queue
```

### JWT — RS256 Asymmetric Keys
```env
JWT_PRIVATE_KEY_PATH=/secrets/jwt_private.pem   # Loaded from AWS KMS in prod
JWT_PUBLIC_KEY_PATH=/secrets/jwt_public.pem
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=RS256
```

### OTP
```env
OTP_EXPIRE_MINUTES=5
OTP_MAX_RESEND_ATTEMPTS=3
OTP_SESSION_LOCK_MINUTES=30
```

### AWS
```env
AWS_REGION=af-south-1
AWS_ACCESS_KEY_ID=                     # Never hardcode — use IAM role in ECS
AWS_SECRET_ACCESS_KEY=                 # Never hardcode — use IAM role in ECS
AWS_S3_KYC_BUCKET=terahbank-kyc-documents-prod
AWS_S3_AUDIT_BUCKET=terahbank-audit-logs-prod
AWS_KMS_KEY_ARN=arn:aws:kms:af-south-1:ACCOUNT:key/KEY_ID
AWS_SES_SENDER_EMAIL=noreply@terahbank.com
```

### MTN Mobile Money
```env
MTN_MOMO_BASE_URL=https://sandbox.momodeveloper.mtn.com   # prod: https://momodeveloper.mtn.com
MTN_MOMO_API_KEY=
MTN_MOMO_API_SECRET=
MTN_MOMO_SUBSCRIPTION_KEY=
MTN_MOMO_COLLECTION_USER_ID=
MTN_MOMO_ENVIRONMENT=sandbox           # sandbox | production
MTN_MOMO_WEBHOOK_SECRET=               # For validating inbound callbacks
MTN_MOMO_CALLBACK_URL=https://api.terahbank.com/api/v1/webhooks/mtn-momo
MTN_MOMO_TIMEOUT_SECONDS=120
```

### Orange Money
```env
ORANGE_MONEY_BASE_URL=
ORANGE_MONEY_CLIENT_ID=
ORANGE_MONEY_CLIENT_SECRET=
ORANGE_MONEY_MERCHANT_KEY=
ORANGE_MONEY_WEBHOOK_SECRET=
ORANGE_MONEY_CALLBACK_URL=https://api.terahbank.com/api/v1/webhooks/orange-money
ORANGE_MONEY_ENVIRONMENT=sandbox       # sandbox | production
```

### VISA / Card Issuing Partner
```env
VISA_PARTNER_BASE_URL=
VISA_PARTNER_API_KEY=
VISA_PARTNER_API_SECRET=
VISA_PARTNER_WEBHOOK_SECRET=
VISA_PARTNER_CALLBACK_URL=https://api.terahbank.com/api/v1/webhooks/visa-card
VISA_PARTNER_MAX_CARDS_PER_USER=3      # Admin-overridable via system_config table
```

### SendGrid (Email)
```env
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=noreply@terahbank.com
SENDGRID_FROM_NAME=TerahBank
```

### SMS Gateway
```env
SMS_GATEWAY_PROVIDER=twilio            # twilio | nexmo | africa_talking
SMS_GATEWAY_API_KEY=
SMS_GATEWAY_API_SECRET=
SMS_GATEWAY_SENDER_ID=TerahBank
```

### FCM (Push Notifications)
```env
FCM_SERVER_KEY=
FCM_PROJECT_ID=
```

### Insurance Partners
```env
INSURANCE_PARTNER_1_NAME=
INSURANCE_PARTNER_1_BASE_URL=
INSURANCE_PARTNER_1_API_KEY=
INSURANCE_PARTNER_1_COMMISSION_RATE=0.05
```

### Security
```env
BCRYPT_ROUNDS=12
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,https://app.terahbank.com,https://admin.terahbank.com
ALLOWED_HOSTS=api.terahbank.com,localhost
```

### BullMQ / Background Jobs
```env
BULLMQ_CONCURRENCY=5
BULLMQ_MAX_RETRY_ATTEMPTS=3
BULLMQ_RETRY_DELAY_MS=5000
```

### Feature Flags (see docs/feature-flags.md)
```env
FEATURE_ORANGE_MONEY=false
FEATURE_INSURANCE=false
FEATURE_VIRTUAL_CARD=true
FEATURE_MULTI_CARD=false
```

### Monitoring
```env
DATADOG_API_KEY=
DATADOG_SERVICE_NAME=terahbank-api
SENTRY_DSN=                            # Optional: error tracking
```

---

## Mobile App — `/apps/mobile/.env`

```env
EXPO_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1   # prod: https://api.terahbank.com/api/v1
EXPO_PUBLIC_APP_ENV=development
EXPO_PUBLIC_SENTRY_DSN=
```

**Rule:** Only `EXPO_PUBLIC_` prefixed vars are exposed to client bundle. Never put secrets in mobile env.

---

## Web App — `/apps/web/.env.local`

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_ENV=development
API_BASE_URL=http://localhost:8000/api/v1   # Server-side only (no NEXT_PUBLIC_ = not in bundle)
```

---

## Admin App — `/apps/admin/.env.local`

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_ENV=development
ADMIN_SESSION_SECRET=                   # For Next.js server-side session encryption
```

---

## `.env.example` Template (committed to git — NO real values)

```env
# Copy this to .env and fill in real values. Never commit .env.
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@localhost:5432/terahbank
REDIS_URL=redis://localhost:6379/0
JWT_PRIVATE_KEY_PATH=/path/to/jwt_private.pem
JWT_PUBLIC_KEY_PATH=/path/to/jwt_public.pem
AWS_REGION=af-south-1
AWS_S3_KYC_BUCKET=
AWS_KMS_KEY_ARN=
MTN_MOMO_API_KEY=
MTN_MOMO_API_SECRET=
MTN_MOMO_SUBSCRIPTION_KEY=
ORANGE_MONEY_CLIENT_ID=
ORANGE_MONEY_CLIENT_SECRET=
VISA_PARTNER_API_KEY=
SENDGRID_API_KEY=
SMS_GATEWAY_API_KEY=
FCM_SERVER_KEY=
BCRYPT_ROUNDS=12
CORS_ORIGINS=http://localhost:3000
```

---

## Secret Rotation Policy

| Secret | Rotation Frequency | Method |
|---|---|---|
| JWT private/public keys | Every 90 days | AWS KMS auto-rotation |
| Database password | Every 90 days | AWS Secrets Manager auto-rotation |
| MTN MoMo API keys | Per provider policy | Manual + notify team |
| Orange Money keys | Per provider policy | Manual + notify team |
| VISA partner keys | Per provider policy | Manual + notify team |
| SendGrid API key | Every 180 days | Manual |
| Webhook secrets | Every 90 days | Manual + update provider config |

**On rotation:** Update in AWS Secrets Manager → ECS tasks auto-reload on next deployment → verify webhooks still validating.
