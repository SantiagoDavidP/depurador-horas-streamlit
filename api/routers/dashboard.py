"""Dashboard router -- 5 endpoints.

GET /api/dashboard/me                                  Full dashboard for authenticated vendor
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
    ActividadRecienteSchema,
    DashboardMeResponse,
    OrdersByStatusResponse,
    PedidoEstadisticasSchema,
    RecentActivityItem,
    TopProductoSchema,
    TopProductResponse,
    VendorDashboardResponse,
)
from api.repositories.devolucion_repository import DevolucionRepository
from api.repositories.pedido_repository import PedidoRepository

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ------------------------------------------------------------------
# GET /api/dashboard/me  (used by frontend useDashboard hook)
# ------------------------------------------------------------------
@router.get("/me", response_model=DashboardMeResponse)
async def my_dashboard(
    db: SessionDep,
    user: CurrentUser,
) -> DashboardMeResponse:
    """Full aggregated dashboard for the authenticated vendor."""
    now = datetime.now(timezone.utc)
    mes = now.month
    anio = now.year
    mes_ant = mes - 1 if mes > 1 else 12
    anio_ant = anio if mes > 1 else anio - 1

    vendor_id = user.id
    pedido_repo = PedidoRepository(db)
    dev_repo = DevolucionRepository(db)

    # --- Estadisticas por estado ---
    counts = await pedido_repo.count_by_status(vendor_id)
    status_map = {c["estado"]: c["cantidad"] for c in counts}
    total = sum(status_map.values())
    aprobados = status_map.get("Aprobado", 0)
    pendientes = status_map.get("Enviado", 0)
    rechazados = status_map.get("Rechazado", 0)

    # Variacion vs mes anterior
    stmt_ant = (
        select(func.count())
        .select_from(PedidoModel)
        .where(
            PedidoModel.vendedor_id == vendor_id,
            func.extract("month", PedidoModel.fecha) == mes_ant,
            func.extract("year", PedidoModel.fecha) == anio_ant,
        )
    )
    result = await db.execute(stmt_ant)
    total_ant = result.scalar_one() or 0
    variacion = round(((total - total_ant) / total_ant * 100) if total_ant > 0 else 0.0, 1)

    # Total ventas (pedidos aprobados este mes)
    stmt_ventas = (
        select(func.coalesce(func.sum(PedidoModel.total), 0.0))
        .where(
            PedidoModel.vendedor_id == vendor_id,
            PedidoModel.estado == "Aprobado",
            func.extract("month", PedidoModel.fecha_aprobacion) == mes,
            func.extract("year", PedidoModel.fecha_aprobacion) == anio,
        )
    )
    result = await db.execute(stmt_ventas)
    total_ventas = float(result.scalar_one() or 0)

    safe_total = total or 1
    estadisticas = PedidoEstadisticasSchema(
        total_pedidos=total,
        pedidos_aprobados=aprobados,
        pedidos_pendientes=pendientes,
        pedidos_rechazados=rechazados,
        total_ventas=total_ventas,
        porcentaje_aprobados=round(aprobados / safe_total * 100, 1),
        porcentaje_pendientes=round(pendientes / safe_total * 100, 1),
        porcentaje_rechazados=round(rechazados / safe_total * 100, 1),
        variacion_mes_anterior=variacion,
    )

    # --- Top 5 productos del mes ---
    from api.db.models.producto import ProductoModel

    stmt_top = (
        select(
            ProductoModel.codigo_sap,
            ProductoModel.nombre,
            func.sum(DetallePedidoModel.cantidad).label("total_qty"),
        )
        .join(PedidoModel, DetallePedidoModel.pedido_id == PedidoModel.id)
        .join(ProductoModel, DetallePedidoModel.producto_id == ProductoModel.id)
        .where(
            PedidoModel.vendedor_id == vendor_id,
            DetallePedidoModel.tipo == "Venta",
            func.extract("month", PedidoModel.fecha) == mes,
            func.extract("year", PedidoModel.fecha) == anio,
        )
        .group_by(ProductoModel.codigo_sap, ProductoModel.nombre)
        .order_by(func.sum(DetallePedidoModel.cantidad).desc())
        .limit(5)
    )
    result = await db.execute(stmt_top)
    top_productos = [
        TopProductoSchema(codigo_sap=r[0], nombre=r[1], unidades_vendidas=int(r[2]))
        for r in result.all()
    ]

    # --- Actividad reciente ---
    stmt_p = (
        select(PedidoModel)
        .where(PedidoModel.vendedor_id == vendor_id)
        .order_by(PedidoModel.updated_at.desc())
        .limit(8)
    )
    result = await db.execute(stmt_p)
    actividad: list[ActividadRecienteSchema] = [
        ActividadRecienteSchema(
            id=str(p.id),
            tipo=f"pedido_{p.estado.lower()}",
            descripcion=f"Pedido {p.codigo_pedido} — {p.estado}",
            fecha=p.updated_at,
            icono=f"pedido_{p.estado.lower()}",
        )
        for p in result.scalars().all()
    ]

    stmt_d = (
        select(DevolucionModel)
        .where(DevolucionModel.solicitante_id == vendor_id)
        .order_by(DevolucionModel.updated_at.desc())
        .limit(4)
    )
    result = await db.execute(stmt_d)
    for d in result.scalars().all():
        actividad.append(
            ActividadRecienteSchema(
                id=str(d.id),
                tipo="devolucion_registrada",
                descripcion=f"Devolucion {d.codigo_devolucion} — {d.estado}",
                fecha=d.updated_at,
                icono="devolucion_registrada",
            )
        )
    actividad.sort(key=lambda e: e.fecha, reverse=True)

    # --- Devoluciones mes actual y anterior ---
    devoluciones_mes = await dev_repo.count_for_vendor_month(vendor_id, mes, anio)
    devoluciones_ant = await dev_repo.count_for_vendor_month(vendor_id, mes_ant, anio_ant)
    variacion_dev = round(
        ((devoluciones_mes - devoluciones_ant) / devoluciones_ant * 100)
        if devoluciones_ant > 0 else 0.0,
        1,
    )

    return DashboardMeResponse(
        estadisticas=estadisticas,
        top_productos=top_productos,
        actividad_reciente=actividad[:10],
        comisiones_acumuladas=0.0,
        devoluciones_mes=devoluciones_mes,
        variacion_devoluciones=variacion_dev,
    )


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

    events.sort(key=lambda e: e.fecha, reverse=True)
    return events[:10]
