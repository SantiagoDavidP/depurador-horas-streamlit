"""Repository for Producto data access."""

import uuid
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models.producto import ProductoModel


class ProductoRepository:
    """Data-access layer for Productos."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, producto_id: uuid.UUID) -> Optional[ProductoModel]:
        return await self.session.get(ProductoModel, producto_id)

    async def get_by_codigo_sap(self, codigo_sap: str) -> Optional[ProductoModel]:
        stmt = select(ProductoModel).where(ProductoModel.codigo_sap == codigo_sap)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 20,
        distribuidor: Optional[str] = None,
        molecula: Optional[str] = None,
        search: Optional[str] = None,
        activo: Optional[bool] = True,
    ) -> Sequence[ProductoModel]:
        stmt = select(ProductoModel).order_by(ProductoModel.nombre)
        if activo is not None:
            stmt = stmt.where(ProductoModel.activo == activo)
        if distribuidor:
            stmt = stmt.where(ProductoModel.distribuidor == distribuidor)
        if molecula:
            stmt = stmt.where(ProductoModel.molecula.ilike(f"%{molecula}%"))
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                ProductoModel.nombre.ilike(pattern)
                | ProductoModel.codigo_sap.ilike(pattern)
            )
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(
        self,
        distribuidor: Optional[str] = None,
        molecula: Optional[str] = None,
        search: Optional[str] = None,
        activo: Optional[bool] = True,
    ) -> int:
        stmt = select(func.count()).select_from(ProductoModel)
        if activo is not None:
            stmt = stmt.where(ProductoModel.activo == activo)
        if distribuidor:
            stmt = stmt.where(ProductoModel.distribuidor == distribuidor)
        if molecula:
            stmt = stmt.where(ProductoModel.molecula.ilike(f"%{molecula}%"))
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                ProductoModel.nombre.ilike(pattern)
                | ProductoModel.codigo_sap.ilike(pattern)
            )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, producto: ProductoModel) -> ProductoModel:
        self.session.add(producto)
        await self.session.commit()
        await self.session.refresh(producto)
        return producto

    async def update(self, producto: ProductoModel, data: dict) -> ProductoModel:
        for key, value in data.items():
            setattr(producto, key, value)
        await self.session.commit()
        await self.session.refresh(producto)
        return producto

    async def upsert_by_codigo_sap(self, codigo_sap: str, data: dict) -> ProductoModel:
        """Create or update a product based on its SAP code."""
        existing = await self.get_by_codigo_sap(codigo_sap)
        if existing:
            return await self.update(existing, data)
        producto = ProductoModel(codigo_sap=codigo_sap, **data)
        return await self.create(producto)
