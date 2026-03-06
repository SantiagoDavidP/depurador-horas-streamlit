"""SQLAlchemy model for Producto."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db.base import Base


class ProductoModel(Base):
    __tablename__ = "productos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    codigo_sap: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    molecula: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    precio_vvf: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    precio_compra: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    distribuidor: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # Dimexa, Quimica Suiza
    inafecto_devolucion: Mapped[bool] = mapped_column(Boolean, default=False)
    stock_disponible: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
