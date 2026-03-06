"""Pydantic schemas for Comision."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ComisionCalculoRequest(BaseModel):
    """Parameters for commission calculation."""
    mes: int = Field(..., ge=1, le=12)
    anio: int = Field(..., ge=2020, le=2100)
    distribuidor: Optional[str] = Field(
        None,
        max_length=100,
        examples=["Dimexa"],
        description="If null, calculates for all distributors",
    )


class ComisionDistribuidorResult(BaseModel):
    """Result of commission calculation for one distributor."""
    distribuidor: str
    ventas_totales: float
    porcentaje: float
    comision_bruta: float
    recuperos: float
    neto_a_pagar: float


class ComisionCalculoResponse(BaseModel):
    """Response containing commission calculations."""
    commissions: list[ComisionDistribuidorResult]
    mes: int
    anio: int


class ComisionResponse(BaseModel):
    """Persisted commission record."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    distribuidor: str
    mes: int
    anio: int
    ventas_totales: float
    porcentaje: float
    comision_bruta: float
    recuperos: float
    neto_a_pagar: float
    estado: str
    calculado_por_id: uuid.UUID
    aprobado_por_id: Optional[uuid.UUID] = None
    fecha_calculo: datetime
    fecha_aprobacion: Optional[datetime] = None
    observaciones: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ComisionDetailResponse(ComisionResponse):
    """Commission with breakdown details."""
    detalle_pedidos: Optional[dict[str, Any]] = None
    detalle_devoluciones: Optional[dict[str, Any]] = None


class ComisionApproveRequest(BaseModel):
    """Payload for approving a commission."""
    observaciones: Optional[str] = None


class ComisionSummaryResponse(BaseModel):
    """Period summary across distributors."""
    mes: int
    anio: int
    ventas_totales: float
    comisiones_totales: float
    recuperos_totales: float
    neto_total: float
    distribuidores: list[ComisionDistribuidorResult]
