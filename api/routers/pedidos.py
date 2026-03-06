"""Pedidos router -- 13 endpoints.

POST   /api/orders                       Create order
GET    /api/orders                        List orders
GET    /api/orders/draft                  List drafts
GET    /api/orders/pending                Pending approval
GET    /api/orders/pending/count          Pending count
GET    /api/orders/{id}                   Get order detail
PUT    /api/orders/{id}                   Edit sent order
PUT    /api/orders/{id}/draft             Update draft
POST   /api/orders/{id}/submit            Submit draft
POST   /api/orders/{id}/resubmit          Resubmit rejected
POST   /api/orders/{id}/validate          Validate before send
POST   /api/orders/{id}/approve           Approve order
POST   /api/orders/{id}/reject            Reject order
POST   /api/orders/{id}/comments          Add comment
GET    /api/orders/{id}/comments          List comments
GET    /api/orders/{id}/approval-detail   Approval detail view
GET    /api/orders/{id}/returnable-products  Returnable products
"""

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Path, Query, status

from api.core.dependencies import AdminOrFinanzas, CurrentUser, OnlyAdmin, SessionDep
from api.models.common import PaginatedResponse
from api.models.devolucion import ReturnableProductResponse
from api.models.pedido import (
    ComentarioCreate,
    ComentarioResponse,
    PedidoApproveRequest,
    PedidoApproveResponse,
    PedidoCreate,
    PedidoListResponse,
    PedidoRejectRequest,
    PedidoRejectResponse,
    PedidoResponse,
    PedidoUpdate,
)
from api.repositories.devolucion_repository import DevolucionRepository
from api.repositories.pedido_repository import PedidoRepository
from api.repositories.producto_repository import ProductoRepository
from api.services.devolucion_service import DevolucionService
from api.services.pedido_service import PedidoService

router = APIRouter(prefix="/api/orders", tags=["pedidos"])


def _get_pedido_service(db: SessionDep) -> PedidoService:
    return PedidoService(
        pedido_repo=PedidoRepository(db),
        producto_repo=ProductoRepository(db),
        session=db,
    )


def _get_devolucion_service(db: SessionDep) -> DevolucionService:
    return DevolucionService(
        devolucion_repo=DevolucionRepository(db),
        pedido_repo=PedidoRepository(db),
        producto_repo=ProductoRepository(db),
        session=db,
    )


# ------------------------------------------------------------------
# POST /api/orders
# ------------------------------------------------------------------
@router.post("/", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: PedidoCreate,
    user: CurrentUser,
    svc: PedidoService = Depends(_get_pedido_service),
) -> PedidoResponse:
    """Create a new order with status Borrador or Enviado."""
    return await svc.create(data, vendedor_id=user.id)


# ------------------------------------------------------------------
# GET /api/orders
# ------------------------------------------------------------------
@router.get("/", response_model=PaginatedResponse[PedidoListResponse])
async def list_orders(
    user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    estado: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    search: Optional[str] = None,
    svc: PedidoService = Depends(_get_pedido_service),
) -> PaginatedResponse[PedidoListResponse]:
    """List orders for the authenticated vendor (or all if admin)."""
    vendedor_id = user.id if user.rol == "Vendedor" else None
    return await svc.list(
        skip=skip,
        limit=limit,
        vendedor_id=vendedor_id,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        search=search,
    )


# ------------------------------------------------------------------
# GET /api/orders/draft
# ------------------------------------------------------------------
@router.get("/draft", response_model=PaginatedResponse[PedidoListResponse])
async def list_drafts(
    user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: PedidoService = Depends(_get_pedido_service),
) -> PaginatedResponse[PedidoListResponse]:
    """List draft orders for the authenticated vendor."""
    return await svc.get_drafts(vendedor_id=user.id, skip=skip, limit=limit)


# ------------------------------------------------------------------
# GET /api/orders/pending
# ------------------------------------------------------------------
@router.get("/pending", response_model=PaginatedResponse[PedidoListResponse])
async def list_pending(
    user: AdminOrFinanzas,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Optional[str] = None,
    svc: PedidoService = Depends(_get_pedido_service),
) -> PaginatedResponse[PedidoListResponse]:
    """List orders pending approval (estado=Enviado)."""
    return await svc.list(skip=skip, limit=limit, estado="Enviado", search=search)


# ------------------------------------------------------------------
# GET /api/orders/pending/count
# ------------------------------------------------------------------
@router.get("/pending/count")
async def pending_count(
    user: AdminOrFinanzas,
    svc: PedidoService = Depends(_get_pedido_service),
) -> dict[str, int]:
    """Count of orders pending approval (for header badge)."""
    count = await svc.pending_count()
    return {"count": count}


# ------------------------------------------------------------------
# GET /api/orders/{id}
# ------------------------------------------------------------------
@router.get("/{order_id}", response_model=PedidoResponse)
async def get_order(
    order_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    svc: PedidoService = Depends(_get_pedido_service),
) -> PedidoResponse:
    """Get full order detail by ID."""
    return await svc.get(order_id)


