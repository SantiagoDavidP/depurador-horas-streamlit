"""Business logic for Devoluciones.

Key rules implemented:
- Associated order must exist and be Aprobado
- Invoice format validation (F001-00012345)
- Products marked inafecto_devolucion cannot be returned
- Quantity cannot exceed original order detail quantity
- Valorizado = cantidad * precio_unitario_original
- Code generation DEV-YYYY-NNNN
- State machine: En Proceso -> Aprobada | Rechazada
"""

from __future__ import annotations


import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.exceptions import (
    BadRequestException,
    NotFoundException,
    ValidationException,
)
from api.db.models.devolucion import DevolucionModel
from api.models.common import PaginatedResponse
from api.models.devolucion import (
    DevolucionCreate,
    DevolucionResponse,
    DevolucionUpdate,
    DevolucionValorizadoResponse,
    ReturnableProductResponse,
)
from api.repositories.devolucion_repository import DevolucionRepository
from api.repositories.pedido_repository import PedidoRepository
from api.repositories.producto_repository import ProductoRepository

logger = logging.getLogger("bonapharm.devolucion_service")


class DevolucionService:
    """Orchestrates return creation, approval, rejection, and valorizado calculation."""

    def __init__(
        self,
        devolucion_repo: DevolucionRepository,
        pedido_repo: PedidoRepository,
        producto_repo: ProductoRepository,
        session: AsyncSession,
    ) -> None:
        self.devolucion_repo = devolucion_repo
        self.pedido_repo = pedido_repo
        self.producto_repo = producto_repo
        self.session = session

    # ------------------------------------------------------------------
    # List / Get
    # ------------------------------------------------------------------

    async def list(
        self,
        skip: int = 0,
        limit: int = 20,
        estado: Optional[str] = None,
        pedido_id: Optional[uuid.UUID] = None,
        producto_id: Optional[uuid.UUID] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[DevolucionResponse]:
        """List returns with pagination and filters."""
        items = await self.devolucion_repo.get_multi(
            skip=skip,
            limit=limit,
            estado=estado,
            pedido_id=pedido_id,
            producto_id=producto_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            search=search,
        )
        total = await self.devolucion_repo.count(
            estado=estado,
            pedido_id=pedido_id,
            producto_id=producto_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            search=search,
        )
        return PaginatedResponse(
            items=[self._to_response(i) for i in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get(self, devolucion_id: uuid.UUID) -> DevolucionResponse:
        """Get a return by ID."""
        dev = await self.devolucion_repo.get(devolucion_id)
        if not dev:
            raise NotFoundException("Devolucion", str(devolucion_id))
        return self._to_response(dev)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(
        self,
        data: DevolucionCreate,
        solicitante_id: uuid.UUID,
    ) -> DevolucionResponse:
        """Register a new return.

        Validates:
        - Order exists and is Aprobado
        - Product exists and is not inafecto
        - Quantity does not exceed original - already returned
        - Calculates valorizado
        """
        # Validate order
        pedido = await self.pedido_repo.get(data.pedido_id)
        if not pedido:
            raise NotFoundException("Pedido", str(data.pedido_id))
        if pedido.estado != "Aprobado":
            raise ValidationException(
                "Solo se pueden crear devoluciones de pedidos aprobados"
            )

        # Validate product
        producto = await self.producto_repo.get(data.producto_id)
        if not producto:
            raise NotFoundException("Producto", str(data.producto_id))
        if producto.inafecto_devolucion:
            raise ValidationException(
                f"Producto {producto.nombre} esta marcado como inafecto a devolucion"
            )

        # Find original detail line
        detalle = next(
            (d for d in pedido.detalles if d.producto_id == data.producto_id),
            None,
        )
        if not detalle:
            raise ValidationException(
                "El producto no pertenece al pedido indicado"
            )

        # Validate quantity
        already_returned = await self.devolucion_repo.get_already_returned_qty(
            data.pedido_id, data.producto_id
        )
        available = detalle.cantidad - already_returned
        if data.cantidad > available:
            raise ValidationException(
                f"Cantidad solicitada ({data.cantidad}) excede la disponible ({available})"
            )

        # Calculate valorizado
        valorizado = round(data.cantidad * detalle.precio_unitario, 2)

        # Generate code
        year = datetime.now(timezone.utc).year
        codigo = await self.devolucion_repo.next_codigo(year)

        devolucion = DevolucionModel(
            codigo_devolucion=codigo,
            pedido_id=data.pedido_id,
            numero_factura=data.numero_factura,
            producto_id=data.producto_id,
            cantidad=data.cantidad,
            lote=data.lote,
            razon=data.razon,
            estado="En Proceso",
            valorizado=valorizado,
            observaciones=data.observaciones,
            solicitante_id=solicitante_id,
        )

        devolucion = await self.devolucion_repo.create(devolucion)
        logger.info("Devolucion creada: %s", devolucion.codigo_devolucion)
        return self._to_response(devolucion)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update(
        self,
        devolucion_id: uuid.UUID,
        data: DevolucionUpdate,
    ) -> DevolucionResponse:
        """Update a return that is still En Proceso."""
        dev = await self.devolucion_repo.get(devolucion_id)
        if not dev:
            raise NotFoundException("Devolucion", str(devolucion_id))
        if dev.estado != "En Proceso":
            raise BadRequestException(
                "Solo se pueden editar devoluciones en estado En Proceso"
            )

        update_data = data.model_dump(exclude_unset=True)

        # Recalculate valorizado if quantity changed
        if "cantidad" in update_data:
            pedido = await self.pedido_repo.get(dev.pedido_id)
            if pedido:
                detalle = next(
                    (d for d in pedido.detalles if d.producto_id == dev.producto_id),
                    None,
                )
                if detalle:
                    update_data["valorizado"] = round(
                        update_data["cantidad"] * detalle.precio_unitario, 2
                    )

        dev = await self.devolucion_repo.update(dev, update_data)
        return self._to_response(dev)

    # ------------------------------------------------------------------
    # Approve / Reject
    # ------------------------------------------------------------------

    async def approve(
        self,
        devolucion_id: uuid.UUID,
        aprobador_id: uuid.UUID,
    ) -> DevolucionResponse:
        """Approve a return."""
        dev = await self.devolucion_repo.get(devolucion_id)
        if not dev:
            raise NotFoundException("Devolucion", str(devolucion_id))
        if dev.estado != "En Proceso":
            raise BadRequestException(
                f"No se puede aprobar una devolucion en estado {dev.estado}"
            )

        now = datetime.now(timezone.utc)
        dev = await self.devolucion_repo.update(
            dev,
            {
                "estado": "Aprobada",
                "aprobador_id": aprobador_id,
                "fecha_aprobacion": now,
            },
        )
        logger.info("Devolucion aprobada: %s", dev.codigo_devolucion)
        return self._to_response(dev)

    async def reject(
        self,
        devolucion_id: uuid.UUID,
        aprobador_id: uuid.UUID,
        motivo_rechazo: str,
    ) -> DevolucionResponse:
        """Reject a return."""
        dev = await self.devolucion_repo.get(devolucion_id)
        if not dev:
            raise NotFoundException("Devolucion", str(devolucion_id))
        if dev.estado != "En Proceso":
            raise BadRequestException(
                f"No se puede rechazar una devolucion en estado {dev.estado}"
            )

        now = datetime.now(timezone.utc)
        dev = await self.devolucion_repo.update(
            dev,
            {
                "estado": "Rechazada",
                "aprobador_id": aprobador_id,
                "fecha_aprobacion": now,
                "motivo_rechazo": motivo_rechazo,
            },
        )
        logger.info("Devolucion rechazada: %s", dev.codigo_devolucion)
        return self._to_response(dev)

    # ------------------------------------------------------------------
    # Valorizado calculation
    # ------------------------------------------------------------------

    async def calculate_valorizado(
        self,
        devolucion_id: uuid.UUID,
    ) -> list[DevolucionValorizadoResponse]:
        """Calculate valorizado for a return (preview before save)."""
        dev = await self.devolucion_repo.get(devolucion_id)
        if not dev:
            raise NotFoundException("Devolucion", str(devolucion_id))

        pedido = await self.pedido_repo.get(dev.pedido_id)
        if not pedido:
            raise NotFoundException("Pedido", str(dev.pedido_id))

        detalle = next(
            (d for d in pedido.detalles if d.producto_id == dev.producto_id),
            None,
        )
        precio = detalle.precio_unitario if detalle else 0.0
        producto = await self.producto_repo.get(dev.producto_id)
        nombre = producto.nombre if producto else "Desconocido"

        return [
            DevolucionValorizadoResponse(
                producto_id=dev.producto_id,
                producto_nombre=nombre,
                cantidad=dev.cantidad,
                precio_unitario=precio,
                valorizado=round(dev.cantidad * precio, 2),
            )
        ]

    # ------------------------------------------------------------------
    # Returnable products
    # ------------------------------------------------------------------

    async def get_returnable_products(
        self,
        pedido_id: uuid.UUID,
    ) -> list[ReturnableProductResponse]:
        """List products from an order that can still be returned."""
        pedido = await self.pedido_repo.get(pedido_id)
        if not pedido:
            raise NotFoundException("Pedido", str(pedido_id))
        if pedido.estado != "Aprobado":
            raise ValidationException("Solo pedidos aprobados permiten devoluciones")

        result: list[ReturnableProductResponse] = []
        for d in pedido.detalles:
            if d.tipo == "Bonificacion":
                continue
            producto = await self.producto_repo.get(d.producto_id)
            if not producto or producto.inafecto_devolucion:
                continue

            already = await self.devolucion_repo.get_already_returned_qty(
                pedido_id, d.producto_id
            )
            available = d.cantidad - already
            if available <= 0:
                continue

            result.append(
                ReturnableProductResponse(
                    producto_id=d.producto_id,
                    producto_nombre=producto.nombre,
                    codigo_sap=producto.codigo_sap,
                    cantidad_original=d.cantidad,
                    cantidad_ya_devuelta=already,
                    cantidad_disponible=available,
                    precio_unitario=d.precio_unitario,
                )
            )

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _to_response(self, dev: DevolucionModel) -> DevolucionResponse:
        return DevolucionResponse(
            id=dev.id,
            codigo_devolucion=dev.codigo_devolucion,
            pedido_id=dev.pedido_id,
            numero_factura=dev.numero_factura,
            producto_id=dev.producto_id,
            cantidad=dev.cantidad,
            lote=dev.lote,
            razon=dev.razon,
            estado=dev.estado,
            valorizado=dev.valorizado,
            observaciones=dev.observaciones,
            solicitante_id=dev.solicitante_id,
            aprobador_id=dev.aprobador_id,
            fecha_aprobacion=dev.fecha_aprobacion,
            motivo_rechazo=dev.motivo_rechazo,
            created_at=dev.created_at,
            updated_at=dev.updated_at,
            producto_nombre=dev.producto.nombre if dev.producto else None,
            producto_codigo_sap=dev.producto.codigo_sap if dev.producto else None,
        )
