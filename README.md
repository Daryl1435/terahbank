# TerahBank

**Pan-African digital savings platform. Built by IBridge. Cameroon-first launch.**

> Mobile-first banking for individuals and small businesses across Cameroon and the CEMAC zone.
> Savings accounts · Goal vaults · Term deposits · Virtual VISA cards · MTN MoMo · Orange Money.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [First-Time Setup](#first-time-setup)
3. [Daily Development](#daily-development)
4. [Project Structure](#project-structure)
5. [Claude Code Skills](#claude-code-skills)
6. [Key Docs](#key-docs)
7. [Tech Stack](#tech-stack)
8. [Environment Files](#environment-files)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Install these before doing anything else:

| Tool | Version | Install |
|---|---|---|
| Python | 3.12+ | https://python.org |
| Node.js | 20+ | https://nodejs.org |
| Docker Desktop | latest | https://docker.com/products/docker-desktop |
| VS Code | latest | https://code.visualstudio.com |
| Claude Code | latest | VS Code extension marketplace |
| Expo CLI | latest | `npm install -g expo-cli` |
| Android Studio | latest | For mobile development only |

---

## First-Time Setup

Do this once when you first join the project.

### Step 1 — Clone the repo and open in VS Code

```bash
# Open VS Code in the project root — the folder containing CLAUDE.md
```

### Step 2 — Generate JWT keys

```bash
mkdir -p apps/api/secrets
openssl genrsa -out apps/api/secrets/jwt_private.pem 2048
openssl rsa -in apps/api/secrets/jwt_private.pem -pubout -out apps/api/secrets/jwt_public.pem
```

### Step 3 — Set up environment files

```bash
cp .env.example apps/api/.env
```

Open `apps/api/.env` and update these four values for local dev:

```env
DATABASE_URL=postgresql+asyncpg://terahbank:terahbank_dev_password@localhost:5432/terahbank_dev
REDIS_URL=redis://localhost:6379/0
JWT_PRIVATE_KEY_PATH=./secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=./secrets/jwt_public.pem
```

Leave all provider keys (MTN MoMo, SendGrid, FCM, etc.) as the mockup values. You will not need real keys until Phase 3.

### Step 4 — Start local services

```bash
docker compose up -d
# Starts PostgreSQL on port 5432 and Redis on port 6379
# Wait ~10 seconds for health checks to pass
```

### Step 5 — Install Python dependencies

> **Important:** Run each command on its own line.
> `venv/Scripts/activate` sets environment variables in the current shell session —
> chaining it with `&&` does NOT work (the activation is lost before the next command runs).

```powershell
cd apps/api
```
```powershell
python -m venv venv
```
```powershell
# Windows (PowerShell or CMD) — activates the virtual environment
venv/Scripts/activate
```
```powershell
# macOS / Linux — use this instead
# source venv/bin/activate
```
```powershell
# Install all backend dependencies into the venv
pip install -r requirements.txt
```

### Step 6 — Run database migrations

```powershell
# Make sure the venv is still active (you should see (venv) in your prompt)
# Make sure Docker services are running before this step
cd apps/api
```
```powershell
# Creates all tables defined in alembic/versions/ in your local PostgreSQL database
alembic upgrade head
```

### Step 7 — Start the API

```powershell
# Always run these three commands separately — never chain them with &&
# Step 1: go to the API folder
cd apps/api
```
```powershell
# Step 2: activate the Python virtual environment
# You will see (venv) appear at the start of your prompt when this works
venv/Scripts/activate
```
```powershell
# Step 3: start the API server with hot-reload enabled
uvicorn main:app --reload

# API is now running at:  http://localhost:8000
# Swagger docs at:        http://localhost:8000/docs  (development only)
```

### Step 8 — Open Claude Code

```bash
# In VS Code terminal, in the project root:
claude
# Then run:
/init
# Claude Code confirms CLAUDE.md is loaded and you are ready
```

---

## Daily Development

### Start your session

> Run each command on its own line — do **not** chain them with `&&`.
> `venv/Scripts/activate` must run in isolation; chaining loses the activation.

```powershell
# 1. Start PostgreSQL (port 5432) and Redis (port 6379) — must be first
#    Docker Desktop must be open before running this
docker compose up -d
```
```powershell
# 2. Move into the API folder
cd apps/api
```
```powershell
# 3. Activate the Python virtual environment
#    You will see (venv) in your prompt when successful
venv/Scripts/activate
```
```powershell
# 4. Start the API with hot-reload (saves file → server restarts automatically)
uvicorn main:app --reload
# API running at http://localhost:8000
```

Then open Claude Code and begin with:

```
"Work on Milestone X.X from @docs/implementation-plan.md.
 Check off tasks as we complete them. ultrathink before starting."
```

### Start each app

> For the API, always activate the venv first (separate command).
> The other apps (mobile, web, admin) use Node — no venv needed.

**API** — three steps, each on its own line:
```powershell
cd apps/api
venv/Scripts/activate      # activates venv — (venv) appears in prompt
uvicorn main:app --reload  # http://localhost:8000  |  docs: http://localhost:8000/docs
```

**Mobile (Android emulator):**
```powershell
cd apps/mobile
expo start --android       # opens Expo dev client on connected Android device / emulator
```

**Web portal:**
```powershell
cd apps/web
npm run dev                # http://localhost:3000
```

**Admin panel:**
```powershell
cd apps/admin
npm run dev                # http://localhost:3001
```

### Run tests

> Activate the venv first before running any pytest command.

```powershell
cd apps/api
venv/Scripts/activate
```
```powershell
# Run every test (unit + integration)
pytest tests/ -v
```
```powershell
# Unit tests only with coverage check — must stay above 80%
pytest tests/unit/ --cov=modules --cov-fail-under=80
```
```powershell
# Integration tests only (requires Docker services running)
pytest tests/integration/ -v
```

### Other common commands

> For API commands, make sure you are inside `apps/api` with the venv active.

```powershell
cd apps/api
venv/Scripts/activate
```
```powershell
alembic upgrade head      # apply all pending database migrations
```
```powershell
alembic downgrade -1      # roll back the last migration (use with care)
```
```powershell
ruff check .              # lint all Python files
```
```powershell
mypy modules/             # run the type checker on all modules
```
```powershell
# Docker service commands — run from the project ROOT (not apps/api)
docker compose down                       # stop PostgreSQL and Redis
docker compose --profile tools up -d     # also start pgAdmin on port 5050
```

### Context hygiene — important

Use `/clear` in Claude Code between different tasks. When you finish one module and start another, clear the context first. Load docs only when you need them — do not reference all 16 docs at once.

```
# Good
"Build the accounts router. Reference @docs/api-endpoints.md only."

# Bad
"Build everything using all docs."
```

---

## Project Structure

```
terahbank/
├── CLAUDE.md                        ← Claude Code context — slim, always loaded
├── CLAUDE.local.md                  ← Your personal notes (gitignored)
├── .gitignore
├── .env.example                     ← Copy to apps/api/.env and fill in values
├── README.md
├── docker-compose.yml               ← Starts PostgreSQL + Redis locally
│
├── .claude/
│   ├── settings.json                ← Hooks, permissions, model config
│   └── skills/                      ← 6 reusable Claude Code workflows
│       ├── add-api-module/SKILL.md  ← /add-api-module
│       ├── financial-calc/SKILL.md  ← /financial-calc
│       ├── momo-integration/SKILL.md← /momo-integration
│       ├── add-notification/SKILL.md← /add-notification
│       ├── run-migrations/SKILL.md  ← /run-migrations
│       └── new-db-migration/SKILL.md← /new-db-migration
│
├── docs/                            ← 16 reference docs (load on demand with @docs/x.md)
│   ├── architecture.md
│   ├── database-schema.md
│   ├── db-indexes.md
│   ├── api-endpoints.md
│   ├── api-versioning.md
│   ├── requirements.md
│   ├── implementation-plan.md       ← Work from this every day
│   ├── security.md
│   ├── error-codes.md
│   ├── mobile-money-integration.md
│   ├── background-jobs.md
│   ├── test-strategy.md
│   ├── env-schema.md
│   ├── feature-flags.md
│   ├── i18n-strategy.md
│   └── cicd-pipeline.md
│
└── apps/
    ├── api/                         ← FastAPI backend (Python 3.12)
    │   ├── CLAUDE.md                ← Auto-loads when working in apps/api/
    │   ├── .env                     ← Local secrets (gitignored)
    │   ├── .claude/skills/
    │   │   ├── new-endpoint/SKILL.md← /new-endpoint
    │   │   └── new-module/SKILL.md  ← /new-module
    │   ├── main.py
    │   ├── modules/                 ← auth/ accounts/ transactions/ cards/
    │   │                               admin/ insurance/ notifications/ kyc/
    │   ├── core/                    ← db, config, auth, audit (shared)
    │   ├── alembic/                 ← Database migrations
    │   ├── tests/                   ← unit/ and integration/
    │   ├── requirements.txt
    │   └── Dockerfile
    │
    ├── mobile/                      ← React Native + Expo (Android Phase 1)
    │   ├── CLAUDE.md                ← Auto-loads when working in apps/mobile/
    │   ├── .env                     ← Expo public variables
    │   ├── .claude/skills/
    │   │   ├── new-screen/SKILL.md  ← /new-screen
    │   │   └── new-component/SKILL.md← /new-component
    │   └── src/
    │       ├── screens/
    │       ├── components/
    │       ├── hooks/
    │       ├── services/
    │       ├── stores/
    │       ├── locales/             ← fr.json, en.json
    │       └── utils/
    │
    ├── web/                         ← Next.js customer portal
    │   ├── CLAUDE.md                ← Auto-loads when working in apps/web/
    │   ├── .env.local
    │   └── .claude/skills/
    │       └── new-page/SKILL.md    ← /new-page
    │
    └── admin/                       ← Next.js back-office
        ├── CLAUDE.md                ← Auto-loads when working in apps/admin/
        ├── .env.local
        └── .claude/skills/
            └── new-admin-table/SKILL.md ← /new-admin-table
```

---

## Claude Code Skills

Skills are saved workflows Claude Code runs on demand. Invoke by typing the skill name.

### Root skills — usable from anywhere

| Skill | What it does |
|---|---|
| `/add-api-module` | Scaffolds a complete FastAPI module: router, service, repository, models, schemas, tests. Wires into main.py and creates the Alembic migration. |
| `/financial-calc` | Canonical BIGINT/Decimal patterns for XAF interest, penalties, progress bars, and balance validation. Prevents float errors in financial code. |
| `/momo-integration` | Full MTN MoMo and Orange Money async flow — state machine, signature validation, duplicate callback guard, timeout handling. |
| `/add-notification` | Step-by-step for adding any push, email, or SMS event. Event code, translation keys, SendGrid template IDs, test stub. |
| `/run-migrations` | Runs Alembic migrations with a safety checklist. Warns before touching audit_logs. Includes rollback commands. |
| `/new-db-migration` | Migration template with enforced column types: UUID PKs, BIGINT money, TIMESTAMPTZ timestamps. Includes downgrade function. |

### App-level skills — load automatically when in that folder

| Skill | Folder | What it does |
|---|---|---|
| `/new-endpoint` | `apps/api/` | Add a single endpoint to an existing module with correct patterns |
| `/new-module` | `apps/api/` | Scaffold a full new API module (api-specific wiring) |
| `/new-screen` | `apps/mobile/` | Add a new React Native screen with nav, i18n, and design tokens |
| `/new-component` | `apps/mobile/` | Add a reusable mobile component with correct touch targets |
| `/new-page` | `apps/web/` | Add a new Next.js page with SSR and i18n |
| `/new-admin-table` | `apps/admin/` | Add a data table with RBAC, masking, and export |

---

## Key Docs

Reference these with `@docs/filename.md` in Claude Code — only load what the current task needs.

| Doc | Read it when... |
|---|---|
| `docs/implementation-plan.md` | Starting any coding session — this is your daily checklist |
| `docs/requirements.md` | Checking FR-001 to FR-056 acceptance criteria |
| `docs/architecture.md` | Understanding module boundaries and system diagram |
| `docs/database-schema.md` | Writing migrations or querying any table |
| `docs/db-indexes.md` | Adding any query with a WHERE or ORDER BY clause |
| `docs/api-endpoints.md` | Adding or verifying any API route |
| `docs/mobile-money-integration.md` | Touching any MTN MoMo or Orange Money code |
| `docs/error-codes.md` | Adding a new error response in any app |
| `docs/security.md` | Working on auth, KYC, audit logs, or encryption |
| `docs/test-strategy.md` | Writing financial calculation tests |
| `docs/env-schema.md` | Adding a new environment variable |
| `docs/feature-flags.md` | Enabling or disabling a feature |
| `docs/background-jobs.md` | Adding a BullMQ job or scheduled task |
| `docs/i18n-strategy.md` | Adding any user-facing string |
| `docs/api-versioning.md` | Changing an existing API response shape |
| `docs/cicd-pipeline.md` | Working on GitHub Actions or deployment |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI + Pydantic v2 |
| Mobile | React Native + Expo (Android Phase 1, iOS Phase 2) |
| Web + Admin | Next.js + TypeScript |
| Database | PostgreSQL — ACID, BIGINT money, UUID PKs |
| Cache + Sessions | Redis — balance cache, OTPs, sessions |
| Background Jobs | BullMQ (Redis-backed) |
| Cloud | AWS af-south-1 (Cape Town) — CEMAC data residency |
| Containers | Docker + AWS ECS Fargate |
| CI/CD | GitHub Actions |
| Infrastructure | Terraform |
| Payments | MTN Mobile Money + Orange Money + VISA/MasterCard |
| Email | SendGrid |
| Push notifications | Firebase Cloud Messaging (FCM) |

---

## Environment Files

| File | App | Purpose |
|---|---|---|
| `apps/api/.env` | Backend | All secrets — DB, Redis, JWT, providers, feature flags |
| `apps/mobile/.env` | Mobile | Expo public vars only — API URL, Sentry |
| `apps/web/.env.local` | Web | Next.js vars — public API URL + server-side API URL |
| `apps/admin/.env.local` | Admin | Next.js vars — public API URL + session secret |

All `.env` files are gitignored. See `docs/env-schema.md` for every variable documented.
See `.env.example` in the project root for a full template.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'pydantic_settings'` | The venv is not active. Run `venv/Scripts/activate` on its own line first, then `uvicorn main:app --reload`. |
| `venv` is not recognized | You are in CMD, not PowerShell. Use `venv\Scripts\activate.bat` (backslash + .bat extension). |
| Redis connection refused (port 6379) | Docker Desktop is not running or containers are stopped. Start Docker Desktop, then run `docker compose up -d` from the project root. |
| API won't start | Run `docker compose up -d` first. Then check `DATABASE_URL` in `apps/api/.env` matches the docker-compose credentials. |
| `&&` chaining breaks activation | `venv/Scripts/activate` must run alone — it sets shell environment variables that `&&` cannot forward. Always run `cd`, `activate`, and `uvicorn` as three separate commands. |
| Migration fails | Run `alembic history` to see state. Run `alembic downgrade -1` to roll back one step. Make sure Docker is running and the venv is active. |
| Tests failing | Activate the venv, then run `pytest -v --tb=short`. Confirm docker services are running with `docker compose ps`. |
| Claude Code ignoring rules | The CLAUDE.md may have gotten too long. Run `/clear` and reload the session. |
| MoMo webhook not firing locally | Install ngrok (`npm install -g ngrok`), run `ngrok http 8000`, update `MTN_MOMO_CALLBACK_URL` in `.env`. |
| Expo can't connect to API | Ensure `EXPO_PUBLIC_API_BASE_URL` in `apps/mobile/.env` points to your machine's local IP, not localhost (Android emulator cannot reach localhost). |
| Port already in use | Run `netstat -ano \| findstr :8000` (Windows) or `lsof -i :8000` (Mac/Linux) to find and kill the process. |

---

## Git Workflow

```
main        ← Production. Protected. Never commit directly.
staging     ← Staging. Auto-deploys on merge. PR target for features.
feature/*   ← Feature branches. PR into staging.
fix/*       ← Bug fix branches. PR into staging (or main for hotfixes).
```

Commit format: `feat: add project account creation endpoint`
Prefix: `feat` / `fix` / `docs` / `test` / `refactor` / `chore`

---

*Built by IBridge for TerahBank · Cameroon · Pan-African Banking · v1.0*