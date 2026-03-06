"""Dashboard router -- 4 endpoints.

GET /api/dashboard/vendor/{vendorId}                   Vendor KPIs
GET /api/dashboard/vendor/{vendorId}/orders-by-status  Orders by status
GET /api/dashboard/vendor/{vendorId}/top-products      Top 5 products
GET /api/dashboard/vendor/{vendorId}/recent-activity   Recent activity timeline
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.dependencies import CurrentUser, SessionDep
from api.db.models.devolucion import DevolucionModel
from api.db.models.pedido import DetallePedidoModel, PedidoModel
from api.models.dashboard import (
    OrdersByStatusResponse,
    RecentActivityItem,
    TopProductResponse,
    VendorDashboardResponse,
)
from api.repositories.devolucion_repository import DevolucionRepository
from api.repositories.pedido_repository import PedidoRepository

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ------------------------------------------------------------------
# GET /api/dashboard/vendor/{vendorId}
# ------------------------------------------------------------------
@router.get("/vendor/{vendor_id}", response_model=VendorDashboardResponse)
async def vendor_dashboard(
    vendor_id: Annotated[uuid.UUID, Path()],
    db: SessionDep,
    user: CurrentUser,
) -> VendorDashboardResponse:
    """Aggregated KPIs for a vendor for the current month."""
    now = datetime.now(timezone.utc)
    mes = now.month
    anio = now.year

    pedido_repo = PedidoRepository(db)
    dev_repo = DevolucionRepository(db)

    total = await pedido_repo.count(vendedor_id=vendor_id)
    en_aprobacion = await pedido_repo.count(vendedor_id=vendor_id, estado="Enviado")
    devoluciones = await dev_repo.count_for_vendor_month(vendor_id, mes, anio)

    # Comisiones del mes (simplified: sum of approved orders * avg commission %)
    comisiones = 0.0  # In production, query ComisionModel

    return VendorDashboardResponse(
        pedidos_totales=total,
        pedidos_en_aprobacion=en_aprobacion,
        devoluciones_mes=devoluciones,
        comisiones_mes=comisiones,
    )


# ------------------------------------------------------------------
# GET /api/dashboard/vendor/{vendorId}/orders-by-status
# ------------------------------------------------------------------
@router.get(
    "/vendor/{vendor_id}/orders-by-status",
    response_model=list[OrdersByStatusResponse],
)
async def orders_by_status(
    vendor_id: Annotated[uuid.UUID, Path()],
    db: SessionDep,
    user: CurrentUser,
) -> list[OrdersByStatusResponse]:
    """Distribution of orders by status with counts and percentages."""
    repo = PedidoRepository(db)
    counts = await repo.count_by_status(vendor_id)
    total = sum(c["cantidad"] for c in counts) or 1
    return [
        OrdersByStatusResponse(
            estado=c["estado"],
            cantidad=c["cantidad"],
            porcentaje=round(c["cantidad"] / total * 100, 2),
        )
        for c in counts
    ]


# ------------------------------------------------------------------
# GET /api/dashboard/vendor/{vendorId}/top-products
# ------------------------------------------------------------------
@router.get(
    "/vendor/{vendor_id}/top-products",
    response_model=list[TopProductResponse],
)
async def top_products(
    vendor_id: Annotated[uuid.UUID, Path()],
    db: SessionDep,
    user: CurrentUser,
) -> list[TopProductResponse]:
    """Top 5 products sold by the vendor this month."""
    now = datetime.now(timezone.utc)
    from api.db.models.producto import ProductoModel

    stmt = (
        select(
            DetallePedidoModel.producto_id,
            ProductoModel.codigo_sap,
            ProductoModel.nombre,
            func.sum(DetallePedidoModel.cantidad).label("total_qty"),
        )
        .join(PedidoModel, DetallePedidoModel.pedido_id == PedidoModel.id)
        .join(ProductoModel, DetallePedidoModel.producto_id == ProductoModel.id)
        .where(
            PedidoModel.vendedor_id == vendor_id,
            DetallePedidoModel.tipo == "Venta",
            func.extract("month", PedidoModel.fecha) == now.month,
            func.extract("year", PedidoModel.fecha) == now.year,
        )
        .group_by(
            DetallePedidoModel.producto_id,
            ProductoModel.codigo_sap,
            ProductoModel.nombre,
        )
        .order_by(func.sum(DetallePedidoModel.cantidad).desc())
        .limit(5)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        TopProductResponse(
            producto_id=r[0],
            codigo_sap=r[1],
            nombre=r[2],
            cantidad_vendida=r[3],
        )
        for r in rows
    ]


# ------------------------------------------------------------------
# GET /api/dashboard/vendor/{vendorId}/recent-activity
# ------------------------------------------------------------------
@router.get(
    "/vendor/{vendor_id}/recent-activity",
    response_model=list[RecentActivityItem],
)
async def recent_activity(
    vendor_id: Annotated[uuid.UUID, Path()],
    db: SessionDep,
    user: CurrentUser,
) -> list[RecentActivityItem]:
    """Timeline of the last 10 events for a vendor."""
    # Gather recent orders
    stmt_orders = (
        select(PedidoModel)
        .where(PedidoModel.vendedor_id == vendor_id)
        .order_by(PedidoModel.updated_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt_orders)
    pedidos = result.scalars().all()

    events: list[RecentActivityItem] = []
    for p in pedidos:
        tipo = f"pedido_{p.estado.lower()}"
        events.append(
            RecentActivityItem(
                tipo=tipo,
                descripcion=f"Pedido {p.codigo_pedido} - {p.estado}",
                entidad_id=p.id,
                fecha=p.updated_at,
            )
        )

    # Gather recent returns
    stmt_devs = (
        select(DevolucionModel)
        .where(DevolucionModel.solicitante_id == vendor_id)
        .order_by(DevolucionModel.updated_at.desc())
        .limit(5)
    )
    result = await db.execute(stmt_devs)
    devs = result.scalars().all()
    for d in devs:
        events.append(
            RecentActivityItem(
                tipo=f"devolucion_{d.estado.lower().replace(' ', '_')}",
                descripcion=f"Devolucion {d.codigo_devolucion} - {d.estado}",
                entidad_id=d.id,
                fecha=d.updated_at,
            )
        )

    # Sort by date descending and take top 10
    events.sort(key=lambda e: e.fecha, reverse=True)
    return events[:10]
