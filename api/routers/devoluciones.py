"""Devoluciones router -- 8 endpoints.

GET    /api/returns                       List returns
GET    /api/returns/reasons               Return reasons
GET    /api/returns/{id}                  Get return detail
POST   /api/returns                       Create return
PUT    /api/returns/{id}                  Update return
POST   /api/returns/{id}/approve          Approve return
POST   /api/returns/{id}/reject           Reject return
POST   /api/returns/{id}/calculate-valorizado  Calculate valorizado
"""

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.dependencies import AdminOrFinanzas, CurrentUser, SessionDep
from api.db.models.config import RazonDevolucionModel
from api.models.common import PaginatedResponse
from api.models.devolucion import (
    DevolucionApproveRequest,
    DevolucionCreate,
    DevolucionRejectRequest,
    DevolucionResponse,
    DevolucionUpdate,
    DevolucionValorizadoResponse,
    RazonDevolucionResponse,
)
from api.repositories.devolucion_repository import DevolucionRepository
from api.repositories.pedido_repository import PedidoRepository
from api.repositories.producto_repository import ProductoRepository
from api.services.devolucion_service import DevolucionService

router = APIRouter(prefix="/api/returns", tags=["devoluciones"])


def _get_service(db: SessionDep) -> DevolucionService:
    return DevolucionService(
        devolucion_repo=DevolucionRepository(db),
        pedido_repo=PedidoRepository(db),
        producto_repo=ProductoRepository(db),
        session=db,
    )


# ------------------------------------------------------------------
# GET /api/returns
# ------------------------------------------------------------------
@router.get("/", response_model=PaginatedResponse[DevolucionResponse])
async def list_returns(
    user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    estado: Optional[str] = None,
    pedido_id: Optional[uuid.UUID] = None,
    producto_id: Optional[uuid.UUID] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    search: Optional[str] = None,
    svc: DevolucionService = Depends(_get_service),
) -> PaginatedResponse[DevolucionResponse]:
    """List returns with filters and pagination."""
    return await svc.list(
        skip=skip,
        limit=limit,
        estado=estado,
        pedido_id=pedido_id,
        producto_id=producto_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        search=search,
    )


# ------------------------------------------------------------------
# GET /api/returns/reasons
# ------------------------------------------------------------------
@router.get("/reasons", response_model=list[RazonDevolucionResponse])
async def list_reasons(
    db: SessionDep,
    user: CurrentUser,
) -> list[RazonDevolucionResponse]:
    """List available return reasons."""
    stmt = select(RazonDevolucionModel).where(RazonDevolucionModel.activo == True)  # noqa: E712
    result = await db.execute(stmt)
    rows = result.scalars().all()
    if not rows:
        # Return hardcoded defaults if DB is empty
        return [
            RazonDevolucionResponse(id=uuid.uuid4(), nombre=r, activo=True)
            for r in [
                "Producto daniado",
                "Fecha de vencimiento proxima",
                "Error en el pedido",
                "Cliente rechazo entrega",
                "Defecto de fabricacion",
            ]
        ]
    return [RazonDevolucionResponse.model_validate(r) for r in rows]


# ------------------------------------------------------------------
# GET /api/returns/{id}
# ------------------------------------------------------------------
@router.get("/{return_id}", response_model=DevolucionResponse)
async def get_return(
    return_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    svc: DevolucionService = Depends(_get_service),
) -> DevolucionResponse:
    """Get return detail by ID."""
    return await svc.get(return_id)


# ------------------------------------------------------------------
# POST /api/returns
# ------------------------------------------------------------------
@router.post("/", response_model=DevolucionResponse, status_code=status.HTTP_201_CREATED)
async def create_return(
    data: DevolucionCreate,
    user: CurrentUser,
    svc: DevolucionService = Depends(_get_service),
) -> DevolucionResponse:
    """Register a new return."""
    return await svc.create(data, solicitante_id=user.id)


# ------------------------------------------------------------------
# PUT /api/returns/{id}
# ------------------------------------------------------------------
@router.put("/{return_id}", response_model=DevolucionResponse)
async def update_return(
    return_id: Annotated[uuid.UUID, Path()],
    data: DevolucionUpdate,
    user: CurrentUser,
    svc: DevolucionService = Depends(_get_service),
) -> DevolucionResponse:
    """Update a return (only if En Proceso)."""
    return await svc.update(return_id, data)


# ------------------------------------------------------------------
# POST /api/returns/{id}/approve
# ------------------------------------------------------------------
@router.post("/{return_id}/approve", response_model=DevolucionResponse)
async def approve_return(
    return_id: Annotated[uuid.UUID, Path()],
    data: DevolucionApproveRequest,
    user: AdminOrFinanzas,
    svc: DevolucionService = Depends(_get_service),
) -> DevolucionResponse:
    """Approve a return."""
    return await svc.approve(return_id, aprobador_id=user.id)


# ------------------------------------------------------------------
# POST /api/returns/{id}/reject
# ------------------------------------------------------------------
@router.post("/{return_id}/reject", response_model=DevolucionResponse)
async def reject_return(
    return_id: Annotated[uuid.UUID, Path()],
    data: DevolucionRejectRequest,
    user: AdminOrFinanzas,
    svc: DevolucionService = Depends(_get_service),
) -> DevolucionResponse:
    """Reject a return with a reason."""
    return await svc.reject(return_id, aprobador_id=user.id, motivo_rechazo=data.motivo_rechazo)


# ------------------------------------------------------------------
# POST /api/returns/{id}/calculate-valorizado
# ------------------------------------------------------------------
@router.post(
    "/{return_id}/calculate-valorizado",
    response_model=list[DevolucionValorizadoResponse],
)
async def calculate_valorizado(
    return_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    svc: DevolucionService = Depends(_get_service),
) -> list[DevolucionValorizadoResponse]:
    """Calculate valorizado for a return before saving."""
    return await svc.calculate_valorizado(return_id)
