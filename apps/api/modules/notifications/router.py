from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.dependencies import get_current_user
from core.schemas import TerahResponse

router = APIRouter()


@router.get("/", response_model=TerahResponse)
async def list_notifications(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    # Returns in-app notification bell items for the authenticated user
    pass
