# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# TerahBank
Pan-African digital savings platform. Cameroon-first launch. Built by IBridge.
Monorepo: FastAPI backend + React Native mobile + Next.js web + Next.js admin.

## Build & test commands
- Infrastructure: `docker compose up -d` (PostgreSQL on 5432, Redis on 6379 — must be running first)
- API: `cd apps/api && venv/Scripts/activate && uvicorn main:app --reload`
- Mobile: `cd apps/mobile && expo start`
- Web: `cd apps/web && npm run dev`
- Admin: `cd apps/admin && npm run dev`
- Tests: `cd apps/api && pytest`
- Single test: `cd apps/api && pytest tests/unit/test_financial_calculations.py::TestInterestCalculation -v`
- Coverage: `cd apps/api && pytest tests/unit/ --cov=modules --cov-fail-under=80`
- Migrations: `cd apps/api && alembic upgrade head`
- New migration: `cd apps/api && alembic revision --autogenerate -m "description"`
- Lint API: `cd apps/api && ruff check . && mypy modules/`

## Known setup gotchas
- `CORS_ORIGINS` in `.env` is a comma-separated string — `settings.cors_origins_list` (not `settings.CORS_ORIGINS`) returns the parsed list.
- Alembic requires `psycopg2-binary` (sync driver) even though the app uses `asyncpg`. Both are in `requirements.txt`.
- JWT keys live in `apps/api/secrets/` (gitignored). Generate with: `openssl genrsa -out apps/api/secrets/jwt_private.pem 2048 && openssl rsa -in apps/api/secrets/jwt_private.pem -pubout -out apps/api/secrets/jwt_public.pem`
- Docker is at `C:\Program Files\Docker\Docker\resources\bin\docker.exe` on Windows — not on PATH in bash. Use `docker compose` from a regular terminal.

## API architecture
`main.py` mounts 8 routers under `/api/v1/{domain}`. All routers follow the same dependency chain for protected routes:
```python
@router.post("/")
async def endpoint(
    payload: Schema,
    idempotency_key: str = Header(...),      # required on all transaction routes
    user: User = Depends(get_current_user),  # JWT → DB lookup
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_kyc_approved), # 403 if kyc_status != 'approved'
):
```
Each module: `router.py` (HTTP only) → `service.py` (business logic + audit) → `repository.py` (DB queries only). Services are instantiated as `ServiceClass(db)`.

`core/config.py` — single `Settings` (pydantic-settings), cached via `@lru_cache`. Import as `from core.config import settings`.
`core/audit.py` — `write_audit_log(db, actor_id, action, ...)` must be called before returning from any mutation.
`core/dependencies.py` — `get_current_user`, `require_kyc_approved`, `require_admin_role`, `require_super_admin`.
`core/security.py` — `hash_password` / `verify_password` (bcrypt rounds=12), `generate_otp` (secrets.randbelow).

All service methods are currently stubs (`raise NotImplementedError`) — implement them one module at a time.

## Mobile architecture
`stores/authStore.ts` — Zustand for auth state (userId, kycStatus). Tokens stored in `expo-secure-store` via `saveTokens()` / `getAccessToken()` helpers — never in Zustand or AsyncStorage.
`stores/appStore.ts` — language, font size, 15-min inactivity session check (`isSessionExpired()`).
`services/*.ts` — raw fetch calls. Each service reads the token via `getAccessToken()` and builds headers.
`hooks/` — React Query wrappers over services (`useLogin`, `useAccounts`, `useTotalBalance`, etc.).
Design tokens (colours, spacing) are in `utils/tokens.ts` — never hardcode hex values in components.
Every user-facing string uses `i18n.t('key')` — add keys to both `locales/fr.json` (source of truth) and `locales/en.json`.

## Money rules — NEVER violate
- ALL money stored as BIGINT (smallest XAF unit). Never FLOAT. Never Decimal for DB storage.
- ALL financial writes wrapped in PostgreSQL transactions. No partial success ever.
- ALL transaction endpoints require an `idempotency_key` header.
- KYC gate: return 403 if `user.kyc_status != 'approved'` on every transaction route.
- Raw card data (PAN, CVV) never stored. Card token + last 4 only.
- OTPs: 6-digit, cryptographically secure, 5-min Redis TTL, deleted on first use.
- Passwords: bcrypt cost factor 12. Never SHA or MD5.
- Every financial event and admin action writes to `audit_logs` before returning.
- `audit_logs` table: no UPDATE or DELETE permissions for the API service account — ever.

## Code standards
- Branch: `feature/description` or `fix/description`
- Commits: conventional commits format
- Unit test coverage minimum: 80% (financial calc tests are mandatory, not optional)
- TypeScript strict mode on all frontend apps
- Python type hints required on all functions

## Currency & locale
- Currency: XAF (Central African CFA Franc)
- Default language: French (fr). English (en) also supported at launch.
- Cloud region: AWS af-south-1 (Cape Town) — CEMAC data residency requirement

## Key docs (reference when needed — do not load all at once)
- Architecture & modules: docs/architecture.md
- All DB tables & columns: docs/database-schema.md
- DB indexes: docs/db-indexes.md
- All API endpoints: docs/api-endpoints.md
- All 56 functional requirements: docs/requirements.md
- Phase-by-phase build plan: docs/implementation-plan.md
- Security & compliance: docs/security.md
- Error codes (all apps): docs/error-codes.md
- MTN MoMo / Orange Money: docs/mobile-money-integration.md
- BullMQ job definitions: docs/background-jobs.md
- Test patterns: docs/test-strategy.md
- Env variables: docs/env-schema.md
- Feature flags: docs/feature-flags.md
- French/English i18n: docs/i18n-strategy.md
- API versioning contract: docs/api-versioning.md
- CI/CD pipeline: docs/cicd-pipeline.md
