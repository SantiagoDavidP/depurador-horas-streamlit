"""SQLAlchemy models for application configuration tables."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db.base import Base


class DistribuidorConfigModel(Base):
    """Configuration per distributor: minimums, commission percentages."""
    __tablename__ = "distribuidor_config"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    ruc: Mapped[str] = mapped_column(String(11), nullable=False, default="")
    porcentaje_comision: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    monto_minimo_pedido: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CondicionPagoModel(Base):
    """Payment terms: Contado, Credito 30, Credito 60."""
    __tablename__ = "condiciones_pago"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    dias_credito: Mapped[int] = mapped_column(nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RazonDevolucionModel(Base):
    """Allowed return reasons."""
    __tablename__ = "razones_devolucion"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
