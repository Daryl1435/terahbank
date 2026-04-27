from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_user, require_kyc_approved
from core.schemas import TerahResponse

from .schemas import EnrollmentRequest
from .service import InsuranceService

router = APIRouter()


@router.get("/products", response_model=TerahResponse)
async def list_products(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    """FR-042: Get available insurance products from partner catalog."""
    return await InsuranceService(db).list_products()


@router.post("/policies", response_model=TerahResponse)
async def enroll_policy(
    payload: EnrollmentRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_kyc_approved),  # KYC required to purchase insurance
) -> TerahResponse:
    """FR-043: Initiate insurance policy enrollment — returns partner redirect URL."""
    return await InsuranceService(db).initiate_enrollment(payload, user.id)


@router.get("/policies/me", response_model=TerahResponse)
async def list_my_policies(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    """FR-044: List all insurance policies for the authenticated user."""
    return await InsuranceService(db).list_user_policies(user.id)


@router.get("/policies/{policy_id}", response_model=TerahResponse)
async def get_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    """Get single policy detail with expiry countdown."""
    return await InsuranceService(db).get_policy(policy_id, user.id)


@router.delete("/policies/{policy_id}", response_model=TerahResponse)
async def cancel_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    """Cancel an active insurance policy."""
    return await InsuranceService(db).cancel_policy(policy_id, user.id)
