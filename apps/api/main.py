import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.database import engine
from core.redis import init_redis, close_redis
from core.schemas import TerahErrorDetail, TerahErrorResponse

from modules.auth.router import router as auth_router
from modules.accounts.router import router as accounts_router
from modules.transactions.router import router as transactions_router
from modules.cards.router import router as cards_router
from modules.kyc.router import router as kyc_router
from modules.insurance.router import router as insurance_router
from modules.notifications.router import router as notifications_router
from modules.admin.router import router as admin_router
from modules.webhooks.router import router as webhooks_router

logger = logging.getLogger("terahbank")


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting TerahBank API…")
    await init_redis()
    logger.info("Redis connected.")

    # Register scheduled BullMQ jobs
    try:
        from modules.jobs.monthly_savings_summary import register_monthly_savings_job
        from modules.jobs.auto_save_executor import register_auto_save_job
        from modules.jobs.term_deposit_maturity_notifier import register_term_deposit_maturity_job
        from modules.jobs.insurance_renewal_notifier import register_insurance_renewal_job
        await register_monthly_savings_job()
        await register_auto_save_job()
        await register_term_deposit_maturity_job()
        await register_insurance_renewal_job()
        logger.info("Scheduled jobs registered.")
    except Exception as exc:  # pragma: no cover
        # Non-fatal: API still starts even if job registration fails
        logger.error("Failed to register scheduled jobs: %s", exc)

    yield
    # Shutdown
    logger.info("Shutting down TerahBank API…")
    await close_redis()
    await engine.dispose()
    logger.info("Connections closed.")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="TerahBank API",
    description=(
        "Pan-African digital savings platform — Cameroon-first. "
        "All monetary values are BIGINT (smallest XAF unit). "
        "Transaction endpoints require an `Idempotency-Key` header."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)


# ─── Middleware ────────────────────────────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attaches a unique X-Request-ID to every request and response."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds OWASP-recommended security headers to every API response.

    Headers added:
    - HSTS: force HTTPS for 1 year (production only; skipped in dev so localhost works)
    - X-Content-Type-Options: prevent MIME sniffing attacks
    - X-Frame-Options: block clickjacking via iframes
    - Referrer-Policy: don't leak the full URL to third parties
    - Permissions-Policy: disable browser features we never use
    - Content-Security-Policy: API returns JSON only — block everything else
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # HSTS — only meaningful over real HTTPS; skip in dev to avoid browser caching
        if settings.APP_ENV != "development":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Block MIME-type sniffing (e.g. serving a JS file as text/plain and executing it)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent the API responses from being embedded in iframes (clickjacking)
        response.headers["X-Frame-Options"] = "DENY"

        # Only send the origin (no path/query) in the Referer header to other sites
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Disable browser features the API never needs
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # CSP: this is a JSON API — there are no scripts, styles, or frames to allow
        response.headers["Content-Security-Policy"] = "default-src 'none'"

        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # parsed list, not raw string
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Error handlers ───────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Convert all HTTPExceptions to the standard TerahErrorResponse envelope."""
    # exc.detail may be a dict (our structured errors) or a plain string
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", str(exc.detail))
        details = exc.detail.get("details", {})
    else:
        code = f"HTTP_{exc.status_code}"
        message = str(exc.detail)
        details = {}

    return JSONResponse(
        status_code=exc.status_code,
        content=TerahErrorResponse(
            error=TerahErrorDetail(code=code, message=message, details=details)
        ).model_dump(mode="json"),
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return 422 with field-level detail in TerahErrorResponse format."""
    field_errors: dict = {}
    for error in exc.errors():
        loc = " → ".join(str(l) for l in error["loc"] if l != "body")
        field_errors[loc] = error["msg"]

    return JSONResponse(
        status_code=422,
        content=TerahErrorResponse(
            error=TerahErrorDetail(
                code="VALIDATION_ERROR",
                message="Request validation failed. Check the 'details' field.",
                details=field_errors,
            )
        ).model_dump(mode="json"),
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all — never expose internal details in production."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        "Unhandled exception on %s %s [request_id=%s]",
        request.method, request.url.path, request_id,
    )
    message = str(exc) if settings.DEBUG else "An unexpected error occurred."
    return JSONResponse(
        status_code=500,
        content=TerahErrorResponse(
            error=TerahErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message=message,
            )
        ).model_dump(mode="json"),
        headers={"X-Request-ID": request_id},
    )


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth_router,          prefix="/api/v1/auth",          tags=["Auth"])
app.include_router(accounts_router,      prefix="/api/v1/accounts",      tags=["Accounts"])
app.include_router(transactions_router,  prefix="/api/v1/transactions",   tags=["Transactions"])
app.include_router(cards_router,         prefix="/api/v1/cards",          tags=["Cards"])
app.include_router(kyc_router,           prefix="/api/v1/users",          tags=["KYC"])
app.include_router(insurance_router,     prefix="/api/v1/insurance",      tags=["Insurance"])
app.include_router(notifications_router, prefix="/api/v1/notifications",  tags=["Notifications"])
app.include_router(admin_router,         prefix="/api/v1/admin",          tags=["Admin"])
app.include_router(webhooks_router,      prefix="/api/v1/webhooks",       tags=["Webhooks"])


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/api/v1/health", tags=["Health"], include_in_schema=True)
async def health_check():
    """
    Liveness + readiness probe.
    Checks DB and Redis connectivity — ECS replaces the task if this returns non-200.
    """
    from sqlalchemy import text
    from core.database import AsyncSessionLocal
    from core.redis import get_redis_client

    db_ok = False
    redis_ok = False

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error("Health check DB failure: %s", e)

    try:
        await get_redis_client().ping()
        redis_ok = True
    except Exception as e:
        logger.error("Health check Redis failure: %s", e)

    status = "ok" if (db_ok and redis_ok) else "degraded"
    status_code = 200 if status == "ok" else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "checks": {"database": db_ok, "redis": redis_ok},
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
