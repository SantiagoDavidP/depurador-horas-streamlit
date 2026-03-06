"""SQLAlchemy model for Comision."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class ComisionModel(Base):
    __tablename__ = "comisiones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    distribuidor: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    ventas_totales: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    porcentaje: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    comision_bruta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recuperos: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    neto_a_pagar: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Calculada"
    )  # Calculada, Aprobada, Pagada

    # JSON detail of included orders / returns for auditing
    detalle_pedidos: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    detalle_devoluciones: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    calculado_por_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    aprobado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    fecha_calculo: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fecha_aprobacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    calculado_por = relationship("UserModel", foreign_keys=[calculado_por_id])
    aprobado_por = relationship("UserModel", foreign_keys=[aprobado_por_id])
