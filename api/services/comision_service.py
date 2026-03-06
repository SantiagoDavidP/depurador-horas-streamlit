"""Business logic for Comisiones.

Key formulas:
- Dimexa (10%):
    comision_bruta = ventas_totales * 0.10
    recuperos = SUM(devoluciones.valorizado) * 0.10
    neto = comision_bruta - recuperos

- Quimica Suiza (13%):
    For each detalle: diferencia = precio_unitario - producto.precio_compra
    base_comision = SUM(cantidad * diferencia)
    comision_bruta = base_comision * 0.13
    recuperos = SUM(devoluciones.valorizado) * 0.13
    neto = comision_bruta - recuperos
"""

from __future__ import annotations


import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    ValidationException,
)
from api.db.models.comision import ComisionModel
from api.models.comision import (
    ComisionApproveRequest,
    ComisionCalculoRequest,
    ComisionCalculoResponse,
    ComisionDetailResponse,
    ComisionDistribuidorResult,
    ComisionResponse,
    ComisionSummaryResponse,
)
from api.models.common import PaginatedResponse
from api.repositories.comision_repository import ComisionRepository
from api.repositories.devolucion_repository import DevolucionRepository
from api.repositories.pedido_repository import PedidoRepository

logger = logging.getLogger("bonapharm.comision_service")

DISTRIBUTOR_PCTS: dict[str, float] = {
    "Dimexa": settings.COMISION_DIMEXA_PCT,
    "Quimica Suiza": settings.COMISION_QUIMICA_PCT,
}


