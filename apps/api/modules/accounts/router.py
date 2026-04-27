from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_user, require_kyc_approved
from core.schemas import TerahResponse

from .schemas import (
    CreateProjectAccountRequest,
    CreateStandardAccountRequest,
    CreateTermDepositRequest,
    UpdateAutoSaveRuleRequest,
)
from .service import AccountService

router = APIRouter()


# ── FR-025: Term Deposit interest calculator ──────────────────────────────────
# Defined before /{account_id} to prevent path-segment collision — though FastAPI
# resolves by segment count (/term-deposit/calculator = 2 segs vs /{id} = 1 seg).

@router.get("/term-deposit/calculator", response_model=TerahResponse)
async def term_deposit_calculator(
    amount: int = Query(..., gt=0, description="Principal amount in smallest XAF unit"),
    duration_months: int = Query(..., ge=1, description="Term duration in months"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """FR-025: Pre-confirmation interest projection for a term deposit."""
    return await AccountService(db).get_term_deposit_calculator(amount, duration_months)


@router.get("/", response_model=TerahResponse)
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """FR-013: Return all active accounts with real-time balances (Redis cache)."""
    return await AccountService(db).list_accounts(user.id)


@router.get("/{account_id}", response_model=TerahResponse)
async def get_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """FR-013: Return a single account with cached balance."""
    return await AccountService(db).get_account(account_id, user.id)


@router.post("/standard", response_model=TerahResponse)
async def open_standard(
    payload: CreateStandardAccountRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _=Depends(require_kyc_approved),
):
    """FR-010/011: Open Standard Savings Account. Requires KYC approved."""
    return await AccountService(db).open_standard(user, payload)


@router.post("/project", response_model=TerahResponse)
async def open_project(
    payload: CreateProjectAccountRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _=Depends(require_kyc_approved),
):
    """FR-016/022: Create Project Account (Vault). Multiple allowed per user."""
    return await AccountService(db).open_project(user, payload)


@router.patch("/project/{account_id}", response_model=TerahResponse)
async def update_project_auto_save(
    account_id: str,
    payload: UpdateAutoSaveRuleRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _=Depends(require_kyc_approved),
):
    """FR-021 [Should Have]: Configure recurring auto-save rule for a project account."""
    return await AccountService(db).update_project_auto_save(account_id, user.id, payload)


@router.get("/project/{account_id}/withdrawal-preview", response_model=TerahResponse)
async def preview_project_withdrawal(
    account_id: str,
    amount: int = Query(..., gt=0, description="Withdrawal amount in smallest XAF unit"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _=Depends(require_kyc_approved),
):
    """FR-018/019: Preview early-withdrawal penalty before confirming."""
    return await AccountService(db).preview_project_withdrawal(account_id, user.id, amount)


@router.post("/term-deposit", response_model=TerahResponse)
async def open_term_deposit(
    payload: CreateTermDepositRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _=Depends(require_kyc_approved),
):
    """FR-023: Open Term Deposit — Milestone 2.3."""
    return await AccountService(db).open_term_deposit(user, payload)


@router.delete("/{account_id}", response_model=TerahResponse)
async def close_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Close account (requires zero balance) — Milestone 2.3."""
    return await AccountService(db).close_account(account_id, user.id)