# ------------------------------------------------------------------
# GET /api/orders/{id}/approval-detail
# ------------------------------------------------------------------
@router.get("/{order_id}/approval-detail", response_model=PedidoResponse)
async def get_approval_detail(
    order_id: Annotated[uuid.UUID, Path()],
    user: AdminOrFinanzas,
    svc: PedidoService = Depends(_get_pedido_service),
) -> PedidoResponse:
    """Get order detail for approval review (same as get but restricted to admins)."""
    return await svc.get(order_id)


# ------------------------------------------------------------------
# PUT /api/orders/{id}
# ------------------------------------------------------------------
@router.put("/{order_id}", response_model=PedidoResponse)
async def update_order(
    order_id: Annotated[uuid.UUID, Path()],
    data: PedidoUpdate,
    user: CurrentUser,
    svc: PedidoService = Depends(_get_pedido_service),
) -> PedidoResponse:
    """Edit a sent order (only estado=Enviado)."""
    return await svc.update_sent(order_id, data, vendedor_id=user.id)


# ------------------------------------------------------------------
# PUT /api/orders/{id}/draft
# ------------------------------------------------------------------
@router.put("/{order_id}/draft", response_model=PedidoResponse)
async def update_draft(
    order_id: Annotated[uuid.UUID, Path()],
    data: PedidoUpdate,
    user: CurrentUser,
    svc: PedidoService = Depends(_get_pedido_service),
) -> PedidoResponse:
    """Update a draft order."""
    return await svc.update_draft(order_id, data, vendedor_id=user.id)


# ------------------------------------------------------------------
# POST /api/orders/{id}/submit
# ------------------------------------------------------------------
@router.post("/{order_id}/submit", response_model=PedidoResponse)
async def submit_order(
    order_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    svc: PedidoService = Depends(_get_pedido_service),
) -> PedidoResponse:
    """Submit a draft order (Borrador -> Enviado)."""
    return await svc.submit(order_id, vendedor_id=user.id)


# ------------------------------------------------------------------
# POST /api/orders/{id}/resubmit
# ------------------------------------------------------------------
@router.post("/{order_id}/resubmit", response_model=PedidoResponse)
async def resubmit_order(
    order_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    svc: PedidoService = Depends(_get_pedido_service),
) -> PedidoResponse:
    """Resubmit a rejected order (creates new version as Enviado)."""
    return await svc.resubmit(order_id, vendedor_id=user.id)


# ------------------------------------------------------------------
# POST /api/orders/{id}/validate
# ------------------------------------------------------------------
@router.post("/{order_id}/validate")
async def validate_order(
    order_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    svc: PedidoService = Depends(_get_pedido_service),
) -> dict:
    """Validate order before submission."""
    return await svc.validate(order_id)


# ------------------------------------------------------------------
# POST /api/orders/{id}/approve
# ------------------------------------------------------------------
@router.post("/{order_id}/approve", response_model=PedidoApproveResponse)
async def approve_order(
    order_id: Annotated[uuid.UUID, Path()],
    data: PedidoApproveRequest,
    user: AdminOrFinanzas,
    svc: PedidoService = Depends(_get_pedido_service),
) -> PedidoApproveResponse:
    """Approve a pending order."""
    return await svc.approve(order_id, aprobador_id=user.id, comentarios=data.comentarios)


# ------------------------------------------------------------------
# POST /api/orders/{id}/reject
# ------------------------------------------------------------------
@router.post("/{order_id}/reject", response_model=PedidoRejectResponse)
async def reject_order(
    order_id: Annotated[uuid.UUID, Path()],
    data: PedidoRejectRequest,
    user: AdminOrFinanzas,
    svc: PedidoService = Depends(_get_pedido_service),
) -> PedidoRejectResponse:
    """Reject a pending order."""
    return await svc.reject(order_id, aprobador_id=user.id, motivo_rechazo=data.motivo_rechazo)


# ------------------------------------------------------------------
# POST /api/orders/{id}/comments
# ------------------------------------------------------------------
@router.post(
    "/{order_id}/comments",
    response_model=ComentarioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    order_id: Annotated[uuid.UUID, Path()],
    data: ComentarioCreate,
    user: CurrentUser,
    svc: PedidoService = Depends(_get_pedido_service),
) -> ComentarioResponse:
    """Add an internal comment to an order."""
    return await svc.add_comment(order_id, user_id=user.id, data=data)


# ------------------------------------------------------------------
# GET /api/orders/{id}/comments
# ------------------------------------------------------------------
@router.get("/{order_id}/comments", response_model=list[ComentarioResponse])
async def list_comments(
    order_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    svc: PedidoService = Depends(_get_pedido_service),
) -> list[ComentarioResponse]:
    """List comments for an order."""
    return await svc.get_comments(order_id)


# ------------------------------------------------------------------
# GET /api/orders/{id}/returnable-products
# ------------------------------------------------------------------
@router.get(
    "/{order_id}/returnable-products",
    response_model=list[ReturnableProductResponse],
)
async def get_returnable_products(
    order_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    dsvc: DevolucionService = Depends(_get_devolucion_service),
) -> list[ReturnableProductResponse]:
    """List products from the order that can still be returned."""
    return await dsvc.get_returnable_products(order_id)
