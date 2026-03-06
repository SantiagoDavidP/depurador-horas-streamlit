"""Repository for Pedido and DetallePedido data access."""

import uuid
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.db.models.pedido import ComentarioPedidoModel, DetallePedidoModel, PedidoModel


class PedidoRepository:
    """Data-access layer for Pedidos."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, pedido_id: uuid.UUID) -> Optional[PedidoModel]:
        """Get a pedido with eager-loaded detalles."""
        stmt = (
            select(PedidoModel)
            .options(selectinload(PedidoModel.detalles).selectinload(DetallePedidoModel.producto))
            .options(selectinload(PedidoModel.comentarios))
            .where(PedidoModel.id == pedido_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_codigo(self, codigo_pedido: str) -> Optional[PedidoModel]:
        stmt = select(PedidoModel).where(PedidoModel.codigo_pedido == codigo_pedido)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 20,
        vendedor_id: Optional[uuid.UUID] = None,
        estado: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> Sequence[PedidoModel]:
        stmt = select(PedidoModel).order_by(PedidoModel.created_at.desc())
        stmt = self._apply_filters(stmt, vendedor_id, estado, fecha_desde, fecha_hasta, search)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(
        self,
        vendedor_id: Optional[uuid.UUID] = None,
        estado: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(PedidoModel)
        stmt = self._apply_filters(stmt, vendedor_id, estado, fecha_desde, fecha_hasta, search)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    def _apply_filters(self, stmt, vendedor_id, estado, fecha_desde, fecha_hasta, search):
        if vendedor_id:
            stmt = stmt.where(PedidoModel.vendedor_id == vendedor_id)
        if estado:
            stmt = stmt.where(PedidoModel.estado == estado)
        if fecha_desde:
            stmt = stmt.where(PedidoModel.fecha >= fecha_desde)
        if fecha_hasta:
            stmt = stmt.where(PedidoModel.fecha <= fecha_hasta)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                PedidoModel.codigo_pedido.ilike(pattern)
                | PedidoModel.cliente_razon_social.ilike(pattern)
                | PedidoModel.cliente_ruc.ilike(pattern)
            )
        return stmt

    async def create(self, pedido: PedidoModel) -> PedidoModel:
        self.session.add(pedido)
        await self.session.commit()
        await self.session.refresh(pedido)
        # Reload with relationships
        return await self.get(pedido.id)  # type: ignore[return-value]

    async def update(self, pedido: PedidoModel, data: dict) -> PedidoModel:
        for key, value in data.items():
            setattr(pedido, key, value)
        await self.session.commit()
        await self.session.refresh(pedido)
        return pedido

    async def replace_detalles(
        self, pedido_id: uuid.UUID, detalles: list[DetallePedidoModel]
    ) -> None:
        """Delete existing detalles and insert new ones."""
        stmt = select(DetallePedidoModel).where(DetallePedidoModel.pedido_id == pedido_id)
        result = await self.session.execute(stmt)
        for old in result.scalars().all():
            await self.session.delete(old)
        for d in detalles:
            self.session.add(d)
        await self.session.commit()

    async def next_codigo(self, year: int) -> str:
        """Generate the next sequential order code PED-YYYY-NNNN."""
        pattern = f"PED-{year}-%"
        stmt = (
            select(func.count())
            .select_from(PedidoModel)
            .where(PedidoModel.codigo_pedido.like(pattern))
        )
        result = await self.session.execute(stmt)
        count = result.scalar_one()
        return f"PED-{year}-{count + 1:04d}"

    async def get_pending_count(self) -> int:
        """Count orders with estado='Enviado'."""
        stmt = (
            select(func.count())
            .select_from(PedidoModel)
            .where(PedidoModel.estado == "Enviado")
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_approved_for_period(
        self,
        mes: int,
        anio: int,
        distribuidor: Optional[str] = None,
    ) -> Sequence[PedidoModel]:
        """Get approved orders whose approval date falls within a month/year."""
        stmt = (
            select(PedidoModel)
            .options(selectinload(PedidoModel.detalles).selectinload(DetallePedidoModel.producto))
            .where(
                and_(
                    PedidoModel.estado == "Aprobado",
                    func.extract("month", PedidoModel.fecha_aprobacion) == mes,
                    func.extract("year", PedidoModel.fecha_aprobacion) == anio,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ---- Comments ----

    async def add_comment(self, comment: ComentarioPedidoModel) -> ComentarioPedidoModel:
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def get_comments(self, pedido_id: uuid.UUID) -> Sequence[ComentarioPedidoModel]:
        stmt = (
            select(ComentarioPedidoModel)
            .where(ComentarioPedidoModel.pedido_id == pedido_id)
            .order_by(ComentarioPedidoModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ---- Dashboard helpers ----

    async def count_by_status(self, vendedor_id: uuid.UUID) -> list[dict]:
        """Count orders per status for a given vendor."""
        stmt = (
            select(PedidoModel.estado, func.count().label("cantidad"))
            .where(PedidoModel.vendedor_id == vendedor_id)
            .group_by(PedidoModel.estado)
        )
        result = await self.session.execute(stmt)
        return [{"estado": row[0], "cantidad": row[1]} for row in result.all()]
