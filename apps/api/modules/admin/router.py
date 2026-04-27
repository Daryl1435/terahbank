from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import require_admin_role, require_super_admin
from core.schemas import TerahResponse

from .schemas import AdminLoginRequest, KYCDecisionRequest, UpdateConfigRequest, UpdateUserStatusRequest
from .service import AdminService

router = APIRouter()


# ── Admin auth ────────────────────────────────────────────────────────────────

@router.post("/auth/login", response_model=TerahResponse)
async def admin_login(
    payload: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TerahResponse:
    """FR-056: Admin login — no Bearer token required."""
    return await AdminService(db).admin_login(payload.email, payload.password)


# ── User management (FR-051) ──────────────────────────────────────────────────

@router.get("/users", response_model=TerahResponse)
async def list_users(
    search: str | None = Query(None, description="Search full_name, email, phone_number"),
    kyc_status: str | None = Query(None),
    account_status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin_role),
) -> TerahResponse:
    return await AdminService(db).list_users(
        search=search,
        kyc_status=kyc_status,
        account_status=account_status,
        offset=offset,
        limit=limit,
    )


@router.get("/users/{user_id}", response_model=TerahResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin_role),
) -> TerahResponse:
    return await AdminService(db).get_user(user_id)


@router.patch("/users/{user_id}/status", response_model=TerahResponse)
async def update_user_status(
    user_id: str,
    payload: UpdateUserStatusRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin_role),
) -> TerahResponse:
    return await AdminService(db).update_user_status(user_id, payload, admin)


# ── KYC queue ─────────────────────────────────────────────────────────────────

@router.get("/kyc/queue", response_model=TerahResponse)
async def kyc_queue(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin_role),
) -> TerahResponse:
    return await AdminService(db).get_kyc_queue(offset=offset, limit=limit)


@router.post("/kyc/{user_id}/decision", response_model=TerahResponse)
async def kyc_decision(
    user_id: str,
    payload: KYCDecisionRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin_role),
) -> TerahResponse:
    return await AdminService(db).make_kyc_decision(user_id, payload, admin)


# ── Transactions (FR-053) ─────────────────────────────────────────────────────

@router.get("/transactions", response_model=TerahResponse)
async def list_transactions(
    user_id: str | None = Query(None),
    transaction_type: str | None = Query(None),
    channel: str | None = Query(None),
    txn_status: str | None = Query(None, alias="status"),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin_role),
) -> TerahResponse:
    return await AdminService(db).list_transactions(
        user_id=user_id,
        transaction_type=transaction_type,
        channel=channel,
        txn_status=txn_status,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )


# ── System config (FR-054) ────────────────────────────────────────────────────

@router.get("/config", response_model=TerahResponse)
async def get_config(
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin_role),
) -> TerahResponse:
    return await AdminService(db).get_config()


@router.patch("/config", response_model=TerahResponse)
async def update_config(
    payload: UpdateConfigRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_super_admin),
) -> TerahResponse:
    return await AdminService(db).update_config(payload, admin)


# ── Fraud alerts ──────────────────────────────────────────────────────────────

@router.get("/fraud-alerts", response_model=TerahResponse)
async def get_fraud_alerts(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin_role),
) -> TerahResponse:
    return await AdminService(db).get_fraud_alerts(offset=offset, limit=limit)


# ── Reports (FR-055) ──────────────────────────────────────────────────────────

@router.get("/reports/transactions")
async def report_transactions(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin_role),
):
    """Download transaction report as CSV."""
    return await AdminService(db).export_transactions_csv(date_from=date_from, date_to=date_to)


@router.get("/reports/users")
async def report_users(
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin_role),
):
    """Download user activity report as CSV."""
    return await AdminService(db).export_users_csv()


@router.get("/reports/insurance-commissions")
async def report_insurance_commissions(
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin_role),
):
    """FR-055: Download insurance commission report as CSV."""
    return await AdminService(db).export_commissions_csv()
