"""Pydantic schemas for Notification."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class NotificationResponse(BaseModel):
    """Notification as returned to clients."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    tipo: str
    titulo: str
    mensaje: str
    entidad: Optional[str] = None
    entidad_id: Optional[uuid.UUID] = None
    leido: bool
    enviado: bool
    fecha_envio: Optional[datetime] = None
    created_at: datetime


class SendEmailRequest(BaseModel):
    """Manual email send (for testing)."""
    to: EmailStr
    subject: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    template: Optional[str] = None


class EmailTemplateResponse(BaseModel):
    """Available email template."""
    id: str
    nombre: str
    asunto: str
    variables: list[str]


class UnreadCountResponse(BaseModel):
    """Unread notification count for badge."""
    count: int
