# TerahBank — CI/CD Pipeline

> Every commit to main triggers the full pipeline.
> No manual deployments — everything goes through GitHub Actions.
> Rule: If it's not in the pipeline, it doesn't get checked.

---

## Branch Strategy

```
main          ← Production-ready code. Protected branch.
staging       ← Staging environment. Auto-deploys on merge.
feature/*     ← Feature branches. PR into staging.
fix/*         ← Bug fix branches. PR into staging or main (hotfix).
```

**Flow:**
`feature/xxx` → PR → staging → QA → PR → main → production

**Hotfix flow:**
`fix/critical-xxx` → PR → main (with 2 approvals) → cherry-pick to staging

---

## GitHub Actions Workflows

### 1. `ci.yml` — Runs on every PR

```yaml
name: CI

on:
  pull_request:
    branches: [main, staging]

jobs:
  backend-lint-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: terahbank_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
      redis:
        image: redis:7
        options: --health-cmd "redis-cli ping"

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with: { python-version: '3.12' }

      - name: Install dependencies
        run: |
          cd apps/api
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Lint (ruff)
        run: cd apps/api && ruff check .

      - name: Type check (mypy)
        run: cd apps/api && mypy modules/

      - name: Run unit tests
        run: |
          cd apps/api
          pytest tests/unit/ --cov=modules --cov-fail-under=80 --cov-report=xml
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/terahbank_test
          REDIS_URL: redis://localhost:6379/0
          APP_ENV: test

      - name: Run integration tests
        run: |
          cd apps/api
          pytest tests/integration/ --cov-fail-under=70
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/terahbank_test
          REDIS_URL: redis://localhost:6379/0
          APP_ENV: test

      - name: Upload coverage
        uses: codecov/codecov-action@v4

  frontend-lint-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }

      - name: Install deps (web)
        run: cd apps/web && npm ci

      - name: Lint (web)
        run: cd apps/web && npm run lint

      - name: Type check (web)
        run: cd apps/web && npm run type-check

      - name: Install deps (admin)
        run: cd apps/admin && npm ci

      - name: Lint + type check (admin)
        run: cd apps/admin && npm run lint && npm run type-check

  mobile-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd apps/mobile && npm ci
      - run: cd apps/mobile && npm run lint
      - run: cd apps/mobile && npx tsc --noEmit

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: SAST — Bandit (Python)
        run: |
          pip install bandit
          bandit -r apps/api/modules/ -ll  # Low severity and above

      - name: Dependency vulnerabilities (Python)
        run: |
          pip install safety
          cd apps/api && safety check -r requirements.txt

      - name: Dependency vulnerabilities (Node)
        run: |
          cd apps/web && npm audit --audit-level=high
          cd apps/admin && npm audit --audit-level=high
          cd apps/mobile && npm audit --audit-level=high
```

### 2. `deploy-staging.yml` — Runs on merge to staging

```yaml
name: Deploy to Staging

on:
  push:
    branches: [staging]

jobs:
  deploy-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: af-south-1

      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build + push API Docker image
        run: |
          docker build -t terahbank-api ./apps/api
          docker tag terahbank-api:latest $ECR_REGISTRY/terahbank-api:staging-${{ github.sha }}
          docker push $ECR_REGISTRY/terahbank-api:staging-${{ github.sha }}

      - name: Run DB migrations
        run: |
          aws ecs run-task \
            --cluster terahbank-staging \
            --task-definition terahbank-migration \
            --overrides '{"containerOverrides":[{"name":"api","command":["alembic","upgrade","head"]}]}'

      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster terahbank-staging \
            --service terahbank-api \
            --force-new-deployment

      - name: Deploy web to Vercel (staging)
        run: cd apps/web && npx vercel deploy --token ${{ secrets.VERCEL_TOKEN }}

      - name: Deploy admin to Vercel (staging)
        run: cd apps/admin && npx vercel deploy --token ${{ secrets.VERCEL_TOKEN }}

  e2e-tests:
    needs: deploy-api
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd apps/web && npm ci
      - name: Run Playwright E2E tests against staging
        run: cd apps/web && npx playwright test
        env:
          BASE_URL: https://staging.terahbank.com
          TEST_USER_PHONE: ${{ secrets.E2E_TEST_USER_PHONE }}
          TEST_USER_PASSWORD: ${{ secrets.E2E_TEST_USER_PASSWORD }}
```

### 3. `deploy-production.yml` — Runs on merge to main

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production    # Requires manual approval in GitHub

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.PROD_AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.PROD_AWS_SECRET_ACCESS_KEY }}
          aws-region: af-south-1

      - name: Build + push production image
        run: |
          docker build -t terahbank-api ./apps/api
          docker tag terahbank-api $ECR_REGISTRY/terahbank-api:prod-${{ github.sha }}
          docker push $ECR_REGISTRY/terahbank-api:prod-${{ github.sha }}

      - name: Run DB migrations (production)
        run: |
          # Same migration task — runs against production DB
          aws ecs run-task --cluster terahbank-prod \
            --task-definition terahbank-migration-prod \
            --overrides '{"containerOverrides":[{"name":"api","command":["alembic","upgrade","head"]}]}'
          # Wait for task to complete before deploying
          aws ecs wait tasks-stopped --cluster terahbank-prod --tasks $TASK_ARN

      - name: Deploy API to production ECS
        run: |
          aws ecs update-service \
            --cluster terahbank-prod \
            --service terahbank-api \
            --force-new-deployment
          aws ecs wait services-stable \
            --cluster terahbank-prod \
            --services terahbank-api

      - name: Deploy web + admin to Vercel (production)
        run: |
          cd apps/web && npx vercel deploy --prod --token ${{ secrets.VERCEL_TOKEN }}
          cd apps/admin && npx vercel deploy --prod --token ${{ secrets.VERCEL_TOKEN }}

      - name: Smoke test production
        run: |
          curl -f https://api.terahbank.com/api/v1/health || exit 1
```

---

## Docker Configuration

```dockerfile
# apps/api/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Non-root user for security
RUN adduser --disabled-password --gecos '' appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## Health Check Endpoint

```python
# Required for ECS health checks and smoke tests
@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "timestamp": datetime.utcnow().isoformat()
    }
```

ECS health check: `GET /api/v1/health` every 30s. 3 failures = task replaced.

---

## Secrets in GitHub Actions

| Secret | Used In |
|---|---|
| `AWS_ACCESS_KEY_ID` | Staging deployments |
| `AWS_SECRET_ACCESS_KEY` | Staging deployments |
| `PROD_AWS_ACCESS_KEY_ID` | Production deployments |
| `PROD_AWS_SECRET_ACCESS_KEY` | Production deployments |
| `VERCEL_TOKEN` | Web + admin deployment |
| `E2E_TEST_USER_PHONE` | E2E tests (staging) |
| `E2E_TEST_USER_PASSWORD` | E2E tests (staging) |

All secrets stored in GitHub repository → Settings → Secrets. Production secrets stored separately in `production` environment with required reviewers.
