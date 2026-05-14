from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_user
from core.schemas import TerahResponse

from .schemas import RegisterDeviceTokenRequest, UpdatePreferencesRequest
from .service import NotificationService

router = APIRouter()


@router.get("/", response_model=TerahResponse)
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await NotificationService(db).list_notifications(user)


@router.get("/unread-count", response_model=TerahResponse)
async def unread_count(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await NotificationService(db).get_unread_count(user)


@router.patch("/{notification_id}/read", response_model=TerahResponse)
async def mark_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await NotificationService(db).mark_read(notification_id, user)


@router.post("/read-all", response_model=TerahResponse)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await NotificationService(db).mark_all_read(user)


@router.get("/preferences", response_model=TerahResponse)
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await NotificationService(db).get_preferences(user)


@router.patch("/preferences", response_model=TerahResponse)
async def update_preferences(
    payload: UpdatePreferencesRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await NotificationService(db).update_preferences(payload, user)


@router.post("/device-token", response_model=TerahResponse)
async def register_device_token(
    payload: RegisterDeviceTokenRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await NotificationService(db).register_device_token(
        payload.token, payload.platform, user
    )
