"""Pydantic schemas for configuration management endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Distribuidor config
# ---------------------------------------------------------------------------

class DistribuidorConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    ruc: str
    porcentaje_comision: float
    monto_minimo_pedido: float
    activo: bool
    created_at: datetime
    updated_at: datetime


class DistribuidorConfigUpdate(BaseModel):
    porcentaje_comision: Optional[float] = Field(None, ge=0, le=100)
    monto_minimo_pedido: Optional[float] = Field(None, ge=0)
    activo: Optional[bool] = None


# ---------------------------------------------------------------------------
# Condicion de pago
# ---------------------------------------------------------------------------

class CondicionPagoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    dias_credito: int
    activo: bool
    created_at: datetime


class CondicionPagoCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    dias_credito: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Razon de devolucion
# ---------------------------------------------------------------------------

class RazonDevolucionCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
