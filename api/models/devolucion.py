"""Pydantic schemas for Devolucion."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DevolucionProductoItem(BaseModel):
    """Single product line within a return request."""
    producto_id: uuid.UUID
    cantidad: int = Field(..., gt=0)
    lote: str = Field(default="", max_length=100)
    razon: str = Field(
        ...,
        max_length=255,
        examples=["Producto daniado"],
    )


class DevolucionCreate(BaseModel):
    """Schema for registering a new return (single-product per record)."""
    pedido_id: uuid.UUID
    numero_factura: str = Field(
        ...,
        pattern=r"^F\d{3}-\d{8}$",
        examples=["F001-00012345"],
    )
    producto_id: uuid.UUID
    cantidad: int = Field(..., gt=0)
    lote: str = Field(default="", max_length=100)
    razon: str = Field(..., max_length=255)
    observaciones: Optional[str] = None


class DevolucionBatchCreate(BaseModel):
    """Create multiple return lines for one invoice at once."""
    pedido_id: uuid.UUID
    numero_factura: str = Field(
        ...,
        pattern=r"^F\d{3}-\d{8}$",
        examples=["F001-00012345"],
    )
    productos: list[DevolucionProductoItem] = Field(..., min_length=1)
    observaciones: Optional[str] = None


class DevolucionUpdate(BaseModel):
    """Partial update for an in-process return."""
    cantidad: Optional[int] = Field(None, gt=0)
    lote: Optional[str] = Field(None, max_length=100)
    razon: Optional[str] = Field(None, max_length=255)
    observaciones: Optional[str] = None


class DevolucionResponse(BaseModel):
    """Return response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo_devolucion: str
    pedido_id: uuid.UUID
    numero_factura: str
    producto_id: uuid.UUID
    cantidad: int
    lote: str
    razon: str
    estado: str
    valorizado: float
    observaciones: Optional[str] = None
    solicitante_id: uuid.UUID
    aprobador_id: Optional[uuid.UUID] = None
    fecha_aprobacion: Optional[datetime] = None
    motivo_rechazo: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    producto_nombre: Optional[str] = None
    producto_codigo_sap: Optional[str] = None


class DevolucionApproveRequest(BaseModel):
    """Payload for approving a return."""
    comentarios: Optional[str] = None


class DevolucionRejectRequest(BaseModel):
    """Payload for rejecting a return."""
    motivo_rechazo: str = Field(..., min_length=1)


class DevolucionValorizadoResponse(BaseModel):
    """Calculated valorizado before saving."""
    producto_id: uuid.UUID
    producto_nombre: str
    cantidad: int
    precio_unitario: float
    valorizado: float


class RazonDevolucionResponse(BaseModel):
    """Available return reason."""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    activo: bool


class ReturnableProductResponse(BaseModel):
    """Product from an order that can still be returned."""
    producto_id: uuid.UUID
    producto_nombre: str
    codigo_sap: str
    cantidad_original: int
    cantidad_ya_devuelta: int
    cantidad_disponible: int
    precio_unitario: float
