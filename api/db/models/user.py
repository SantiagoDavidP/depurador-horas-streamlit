"""SQLAlchemy model for User."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rol: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Vendedor"
    )  # Vendedor, AdminComercial, Finanzas, GerenteGeneral
    entra_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remember_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    pedidos_creados = relationship("PedidoModel", back_populates="vendedor", foreign_keys="PedidoModel.vendedor_id")
    pedidos_aprobados = relationship("PedidoModel", back_populates="aprobador", foreign_keys="PedidoModel.aprobador_id")
    devoluciones_solicitadas = relationship("DevolucionModel", back_populates="solicitante", foreign_keys="DevolucionModel.solicitante_id")
    notificaciones = relationship("NotificationModel", back_populates="user")
