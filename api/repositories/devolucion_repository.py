"""Repository for Devolucion data access."""

import uuid
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.db.models.devolucion import DevolucionModel


class DevolucionRepository:
    """Data-access layer for Devoluciones."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, dev_id: uuid.UUID) -> Optional[DevolucionModel]:
        stmt = (
            select(DevolucionModel)
            .options(selectinload(DevolucionModel.producto))
            .where(DevolucionModel.id == dev_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_codigo(self, codigo: str) -> Optional[DevolucionModel]:
        stmt = select(DevolucionModel).where(DevolucionModel.codigo_devolucion == codigo)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 20,
        estado: Optional[str] = None,
        pedido_id: Optional[uuid.UUID] = None,
        producto_id: Optional[uuid.UUID] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> Sequence[DevolucionModel]:
        stmt = select(DevolucionModel).order_by(DevolucionModel.created_at.desc())
        stmt = self._apply_filters(stmt, estado, pedido_id, producto_id, fecha_desde, fecha_hasta, search)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(
        self,
        estado: Optional[str] = None,
        pedido_id: Optional[uuid.UUID] = None,
        producto_id: Optional[uuid.UUID] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(DevolucionModel)
        stmt = self._apply_filters(stmt, estado, pedido_id, producto_id, fecha_desde, fecha_hasta, search)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    def _apply_filters(self, stmt, estado, pedido_id, producto_id, fecha_desde, fecha_hasta, search):
        if estado:
            stmt = stmt.where(DevolucionModel.estado == estado)
        if pedido_id:
            stmt = stmt.where(DevolucionModel.pedido_id == pedido_id)
        if producto_id:
            stmt = stmt.where(DevolucionModel.producto_id == producto_id)
        if fecha_desde:
            stmt = stmt.where(DevolucionModel.created_at >= fecha_desde)
        if fecha_hasta:
            stmt = stmt.where(DevolucionModel.created_at <= fecha_hasta)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                DevolucionModel.codigo_devolucion.ilike(pattern)
                | DevolucionModel.numero_factura.ilike(pattern)
            )
        return stmt

    async def create(self, devolucion: DevolucionModel) -> DevolucionModel:
        self.session.add(devolucion)
        await self.session.commit()
        await self.session.refresh(devolucion)
        return devolucion

    async def update(self, devolucion: DevolucionModel, data: dict) -> DevolucionModel:
        for key, value in data.items():
            setattr(devolucion, key, value)
        await self.session.commit()
        await self.session.refresh(devolucion)
        return devolucion

    async def next_codigo(self, year: int) -> str:
        """Generate DEV-YYYY-NNNN."""
        pattern = f"DEV-{year}-%"
        stmt = (
            select(func.count())
            .select_from(DevolucionModel)
            .where(DevolucionModel.codigo_devolucion.like(pattern))
        )
        result = await self.session.execute(stmt)
        count = result.scalar_one()
        return f"DEV-{year}-{count + 1:04d}"

    async def get_already_returned_qty(
        self, pedido_id: uuid.UUID, producto_id: uuid.UUID
    ) -> int:
        """Sum of quantities already returned for a product in a given order."""
        stmt = (
            select(func.coalesce(func.sum(DevolucionModel.cantidad), 0))
            .where(
                and_(
                    DevolucionModel.pedido_id == pedido_id,
                    DevolucionModel.producto_id == producto_id,
                    DevolucionModel.estado.in_(["En Proceso", "Aprobada"]),
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_approved_for_period(
        self,
        mes: int,
        anio: int,
        distribuidor: Optional[str] = None,
    ) -> Sequence[DevolucionModel]:
        """Get approved returns in a given month/year, optionally filtered by distribuidor."""
        stmt = (
            select(DevolucionModel)
            .options(selectinload(DevolucionModel.producto))
            .where(
                and_(
                    DevolucionModel.estado == "Aprobada",
                    func.extract("month", DevolucionModel.fecha_aprobacion) == mes,
                    func.extract("year", DevolucionModel.fecha_aprobacion) == anio,
                )
            )
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        if distribuidor:
            return [r for r in rows if r.producto and r.producto.distribuidor == distribuidor]
        return rows

    async def count_for_vendor_month(self, vendedor_id: uuid.UUID, mes: int, anio: int) -> int:
        """Count returns made by a vendor in a given month."""
        stmt = (
            select(func.count())
            .select_from(DevolucionModel)
            .where(
                and_(
                    DevolucionModel.solicitante_id == vendedor_id,
                    func.extract("month", DevolucionModel.created_at) == mes,
                    func.extract("year", DevolucionModel.created_at) == anio,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
