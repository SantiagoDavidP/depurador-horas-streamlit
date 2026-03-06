"""Pydantic schemas for Producto."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductoBase(BaseModel):
    """Shared product fields."""
    codigo_sap: str = Field(..., min_length=1, max_length=50)
    nombre: str = Field(..., min_length=1, max_length=255)
    molecula: str = Field(default="", max_length=255)
    precio_vvf: float = Field(..., ge=0, examples=[29.99])
    precio_compra: float = Field(default=0.0, ge=0)
    distribuidor: str = Field(
        ...,
        max_length=100,
        examples=["Dimexa"],
    )
    inafecto_devolucion: bool = Field(default=False)
    stock_disponible: int = Field(default=0, ge=0)


class ProductoCreate(ProductoBase):
    """Schema for creating a product."""
    pass


class ProductoUpdate(BaseModel):
    """Partial update for a product."""
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    molecula: Optional[str] = Field(None, max_length=255)
    precio_vvf: Optional[float] = Field(None, ge=0)
    precio_compra: Optional[float] = Field(None, ge=0)
    distribuidor: Optional[str] = Field(None, max_length=100)
    inafecto_devolucion: Optional[bool] = None
    stock_disponible: Optional[int] = Field(None, ge=0)
    activo: Optional[bool] = None


class ProductoResponse(ProductoBase):
    """Product response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activo: bool
    created_at: datetime
    updated_at: datetime