class ComisionService:
    """Calculates, persists, and approves commissions."""

    def __init__(
        self,
        comision_repo: ComisionRepository,
        pedido_repo: PedidoRepository,
        devolucion_repo: DevolucionRepository,
        session: AsyncSession,
    ) -> None:
        self.comision_repo = comision_repo
        self.pedido_repo = pedido_repo
        self.devolucion_repo = devolucion_repo
        self.session = session

    # ------------------------------------------------------------------
    # List / Get
    # ------------------------------------------------------------------

    async def list(
        self,
        skip: int = 0,
        limit: int = 20,
        distribuidor: Optional[str] = None,
        mes: Optional[int] = None,
        anio: Optional[int] = None,
        estado: Optional[str] = None,
    ) -> PaginatedResponse[ComisionResponse]:
        """List commission records with filters and pagination."""
        items = await self.comision_repo.get_multi(
            skip=skip, limit=limit,
            distribuidor=distribuidor, mes=mes, anio=anio, estado=estado,
        )
        total = await self.comision_repo.count(
            distribuidor=distribuidor, mes=mes, anio=anio, estado=estado,
        )
        return PaginatedResponse(
            items=[ComisionResponse.model_validate(i) for i in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_detail(self, comision_id: uuid.UUID) -> ComisionDetailResponse:
        """Get commission with full breakdown details."""
        com = await self.comision_repo.get(comision_id)
        if not com:
            raise NotFoundException("Comision", str(comision_id))
        return ComisionDetailResponse.model_validate(com)

    # ------------------------------------------------------------------
    # Calculate
    # ------------------------------------------------------------------

    async def calculate(
        self,
        data: ComisionCalculoRequest,
        calculado_por_id: uuid.UUID,
    ) -> ComisionCalculoResponse:
        """Execute commission calculation for a period.

        If distribuidor is None, calculates for all distributors.
        """
        distributors = (
            [data.distribuidor] if data.distribuidor else list(DISTRIBUTOR_PCTS.keys())
        )

        results: list[ComisionDistribuidorResult] = []
        for dist in distributors:
            result = await self._calculate_for_distributor(
                dist, data.mes, data.anio, calculado_por_id
            )
            results.append(result)

        return ComisionCalculoResponse(
            commissions=results,
            mes=data.mes,
            anio=data.anio,
        )

    async def _calculate_for_distributor(
        self,
        distribuidor: str,
        mes: int,
        anio: int,
        calculado_por_id: uuid.UUID,
    ) -> ComisionDistribuidorResult:
        """Core calculation logic per distributor."""
        pct = DISTRIBUTOR_PCTS.get(distribuidor, 0.10)

        # Check for existing commission
        existing = await self.comision_repo.get_by_period(distribuidor, mes, anio)
        if existing and existing.estado in ("Aprobada", "Pagada"):
            raise ConflictException(
                f"Ya existe una comision {existing.estado} para {distribuidor} {mes}/{anio}"
            )

        # Fetch approved orders for the period
        pedidos = await self.pedido_repo.get_approved_for_period(mes, anio)

        # Filter detalles by distribuidor
        if distribuidor == "Quimica Suiza":
            # Formula: 13% of price difference (VVF - purchase price)
            base_comision = 0.0
            pedido_ids: list[str] = []
            for p in pedidos:
                for d in p.detalles:
                    if d.producto and d.producto.distribuidor == distribuidor and d.tipo == "Venta":
                        diferencia = d.precio_unitario - (d.producto.precio_compra or 0.0)
                        base_comision += d.cantidad * diferencia
                        if str(p.id) not in pedido_ids:
                            pedido_ids.append(str(p.id))
            ventas_totales = base_comision
            comision_bruta = round(base_comision * pct, 2)
        else:
            # Dimexa: 10% of total sales
            ventas_totales = 0.0
            pedido_ids = []
            for p in pedidos:
                has_dist = any(
                    d.producto and d.producto.distribuidor == distribuidor
                    for d in p.detalles
                )
                if has_dist:
                    # Sum only detalles belonging to this distributor
                    dist_total = sum(
                        d.subtotal for d in p.detalles
                        if d.producto and d.producto.distribuidor == distribuidor and d.tipo == "Venta"
                    )
                    ventas_totales += dist_total
                    pedido_ids.append(str(p.id))
            comision_bruta = round(ventas_totales * pct, 2)

        # Fetch approved returns for the period
        devoluciones = await self.devolucion_repo.get_approved_for_period(
            mes, anio, distribuidor=distribuidor
        )
        dev_valorizado = sum(d.valorizado for d in devoluciones)
        dev_ids = [str(d.id) for d in devoluciones]
        recuperos = round(dev_valorizado * pct, 2)
        neto = round(comision_bruta - recuperos, 2)

        # Persist or update
        now = datetime.now(timezone.utc)
        if existing and existing.estado == "Calculada":
            await self.comision_repo.update(
                existing,
                {
                    "ventas_totales": round(ventas_totales, 2),
                    "porcentaje": pct * 100,
                    "comision_bruta": comision_bruta,
                    "recuperos": recuperos,
                    "neto_a_pagar": neto,
                    "calculado_por_id": calculado_por_id,
                    "fecha_calculo": now,
                    "detalle_pedidos": {"pedido_ids": pedido_ids},
                    "detalle_devoluciones": {"devolucion_ids": dev_ids},
                },
            )
        else:
            new_com = ComisionModel(
                distribuidor=distribuidor,
                mes=mes,
                anio=anio,
                ventas_totales=round(ventas_totales, 2),
                porcentaje=pct * 100,
                comision_bruta=comision_bruta,
                recuperos=recuperos,
                neto_a_pagar=neto,
                estado="Calculada",
                calculado_por_id=calculado_por_id,
                fecha_calculo=now,
                detalle_pedidos={"pedido_ids": pedido_ids},
                detalle_devoluciones={"devolucion_ids": dev_ids},
            )
            await self.comision_repo.create(new_com)

        logger.info(
            "Comision calculada: %s %d/%d neto=%.2f",
            distribuidor, mes, anio, neto,
        )

        return ComisionDistribuidorResult(
            distribuidor=distribuidor,
            ventas_totales=round(ventas_totales, 2),
            porcentaje=pct * 100,
            comision_bruta=comision_bruta,
            recuperos=recuperos,
            neto_a_pagar=neto,
        )

    # ------------------------------------------------------------------
    # Save (POST)
    # ------------------------------------------------------------------

    async def save(
        self,
        data: ComisionCalculoRequest,
        calculado_por_id: uuid.UUID,
    ) -> ComisionResponse:
        """Save a commission calculation result."""
        calc = await self.calculate(data, calculado_por_id)
        if not calc.commissions:
            raise ValidationException("No se generaron comisiones para el periodo")
        # Return the first commission for the specified distribuidor
        dist = data.distribuidor or calc.commissions[0].distribuidor
        com = await self.comision_repo.get_by_period(dist, data.mes, data.anio)
        if not com:
            raise NotFoundException("Comision", f"{dist} {data.mes}/{data.anio}")
        return ComisionResponse.model_validate(com)

    # ------------------------------------------------------------------
    # Approve
    # ------------------------------------------------------------------

    async def approve(
        self,
        comision_id: uuid.UUID,
        aprobador_id: uuid.UUID,
        observaciones: Optional[str] = None,
    ) -> ComisionResponse:
        """Approve a calculated commission."""
        com = await self.comision_repo.get(comision_id)
        if not com:
            raise NotFoundException("Comision", str(comision_id))
        if com.estado != "Calculada":
            raise BadRequestException(
                f"No se puede aprobar una comision en estado {com.estado}"
            )

        now = datetime.now(timezone.utc)
        update_data: dict = {
            "estado": "Aprobada",
            "aprobado_por_id": aprobador_id,
            "fecha_aprobacion": now,
        }
        if observaciones:
            update_data["observaciones"] = observaciones

        com = await self.comision_repo.update(com, update_data)
        logger.info("Comision aprobada: %s %d/%d", com.distribuidor, com.mes, com.anio)
        return ComisionResponse.model_validate(com)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    async def summary(self, mes: int, anio: int) -> ComisionSummaryResponse:
        """Get a summary of commissions for a period across all distributors."""
        items = await self.comision_repo.get_multi(
            skip=0, limit=100, mes=mes, anio=anio
        )
        distribuidores = []
        ventas_total = 0.0
        comisiones_total = 0.0
        recuperos_total = 0.0
        neto_total = 0.0

        for c in items:
            distribuidores.append(
                ComisionDistribuidorResult(
                    distribuidor=c.distribuidor,
                    ventas_totales=c.ventas_totales,
                    porcentaje=c.porcentaje,
                    comision_bruta=c.comision_bruta,
                    recuperos=c.recuperos,
                    neto_a_pagar=c.neto_a_pagar,
                )
            )
            ventas_total += c.ventas_totales
            comisiones_total += c.comision_bruta
            recuperos_total += c.recuperos
            neto_total += c.neto_a_pagar

        return ComisionSummaryResponse(
            mes=mes,
            anio=anio,
            ventas_totales=round(ventas_total, 2),
            comisiones_totales=round(comisiones_total, 2),
            recuperos_totales=round(recuperos_total, 2),
            neto_total=round(neto_total, 2),
            distribuidores=distribuidores,
        )
