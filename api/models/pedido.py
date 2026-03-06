"""Pydantic schemas for Pedido and DetallePedido."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# DetallePedido
# ---------------------------------------------------------------------------

class DetallePedidoBase(BaseModel):
    """Single line-item within an order."""
    producto_id: uuid.UUID
    cantidad: int = Field(..., gt=0)
    tipo: str = Field(
        default="Venta",
        pattern=r"^(Venta|Bonificacion)$",
        examples=["Venta"],
    )


class DetallePedidoCreate(DetallePedidoBase):
    """Schema used when creating a new order detail."""
    pass


class DetallePedidoResponse(DetallePedidoBase):
    """Response schema for a line-item."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    precio_unitario: float
    subtotal: float
    created_at: datetime
    producto_nombre: Optional[str] = None
    producto_codigo_sap: Optional[str] = None


# ---------------------------------------------------------------------------
# Pedido
# ---------------------------------------------------------------------------

class PedidoBase(BaseModel):
    """Shared order fields."""
    cliente_ruc: str = Field(
        ...,
        min_length=11,
        max_length=11,
        pattern=r"^\d{11}$",
        examples=["20100130204"],
    )
    cliente_razon_social: str = Field(default="", max_length=255)
    representante: str = Field(default="", max_length=255)
    condicion_pago: str = Field(
        default="Contado",
        pattern=r"^(Contado|Credito 30 dias|Credito 60 dias)$",
    )
    observaciones: Optional[str] = None


class PedidoCreate(PedidoBase):
    """Schema for creating an order (Borrador or Enviado)."""
    detalles: list[DetallePedidoCreate] = Field(..., min_length=1)
    estado: str = Field(
        default="Borrador",
        pattern=r"^(Borrador|Enviado)$",
    )


class PedidoUpdate(BaseModel):
    """Partial update for a draft/sent order."""
    cliente_ruc: Optional[str] = Field(
        None,
        min_length=11,
        max_length=11,
        pattern=r"^\d{11}$",
    )
    cliente_razon_social: Optional[str] = Field(None, max_length=255)
    representante: Optional[str] = Field(None, max_length=255)
    condicion_pago: Optional[str] = Field(
        None,
        pattern=r"^(Contado|Credito 30 dias|Credito 60 dias)$",
    )
    observaciones: Optional[str] = None
    detalles: Optional[list[DetallePedidoCreate]] = None


class PedidoResponse(PedidoBase):
    """Full order response including computed totals."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo_pedido: str
    fecha: datetime
    estado: str
    subtotal: float
    igv: float
    total: float
    vendedor_id: uuid.UUID
    aprobador_id: Optional[uuid.UUID] = None
    fecha_aprobacion: Optional[datetime] = None
    motivo_rechazo: Optional[str] = None
    detalles: list[DetallePedidoResponse] = []
    created_at: datetime
    updated_at: datetime


class PedidoListResponse(BaseModel):
    """Lightweight list item (no nested detalles)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo_pedido: str
    fecha: datetime
    cliente_ruc: str
    cliente_razon_social: str
    representante: str
    condicion_pago: str
    estado: str
    subtotal: float
    igv: float
    total: float
    vendedor_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

class PedidoApproveRequest(BaseModel):
    """Payload for order approval."""
    comentarios: Optional[str] = None


class PedidoRejectRequest(BaseModel):
    """Payload for order rejection."""
    motivo_rechazo: str = Field(..., min_length=1)


class PedidoApproveResponse(BaseModel):
    """Response after approval."""
    success: bool = True
    order_id: uuid.UUID
    new_status: str
    notification_sent: bool = True


class PedidoRejectResponse(BaseModel):
    """Response after rejection."""
    success: bool = True
    order_id: uuid.UUID
    new_status: str


# ---------------------------------------------------------------------------
# Comentarios
# ---------------------------------------------------------------------------

class ComentarioCreate(BaseModel):
    """Payload for adding a comment."""
    contenido: str = Field(..., min_length=1, max_length=2000)


class ComentarioResponse(BaseModel):
    """Comment response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pedido_id: uuid.UUID
    user_id: uuid.UUID
    contenido: str
    created_at: datetime
    user_nombre: Optional[str] = None
