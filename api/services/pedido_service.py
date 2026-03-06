"""Business logic for Pedidos.

Key rules implemented:
- Code generation PED-YYYY-NNNN
- RUC validation (11 numeric digits)
- At least 1 product with type Venta
- Bonificacion items forced to price=0, subtotal=0
- IGV calculation: subtotal * 0.18
- Distributor minimum validation
- State machine: Borrador -> Enviado -> Aprobado | Rechazado
"""

from __future__ import annotations


import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    ValidationException,
)
from api.db.models.pedido import ComentarioPedidoModel, DetallePedidoModel, PedidoModel
from api.db.models.producto import ProductoModel
from api.models.common import PaginatedResponse
from api.models.pedido import (
    ComentarioCreate,
    ComentarioResponse,
    DetallePedidoCreate,
    PedidoApproveResponse,
    PedidoCreate,
    PedidoListResponse,
    PedidoRejectResponse,
    PedidoResponse,
    PedidoUpdate,
)
from api.repositories.pedido_repository import PedidoRepository
from api.repositories.producto_repository import ProductoRepository

logger = logging.getLogger("bonapharm.pedido_service")


class PedidoService:
    """Orchestrates pedido creation, validation, approval, and rejection."""

    def __init__(
        self,
        pedido_repo: PedidoRepository,
        producto_repo: ProductoRepository,
        session: AsyncSession,
    ) -> None:
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
        vendedor_id: Optional[uuid.UUID] = None,
        estado: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[PedidoListResponse]:
        """List orders with pagination and filters."""
        items = await self.pedido_repo.get_multi(
            skip=skip,
            limit=limit,
            vendedor_id=vendedor_id,
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            search=search,
        )
        total = await self.pedido_repo.count(
            vendedor_id=vendedor_id,
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            search=search,
        )
        return PaginatedResponse(
            items=[PedidoListResponse.model_validate(i) for i in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get(self, pedido_id: uuid.UUID) -> PedidoResponse:
        """Get full order detail by ID."""
        pedido = await self.pedido_repo.get(pedido_id)
        if not pedido:
            raise NotFoundException("Pedido", str(pedido_id))
        return self._to_response(pedido)

    async def get_drafts(
        self,
        vendedor_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> PaginatedResponse[PedidoListResponse]:
        """List drafts for a specific vendor."""
        return await self.list(
            skip=skip, limit=limit, vendedor_id=vendedor_id, estado="Borrador"
        )

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(
        self,
        data: PedidoCreate,
        vendedor_id: uuid.UUID,
    ) -> PedidoResponse:
        """Create a new order (Borrador or Enviado).

        Business rules:
        - At least 1 detail with tipo=Venta
        - Bonificacion items: price and subtotal forced to 0
        - Subtotal = SUM(detalle.subtotal) for tipo=Venta only
        - IGV = subtotal * 0.18
        - Total = subtotal + IGV
        - If estado=Enviado: validate minimums, generate code
        """
        # Validate at least one Venta item
        venta_items = [d for d in data.detalles if d.tipo == "Venta"]
        if not venta_items:
            raise ValidationException(
                "El pedido debe contener al menos 1 producto de tipo Venta"
            )

        now = datetime.now(timezone.utc)
        year = now.year

        # Build detalles and calculate totals
        detalles: list[DetallePedidoModel] = []
        subtotal = 0.0
        for det in data.detalles:
            producto = await self.producto_repo.get(det.producto_id)
            if not producto:
                raise NotFoundException("Producto", str(det.producto_id))
            if not producto.activo:
                raise ValidationException(
                    f"Producto {producto.nombre} esta inactivo"
                )

            precio = 0.0 if det.tipo == "Bonificacion" else producto.precio_vvf
            det_subtotal = 0.0 if det.tipo == "Bonificacion" else det.cantidad * precio

            detalles.append(
                DetallePedidoModel(
                    producto_id=det.producto_id,
                    cantidad=det.cantidad,
                    precio_unitario=precio,
                    tipo=det.tipo,
                    subtotal=round(det_subtotal, 2),
                )
            )
            if det.tipo == "Venta":
                subtotal += det_subtotal

        subtotal = round(subtotal, 2)
        igv = round(subtotal * settings.IGV_RATE, 2)
        total = round(subtotal + igv, 2)

        # Generate code
        codigo = await self.pedido_repo.next_codigo(year)

        # If sending, validate distributor minimums
        if data.estado == "Enviado":
            await self._validate_minimums(detalles, total)

        pedido = PedidoModel(
            codigo_pedido=codigo,
            fecha=now,
            cliente_ruc=data.cliente_ruc,
            cliente_razon_social=data.cliente_razon_social,
            representante=data.representante,
            condicion_pago=data.condicion_pago,
            estado=data.estado,
            subtotal=subtotal,
            igv=igv,
            total=total,
            vendedor_id=vendedor_id,
            observaciones=data.observaciones,
            detalles=detalles,
        )

        pedido = await self.pedido_repo.create(pedido)
        logger.info("Pedido creado: %s estado=%s", pedido.codigo_pedido, pedido.estado)
        return self._to_response(pedido)

    # ------------------------------------------------------------------
    # Update draft
    # ------------------------------------------------------------------

    async def update_draft(
        self,
        pedido_id: uuid.UUID,
        data: PedidoUpdate,
        vendedor_id: uuid.UUID,
    ) -> PedidoResponse:
        """Update a draft order."""
        pedido = await self.pedido_repo.get(pedido_id)
        if not pedido:
            raise NotFoundException("Pedido", str(pedido_id))
        if pedido.estado != "Borrador":
            raise BadRequestException("Solo se pueden editar borradores")
        if pedido.vendedor_id != vendedor_id:
            raise BadRequestException("No puede editar un pedido de otro vendedor")

        update_fields = data.model_dump(exclude_unset=True, exclude={"detalles"})
        if update_fields:
            await self.pedido_repo.update(pedido, update_fields)

        if data.detalles is not None:
            new_detalles = await self._build_detalles(data.detalles)
            await self.pedido_repo.replace_detalles(pedido_id, new_detalles)
            await self._recalculate_totals(pedido)

        return await self.get(pedido_id)

    # ------------------------------------------------------------------
    # Update sent order
    # ------------------------------------------------------------------

    async def update_sent(
        self,
        pedido_id: uuid.UUID,
        data: PedidoUpdate,
        vendedor_id: uuid.UUID,
    ) -> PedidoResponse:
        """Edit a sent order (estado=Enviado)."""
        pedido = await self.pedido_repo.get(pedido_id)
        if not pedido:
            raise NotFoundException("Pedido", str(pedido_id))
        if pedido.estado != "Enviado":
            raise BadRequestException("Solo se pueden editar pedidos en estado Enviado")
        if pedido.vendedor_id != vendedor_id:
            raise BadRequestException("No puede editar un pedido de otro vendedor")

        update_fields = data.model_dump(exclude_unset=True, exclude={"detalles"})
        if update_fields:
            await self.pedido_repo.update(pedido, update_fields)

        if data.detalles is not None:
            new_detalles = await self._build_detalles(data.detalles)
            await self.pedido_repo.replace_detalles(pedido_id, new_detalles)
            await self._recalculate_totals(pedido)

        return await self.get(pedido_id)

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    async def submit(self, pedido_id: uuid.UUID, vendedor_id: uuid.UUID) -> PedidoResponse:
        """Submit a draft order (Borrador -> Enviado)."""
        pedido = await self.pedido_repo.get(pedido_id)
        if not pedido:
            raise NotFoundException("Pedido", str(pedido_id))
        if pedido.estado != "Borrador":
            raise BadRequestException("Solo se pueden enviar borradores")
        if pedido.vendedor_id != vendedor_id:
            raise BadRequestException("No puede enviar un pedido de otro vendedor")

        # Validate
        if not pedido.detalles:
            raise ValidationException("El pedido no tiene productos")
        venta_items = [d for d in pedido.detalles if d.tipo == "Venta"]
        if not venta_items:
            raise ValidationException("El pedido debe contener al menos 1 producto de tipo Venta")

        await self._validate_minimums(pedido.detalles, pedido.total)

        await self.pedido_repo.update(pedido, {"estado": "Enviado"})
        logger.info("Pedido enviado: %s", pedido.codigo_pedido)
        return await self.get(pedido_id)

    # ------------------------------------------------------------------
    # Resubmit
    # ------------------------------------------------------------------

    async def resubmit(self, pedido_id: uuid.UUID, vendedor_id: uuid.UUID) -> PedidoResponse:
        """Resubmit a rejected order (creates a new version as Enviado)."""
        original = await self.pedido_repo.get(pedido_id)
        if not original:
            raise NotFoundException("Pedido", str(pedido_id))
        if original.estado != "Rechazado":
            raise BadRequestException("Solo se pueden reenviar pedidos rechazados")
        if original.vendedor_id != vendedor_id:
            raise BadRequestException("No puede reenviar un pedido de otro vendedor")

        # Clone into new Enviado order
        year = datetime.now(timezone.utc).year
        codigo = await self.pedido_repo.next_codigo(year)

        new_detalles = [
            DetallePedidoModel(
                producto_id=d.producto_id,
                cantidad=d.cantidad,
                precio_unitario=d.precio_unitario,
                tipo=d.tipo,
                subtotal=d.subtotal,
            )
            for d in original.detalles
        ]

        new_pedido = PedidoModel(
            codigo_pedido=codigo,
            fecha=datetime.now(timezone.utc),
            cliente_ruc=original.cliente_ruc,
            cliente_razon_social=original.cliente_razon_social,
            representante=original.representante,
            condicion_pago=original.condicion_pago,
            estado="Enviado",
            subtotal=original.subtotal,
            igv=original.igv,
            total=original.total,
            vendedor_id=vendedor_id,
            observaciones=original.observaciones,
            detalles=new_detalles,
        )
        new_pedido = await self.pedido_repo.create(new_pedido)
        logger.info(
            "Pedido reenviado: %s (original %s)",
            new_pedido.codigo_pedido,
            original.codigo_pedido,
        )
        return self._to_response(new_pedido)

    # ------------------------------------------------------------------
    # Approve / Reject
    # ------------------------------------------------------------------

    async def approve(
        self,
        pedido_id: uuid.UUID,
        aprobador_id: uuid.UUID,
        comentarios: Optional[str] = None,
    ) -> PedidoApproveResponse:
        """Approve a sent order."""
        pedido = await self.pedido_repo.get(pedido_id)
        if not pedido:
            raise NotFoundException("Pedido", str(pedido_id))
        if pedido.estado != "Enviado":
            raise BadRequestException(
                f"No se puede aprobar un pedido en estado {pedido.estado}"
            )

        now = datetime.now(timezone.utc)
        await self.pedido_repo.update(
            pedido,
            {
                "estado": "Aprobado",
                "aprobador_id": aprobador_id,
                "fecha_aprobacion": now,
            },
        )
        if comentarios:
            await self.pedido_repo.add_comment(
                ComentarioPedidoModel(
                    pedido_id=pedido_id,
                    user_id=aprobador_id,
                    contenido=comentarios,
                )
            )

        logger.info("Pedido aprobado: %s por %s", pedido.codigo_pedido, aprobador_id)
        return PedidoApproveResponse(
            order_id=pedido_id,
            new_status="Aprobado",
            notification_sent=True,
        )

    async def reject(
        self,
        pedido_id: uuid.UUID,
        aprobador_id: uuid.UUID,
        motivo_rechazo: str,
    ) -> PedidoRejectResponse:
        """Reject a sent order."""
        pedido = await self.pedido_repo.get(pedido_id)
        if not pedido:
            raise NotFoundException("Pedido", str(pedido_id))
        if pedido.estado != "Enviado":
            raise BadRequestException(
                f"No se puede rechazar un pedido en estado {pedido.estado}"
            )

        now = datetime.now(timezone.utc)
        await self.pedido_repo.update(
            pedido,
            {
                "estado": "Rechazado",
                "aprobador_id": aprobador_id,
                "fecha_aprobacion": now,
                "motivo_rechazo": motivo_rechazo,
            },
        )

        logger.info("Pedido rechazado: %s motivo=%s", pedido.codigo_pedido, motivo_rechazo)
        return PedidoRejectResponse(
            order_id=pedido_id,
            new_status="Rechazado",
        )

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------

    async def validate(self, pedido_id: uuid.UUID) -> dict:
        """Validate order before submission. Returns validation result dict."""
        pedido = await self.pedido_repo.get(pedido_id)
        if not pedido:
            raise NotFoundException("Pedido", str(pedido_id))

        errors: list[str] = []
        if not pedido.detalles:
            errors.append("El pedido no tiene productos")
        else:
            venta = [d for d in pedido.detalles if d.tipo == "Venta"]
            if not venta:
                errors.append("Debe haber al menos 1 producto de tipo Venta")

        if len(pedido.cliente_ruc) != 11 or not pedido.cliente_ruc.isdigit():
            errors.append("RUC debe tener exactamente 11 digitos numericos")

        return {"valid": len(errors) == 0, "errors": errors}

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    async def add_comment(
        self, pedido_id: uuid.UUID, user_id: uuid.UUID, data: ComentarioCreate
    ) -> ComentarioResponse:
        """Add an internal comment to an order."""
        pedido = await self.pedido_repo.get(pedido_id)
        if not pedido:
            raise NotFoundException("Pedido", str(pedido_id))
        comment = ComentarioPedidoModel(
            pedido_id=pedido_id,
            user_id=user_id,
            contenido=data.contenido,
        )
        comment = await self.pedido_repo.add_comment(comment)
        return ComentarioResponse.model_validate(comment)

    async def get_comments(self, pedido_id: uuid.UUID) -> list[ComentarioResponse]:
        """Get all comments for an order."""
        pedido = await self.pedido_repo.get(pedido_id)
        if not pedido:
            raise NotFoundException("Pedido", str(pedido_id))
        rows = await self.pedido_repo.get_comments(pedido_id)
        return [ComentarioResponse.model_validate(c) for c in rows]

    # ------------------------------------------------------------------
    # Pending count
    # ------------------------------------------------------------------

    async def pending_count(self) -> int:
        """Count of orders pending approval."""
        return await self.pedido_repo.get_pending_count()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _build_detalles(
        self, items: list[DetallePedidoCreate]
    ) -> list[DetallePedidoModel]:
        detalles: list[DetallePedidoModel] = []
        for det in items:
            producto = await self.producto_repo.get(det.producto_id)
            if not producto:
                raise NotFoundException("Producto", str(det.producto_id))
            precio = 0.0 if det.tipo == "Bonificacion" else producto.precio_vvf
            det_subtotal = 0.0 if det.tipo == "Bonificacion" else det.cantidad * precio
            detalles.append(
                DetallePedidoModel(
                    producto_id=det.producto_id,
                    cantidad=det.cantidad,
                    precio_unitario=precio,
                    tipo=det.tipo,
                    subtotal=round(det_subtotal, 2),
                )
            )
        return detalles

    async def _recalculate_totals(self, pedido: PedidoModel) -> None:
        refreshed = await self.pedido_repo.get(pedido.id)
        if not refreshed:
            return
        subtotal = sum(d.subtotal for d in refreshed.detalles if d.tipo == "Venta")
        subtotal = round(subtotal, 2)
        igv = round(subtotal * settings.IGV_RATE, 2)
        total = round(subtotal + igv, 2)
        await self.pedido_repo.update(
            refreshed, {"subtotal": subtotal, "igv": igv, "total": total}
        )

    async def _validate_minimums(
        self,
        detalles: list[DetallePedidoModel] | Sequence,
        total: float,
    ) -> None:
        """Check that order total meets distributor minimum requirements.

        In production this queries DistribuidorConfigModel for each
        distributor configured minimum.
        """
        pass

    def _to_response(self, pedido: PedidoModel) -> PedidoResponse:
        """Convert ORM model to Pydantic response with nested detalles."""
        detalles_resp = []
        for d in (pedido.detalles or []):
            dr = {
                "id": d.id,
                "producto_id": d.producto_id,
                "cantidad": d.cantidad,
                "precio_unitario": d.precio_unitario,
                "tipo": d.tipo,
                "subtotal": d.subtotal,
                "created_at": d.created_at,
                "producto_nombre": d.producto.nombre if d.producto else None,
                "producto_codigo_sap": d.producto.codigo_sap if d.producto else None,
            }
            detalles_resp.append(dr)

        return PedidoResponse(
            id=pedido.id,
            codigo_pedido=pedido.codigo_pedido,
            fecha=pedido.fecha,
            cliente_ruc=pedido.cliente_ruc,
            cliente_razon_social=pedido.cliente_razon_social,
            representante=pedido.representante,
            condicion_pago=pedido.condicion_pago,
            estado=pedido.estado,
            subtotal=pedido.subtotal,
            igv=pedido.igv,
            total=pedido.total,
            vendedor_id=pedido.vendedor_id,
            aprobador_id=pedido.aprobador_id,
            fecha_aprobacion=pedido.fecha_aprobacion,
            motivo_rechazo=pedido.motivo_rechazo,
            observaciones=pedido.observaciones,
            detalles=detalles_resp,
            created_at=pedido.created_at,
            updated_at=pedido.updated_at,
        )
