"""SQLAlchemy models for Pedido and DetallePedido."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class PedidoModel(Base):
    __tablename__ = "pedidos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    codigo_pedido: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    cliente_ruc: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    cliente_razon_social: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    representante: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    condicion_pago: Mapped[str] = mapped_column(String(50), nullable=False, default="Contado")
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Borrador", index=True
    )  # Borrador, Enviado, Aprobado, Rechazado
    subtotal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    igv: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    vendedor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    aprobador_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    fecha_aprobacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    vendedor = relationship("UserModel", back_populates="pedidos_creados", foreign_keys=[vendedor_id])
    aprobador = relationship("UserModel", back_populates="pedidos_aprobados", foreign_keys=[aprobador_id])
    detalles = relationship(
        "DetallePedidoModel", back_populates="pedido", cascade="all, delete-orphan"
    )
    devoluciones = relationship("DevolucionModel", back_populates="pedido")
    comentarios = relationship("ComentarioPedidoModel", back_populates="pedido", cascade="all, delete-orphan")


class DetallePedidoModel(Base):
    __tablename__ = "detalles_pedido"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pedido_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False
    )
    producto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("productos.id"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tipo: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Venta"
    )  # Venta, Bonificacion
    subtotal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    pedido = relationship("PedidoModel", back_populates="detalles")
    producto = relationship("ProductoModel")


class ComentarioPedidoModel(Base):
    __tablename__ = "comentarios_pedido"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pedido_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    pedido = relationship("PedidoModel", back_populates="comentarios")
    user = relationship("UserModel")
