"""Pydantic schemas for Dashboard / analytics endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VendorDashboardResponse(BaseModel):
    """Aggregated KPIs for a vendor."""
    pedidos_totales: int
    pedidos_en_aprobacion: int
    devoluciones_mes: int
    comisiones_mes: float


class OrdersByStatusResponse(BaseModel):
    """Distribution of orders by status."""
    estado: str
    cantidad: int
    porcentaje: float


class TopProductResponse(BaseModel):
    """Top-selling product for the month."""
    producto_id: uuid.UUID
    codigo_sap: str
    nombre: str
    cantidad_vendida: int


class RecentActivityItem(BaseModel):
    """Single activity event in timeline."""
    tipo: str  # pedido_creado, pedido_aprobado, devolucion_creada, etc.
    descripcion: str
    entidad_id: Optional[uuid.UUID] = None
    fecha: datetime


# ---- Schemas for GET /api/dashboard/me ----

class PedidoEstadisticasSchema(BaseModel):
    total_pedidos: int
    pedidos_aprobados: int
    pedidos_pendientes: int
    pedidos_rechazados: int
    total_ventas: float
    porcentaje_aprobados: float
    porcentaje_pendientes: float
    porcentaje_rechazados: float
    variacion_mes_anterior: float


class TopProductoSchema(BaseModel):
    codigo_sap: str
    nombre: str
    unidades_vendidas: int


class ActividadRecienteSchema(BaseModel):
    id: str
    tipo: str
    descripcion: str
    fecha: datetime
    icono: str


class DashboardMeResponse(BaseModel):
    estadisticas: PedidoEstadisticasSchema
    top_productos: list[TopProductoSchema]
    actividad_reciente: list[ActividadRecienteSchema]
    comisiones_acumuladas: float
    devoluciones_mes: int
    variacion_devoluciones: float
