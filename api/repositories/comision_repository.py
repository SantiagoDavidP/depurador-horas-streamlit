"""Repository for Comision data access."""

import uuid
from typing import Optional, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models.comision import ComisionModel


class ComisionRepository:
    """Data-access layer for Comisiones."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, comision_id: uuid.UUID) -> Optional[ComisionModel]:
        return await self.session.get(ComisionModel, comision_id)

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 20,
        distribuidor: Optional[str] = None,
        mes: Optional[int] = None,
        anio: Optional[int] = None,
        estado: Optional[str] = None,
    ) -> Sequence[ComisionModel]:
        stmt = select(ComisionModel).order_by(ComisionModel.created_at.desc())
        stmt = self._apply_filters(stmt, distribuidor, mes, anio, estado)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(
        self,
        distribuidor: Optional[str] = None,
        mes: Optional[int] = None,
        anio: Optional[int] = None,
        estado: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(ComisionModel)
        stmt = self._apply_filters(stmt, distribuidor, mes, anio, estado)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    def _apply_filters(self, stmt, distribuidor, mes, anio, estado):
        if distribuidor:
            stmt = stmt.where(ComisionModel.distribuidor == distribuidor)
        if mes is not None:
            stmt = stmt.where(ComisionModel.mes == mes)
        if anio is not None:
            stmt = stmt.where(ComisionModel.anio == anio)
        if estado:
            stmt = stmt.where(ComisionModel.estado == estado)
        return stmt

    async def get_by_period(
        self, distribuidor: str, mes: int, anio: int
    ) -> Optional[ComisionModel]:
        """Find existing commission record for a distributor in a given period."""
        stmt = select(ComisionModel).where(
            and_(
                ComisionModel.distribuidor == distribuidor,
                ComisionModel.mes == mes,
                ComisionModel.anio == anio,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, comision: ComisionModel) -> ComisionModel:
        self.session.add(comision)
        await self.session.commit()
        await self.session.refresh(comision)
        return comision

    async def update(self, comision: ComisionModel, data: dict) -> ComisionModel:
        for key, value in data.items():
            setattr(comision, key, value)
        await self.session.commit()
        await self.session.refresh(comision)
        return comision
