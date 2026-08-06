"""Notifications REST endpoints (Band 10: Notifications resource group;
Band 11). Everything here is user-scoped and requires auth — a
notification/preference/device registration is only ever visible to, or
mutable by, its owner.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.modules.auth.presentation.dependencies import get_current_user_id
from app.modules.notifications.application.interfaces import NotificationSenderProtocol
from app.modules.notifications.application.service import NotificationService
from app.modules.notifications.domain.entities import (
    DeviceToken,
    Notification,
    NotificationPreference,
)
from app.modules.notifications.infrastructure.device_token_repository import (
    SqlAlchemyDeviceTokenRepository,
)
from app.modules.notifications.infrastructure.fcm_provider import FcmNotificationSender
from app.modules.notifications.infrastructure.preference_repository import (
    SqlAlchemyNotificationPreferenceRepository,
)
from app.modules.notifications.infrastructure.repository import SqlAlchemyNotificationRepository
from app.modules.notifications.presentation.schemas import (
    DeviceTokenResponse,
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationResponse,
    RegisterDeviceRequest,
    SetNotificationPreferenceRequest,
    UnregisterDeviceRequest,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def get_notification_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> NotificationService:
    sender: NotificationSenderProtocol | None = (
        FcmNotificationSender(settings)
        if settings.fcm_project_id and settings.fcm_credentials_json_path
        else None
    )
    return NotificationService(
        notifications=SqlAlchemyNotificationRepository(session),
        device_tokens=SqlAlchemyDeviceTokenRepository(session),
        preferences=SqlAlchemyNotificationPreferenceRepository(session),
        sender=sender,
    )


def _device_to_response(device: DeviceToken) -> DeviceTokenResponse:
    return DeviceTokenResponse(
        id=device.id, token=device.token, platform=device.platform, is_active=device.is_active
    )


def _notification_to_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        event=notification.event,
        channel=notification.channel,
        title=notification.title,
        body=notification.body,
        data=notification.data,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


def _preference_to_response(preference: NotificationPreference) -> NotificationPreferenceResponse:
    return NotificationPreferenceResponse(
        event=preference.event, channel=preference.channel, enabled=preference.enabled
    )


@router.post(
    "/devices", response_model=DeviceTokenResponse, status_code=status.HTTP_201_CREATED
)
async def register_device(
    body: RegisterDeviceRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> DeviceTokenResponse:
    device = await service.register_device(user_id, token=body.token, platform=body.platform)
    return _device_to_response(device)


@router.delete("/devices", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def unregister_device(
    body: UnregisterDeviceRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> None:
    await service.unregister_device(user_id, token=body.token)


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    notifications, total = await service.list_notifications(
        user_id, page=page, page_size=page_size
    )
    return NotificationListResponse(
        items=[_notification_to_response(n) for n in notifications],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> None:
    await service.mark_read(user_id, notification_id)


@router.get("/preferences", response_model=list[NotificationPreferenceResponse])
async def get_preferences(
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> list[NotificationPreferenceResponse]:
    preferences = await service.get_preferences(user_id)
    return [_preference_to_response(p) for p in preferences]


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def set_preference(
    body: SetNotificationPreferenceRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationPreferenceResponse:
    preference = await service.set_preference(
        user_id, event=body.event, channel=body.channel, enabled=body.enabled
    )
    return _preference_to_response(preference)
