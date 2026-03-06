"""Notificaciones router -- 6 endpoints.

POST   /api/notifications/email                     Send manual email
GET    /api/notifications/email/templates            List email templates
GET    /api/notifications/sent                       Sent history
GET    /api/notifications/user/{userId}              User notifications
GET    /api/notifications/unread/count               Unread count
PUT    /api/notifications/{id}/read                  Mark as read
DELETE /api/notifications/{id}                       Delete notification
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from api.core.dependencies import CurrentUser, SessionDep
from api.models.common import MessageResponse
from api.models.notification import (
    EmailTemplateResponse,
    NotificationResponse,
    SendEmailRequest,
    UnreadCountResponse,
)
from api.services.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["notificaciones"])


def _get_service(db: SessionDep) -> NotificationService:
    return NotificationService(db)


# ------------------------------------------------------------------
# POST /api/notifications/email
# ------------------------------------------------------------------
@router.post("/email", response_model=MessageResponse)
async def send_email(
    data: SendEmailRequest,
    user: CurrentUser,
    svc: NotificationService = Depends(_get_service),
) -> MessageResponse:
    """Send a manual email (for testing)."""
    success = await svc.send_email(
        to=data.to,
        subject=data.subject,
        body=data.body,
        user_id=user.id,
    )
    if success:
        return MessageResponse(message="Email enviado exitosamente")
    return MessageResponse(message="Error al enviar email")


# ------------------------------------------------------------------
# GET /api/notifications/email/templates
# ------------------------------------------------------------------
@router.get("/email/templates", response_model=list[EmailTemplateResponse])
async def list_templates(
    user: CurrentUser,
) -> list[EmailTemplateResponse]:
    """List available email templates."""
    return NotificationService.list_templates()


# ------------------------------------------------------------------
# GET /api/notifications/sent
# ------------------------------------------------------------------
@router.get("/sent", response_model=list[NotificationResponse])
async def sent_history(
    user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: NotificationService = Depends(_get_service),
) -> list[NotificationResponse]:
    """History of sent notifications."""
    return await svc.get_sent_history(skip=skip, limit=limit)


# ------------------------------------------------------------------
# GET /api/notifications/user/{userId}
# ------------------------------------------------------------------
@router.get("/user/{user_id}", response_model=list[NotificationResponse])
async def user_notifications(
    user_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: NotificationService = Depends(_get_service),
) -> list[NotificationResponse]:
    """List notifications for a user (read and unread)."""
    return await svc.get_user_notifications(user_id=user_id, skip=skip, limit=limit)


# ------------------------------------------------------------------
# GET /api/notifications/unread/count
# ------------------------------------------------------------------
@router.get("/unread/count", response_model=UnreadCountResponse)
async def unread_count(
    user: CurrentUser,
    svc: NotificationService = Depends(_get_service),
) -> UnreadCountResponse:
    """Count of unread notifications for header badge."""
    return await svc.unread_count(user.id)


# ------------------------------------------------------------------
# PUT /api/notifications/{id}/read
# ------------------------------------------------------------------
@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    svc: NotificationService = Depends(_get_service),
) -> NotificationResponse:
    """Mark a notification as read."""
    return await svc.mark_as_read(notification_id)


# ------------------------------------------------------------------
# DELETE /api/notifications/{id}
# ------------------------------------------------------------------
@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    svc: NotificationService = Depends(_get_service),
) -> None:
    """Delete a notification."""
    await svc.delete(notification_id)
