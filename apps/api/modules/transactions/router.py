from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_user, require_kyc_approved
from core.schemas import TerahResponse

from .schemas import DepositRequest, TransferRequest, WithdrawRequest
from fastapi.responses import JSONResponse
from .service import TransactionService

router = APIRouter()


# ── FR-037: List transactions (searchable) ────────────────────────────────────

@router.get("/", response_model=TerahResponse)
async def list_transactions(
    account_id: Optional[str] = Query(None, description="Filter by account ID (debit or credit side)"),
    transaction_type: Optional[str] = Query(None, description="Filter by type: transfer | deposit | withdrawal | fee | interest | penalty"),
    txn_status: Optional[str] = Query(None, alias="status", description="Filter by status: pending | processing | success | failed | reversed"),
    date_from: Optional[datetime] = Query(None, description="Filter transactions on or after this ISO datetime"),
    date_to: Optional[datetime] = Query(None, description="Filter transactions on or before this ISO datetime"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    """FR-037: Full, searchable transfer history per user."""
    return await TransactionService(db).list_transactions(
        user_id=user.id,
        account_id=account_id,
        transaction_type=transaction_type,
        txn_status=txn_status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/{transaction_id}/status", response_model=TerahResponse)
async def get_transaction_status(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    """FR-041: Real-time transaction status poll (pending → processing → success/failed)."""
    return await TransactionService(db).get_transaction_status(transaction_id, user.id)


@router.get("/{transaction_id}", response_model=TerahResponse)
async def get_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    return await TransactionService(db).get_transaction(transaction_id, user.id)


# ── FR-038: MTN MoMo Deposit ──────────────────────────────────────────────────

@router.post("/deposit", status_code=202)
async def deposit(
    payload: DepositRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _=Depends(require_kyc_approved),
):
    """
    FR-038: Initiate a deposit via MTN MoMo.
    UC-003: Async — returns 202 Accepted immediately. Final status via webhook or GET /{id}/status.
    Idempotency-Key header required — duplicate keys return 409.
    """
    response = await TransactionService(db).deposit(payload, user, idempotency_key)
    return JSONResponse(status_code=202, content=response.model_dump(mode="json"))


# ── FR-039: Withdraw ──────────────────────────────────────────────────────────

@router.post("/withdraw", status_code=202)
async def withdraw(
    payload: WithdrawRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _=Depends(require_kyc_approved),
):
    """
    FR-039: Initiate a withdrawal via MTN MoMo or Orange Money.
    Async — debits account atomically, enqueues job, returns 202 Accepted.
    Final status tracked via GET /{id}/status polling.
    Idempotency-Key + pin_token required.
    """
    response = await TransactionService(db).withdraw(payload, user, idempotency_key)
    return JSONResponse(status_code=202, content=response.model_dump(mode="json"))


# ── FR-034/035: Internal Transfer ─────────────────────────────────────────────

@router.post("/transfer", response_model=TerahResponse)
async def transfer(
    payload: TransferRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _=Depends(require_kyc_approved),
) -> TerahResponse:
    """
    FR-034: Instant transfer between own accounts.
    FR-035: Transfer to another TerahBank user by phone number or account ID.
    FR-036: Requires pin_token from POST /auth/verify-pin (valid 60 s, single-use).
    Idempotency-Key header required — duplicate keys return 409.
    """
    return await TransactionService(db).transfer(payload, user, idempotency_key)
