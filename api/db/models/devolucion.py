"""SQLAlchemy model for Devolucion."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class DevolucionModel(Base):
    __tablename__ = "devoluciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    codigo_devolucion: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    pedido_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pedidos.id"), nullable=False
    )
    numero_factura: Mapped[str] = mapped_column(String(20), nullable=False)
    producto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("productos.id"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    lote: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    razon: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="En Proceso", index=True
    )  # En Proceso, Aprobada, Rechazada
    valorizado: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    solicitante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    aprobador_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    fecha_aprobacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    pedido = relationship("PedidoModel", back_populates="devoluciones")
    producto = relationship("ProductoModel")
    solicitante = relationship("UserModel", back_populates="devoluciones_solicitadas", foreign_keys=[solicitante_id])
    aprobador = relationship("UserModel", foreign_keys=[aprobador_id])
