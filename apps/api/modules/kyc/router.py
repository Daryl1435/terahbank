from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_user
from core.schemas import TerahResponse

from .service import KYCService

router = APIRouter()


# ── KYC document endpoints ────────────────────────────────────────────────────

@router.post("/me/kyc", response_model=TerahResponse)
async def upload_kyc(
    document_type: str = Form(..., description="national_id | passport | residence_permit"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    """Upload a KYC identity document. Stored in S3 with AES256 server-side encryption."""
    return await KYCService(db).upload_document(user, file, document_type)


@router.get("/me/kyc", response_model=TerahResponse)
async def get_kyc_status(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    """Return the user's KYC verification status and all submitted documents."""
    return await KYCService(db).get_kyc_status(user)


# ── Profile endpoints (Milestone 5.x) ────────────────────────────────────────

@router.get("/me", response_model=TerahResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"code": "NOT_IMPLEMENTED", "message": "Profile endpoint coming in a future milestone."},
    )


@router.patch("/me", response_model=TerahResponse)
async def update_profile(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"code": "NOT_IMPLEMENTED", "message": "Profile update coming in a future milestone."},
    )


@router.get("/me/activity-log", response_model=TerahResponse)
async def activity_log(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"code": "NOT_IMPLEMENTED", "message": "Activity log coming in a future milestone."},
    )


@router.get("/me/data-export", response_model=TerahResponse)
async def data_export(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TerahResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"code": "NOT_IMPLEMENTED", "message": "Data export coming in a future milestone."},
    )
