from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.dependencies import get_current_user, require_kyc_approved
from core.schemas import TerahResponse
from .schemas import IssueCardRequest, UpdateLimitsRequest
from .service import CardService

router = APIRouter()


@router.get("/", response_model=TerahResponse)
async def list_cards(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await CardService(db).list_cards(user.id)


@router.post("/", response_model=TerahResponse)
async def issue_card(payload: IssueCardRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user), _=Depends(require_kyc_approved)):
    return await CardService(db).issue_card(user, payload)


@router.patch("/{card_id}/freeze", response_model=TerahResponse)
async def freeze_card(card_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await CardService(db).freeze(card_id, user.id)


@router.patch("/{card_id}/unfreeze", response_model=TerahResponse)
async def unfreeze_card(card_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await CardService(db).unfreeze(card_id, user.id)


@router.patch("/{card_id}/limits", response_model=TerahResponse)
async def update_limits(card_id: str, payload: UpdateLimitsRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await CardService(db).update_limits(card_id, user.id, payload)


@router.get("/{card_id}/transactions", response_model=TerahResponse)
async def card_transactions(card_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await CardService(db).get_transactions(card_id, user.id)
