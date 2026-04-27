# TerahBank — Architecture

## Architecture Decision: Modular Monolith (Phase 1) → Microservices Migration Path

**Why Modular Monolith:** Small founding team, less operational overhead, clear module boundaries that support future extraction. Proven by Shopify and Stack Overflow.

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        CLIENTS                          │
│  [Android App]  [Customer Web App]  [Admin Back-Office] │
│  /apps/mobile     /apps/web           /apps/admin       │
└──────────────────────┬──────────────────────────────────┘
                       │  HTTPS / TLS 1.3 ONLY
┌──────────────────────▼──────────────────────────────────┐
│                    API GATEWAY                          │
│     Rate Limiting · JWT Validation · Routing            │
│              (Kong or AWS API Gateway)                  │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│           MODULAR MONOLITH — FastAPI Backend            │
│  /apps/api                                              │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │  Auth   │ │ Accounts │ │Transact. │ │  Admin    │  │
│  └─────────┘ └──────────┘ └──────────┘ └───────────┘  │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │  Cards  │ │Insurance │ │Notificat.│ │   KYC     │  │
│  └─────────┘ └──────────┘ └──────────┘ └───────────┘  │
└──────────┬──────────────────────┬───────────────────────┘
           │                      │
┌──────────▼──────┐   ┌───────────▼──────────────────────┐
│  PRIMARY DB     │   │   SUPPORTING SERVICES            │
│  PostgreSQL     │   │  Redis · S3 · BullMQ             │
│  (Read Replicas │   │  SendGrid · FCM · SMS Gateway    │
│   at Tier 2)    │   └──────────────────────────────────┘
└─────────────────┘
           │
┌──────────▼──────────────────────────────────────────────┐
│              EXTERNAL INTEGRATIONS                      │
│  MTN MoMo API · Orange Money API · VISA/MC Gateway      │
│  VISA Card-Issuing Partner · Insurance Partner APIs     │
└─────────────────────────────────────────────────────────┘
```

## Module Boundaries

| Module | Responsibility | External Dependencies |
|---|---|---|
| **Auth** | Registration, login, OTP, sessions, device tracking, activity logs | SMS Gateway, SendGrid |
| **Accounts** | Account CRUD, balance management, savings rules, progress tracking | None (internal) |
| **Transactions** | Deposits, withdrawals, transfers, transaction state machine | MTN MoMo, Orange Money, VISA/MC Gateway |
| **Cards** | Virtual card issuance, freeze/unfreeze, spending limits | VISA card-issuing partner API |
| **Admin** | User management, KYC queue, config, reporting, RBAC | None (internal) |
| **Insurance** | Policy catalog, referral flow, policy dashboard, renewal reminders | Insurance Partner APIs |
| **Notifications** | In-app, push, email, SMS for all events | FCM, SendGrid, SMS Gateway |
| **KYC** | Document upload, admin review queue, status management | AWS S3 |

## Monorepo Folder Structure

```
/terahbank/
├── CLAUDE.md                      ← Root constitution (always loaded)
├── .claude/
│   └── rules/
│       ├── backend.md             ← FastAPI-specific rules
│       ├── mobile.md              ← React Native rules
│       └── frontend.md            ← Next.js web rules
├── apps/
│   ├── api/                       ← FastAPI backend
│   │   ├── CLAUDE.md              ← Backend sub-rules
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── accounts/
│   │   │   ├── transactions/
│   │   │   ├── cards/
│   │   │   ├── admin/
│   │   │   ├── insurance/
│   │   │   ├── notifications/
│   │   │   └── kyc/
│   │   ├── core/                  ← Shared: db, config, security, dependencies
│   │   └── tests/
│   ├── mobile/                    ← React Native + Expo (Android Phase 1)
│   │   └── CLAUDE.md              ← Mobile sub-rules
│   ├── web/                       ← Next.js customer portal
│   │   └── CLAUDE.md              ← Web sub-rules
│   └── admin/                     ← Next.js admin back-office
│       └── CLAUDE.md              ← Admin sub-rules
├── docs/                          ← All reference docs (loaded on demand)
│   ├── architecture.md            ← This file
│   ├── database-schema.md
│   ├── api-endpoints.md
│   ├── requirements.md
│   ├── implementation-plan.md
│   └── security.md
├── infrastructure/                ← Terraform IaC
└── .github/
    └── workflows/                 ← GitHub Actions CI/CD
```

## Scaling Tiers

| Tier | MAU | Strategy |
|---|---|---|
| Tier 1 — Launch | 0–10K | Single-region AWS, ECS Fargate 2–4 instances, single RDS PostgreSQL (db.t3.medium), single Redis node |
| Tier 2 — Growth | 10K–100K | Add PostgreSQL read replica, scale ECS 4–8 instances, CloudFront CDN, Redis cluster mode |
| Tier 3 — Scale | 100K–1M | Extract Transactions + Auth to microservices, Aurora PostgreSQL, PgBouncer, AWS Redshift for analytics, multi-AZ |

## Key Bottlenecks & Mitigations

| Bottleneck | Mitigation |
|---|---|
| DB write contention on balance updates | PostgreSQL advisory locks or optimistic locking. Idempotency keys on all transaction endpoints. |
| MTN/Orange Money API rate limits & latency | Queue-based async pattern: transaction queued instantly → worker processes MoMo API → webhook updates status. Expose polling endpoint. |
| Notification volume at scale | BullMQ + Redis job queue. Dead-letter queues. At Tier 3: AWS SQS + SNS. |
| KYC document slow load for admins | S3 presigned URLs with short TTLs. Cache presigned URLs in Redis for 5 minutes. |
