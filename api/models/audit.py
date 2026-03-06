"""Pydantic schemas for AuditLog."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Audit log entry."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    entidad: str
    entidad_id: uuid.UUID
    accion: str
    valores_anteriores: Optional[dict[str, Any]] = None
    valores_nuevos: Optional[dict[str, Any]] = None
    ip_address: str
    user_agent: str
    created_at: datetime
