"""Comisiones router -- 7 endpoints.

GET    /api/commissions                   List commissions
GET    /api/commissions/calculate         Execute calculation
GET    /api/commissions/summary           Period summary
GET    /api/commissions/export            Export to Excel (placeholder)
POST   /api/commissions                   Save calculation result
POST   /api/commissions/{id}/approve      Approve commission
GET    /api/commissions/{id}/detail       Detailed breakdown
"""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Path, Query, status

from api.core.dependencies import CurrentUser, OnlyFinanzas, SessionDep
from api.models.comision import (
    ComisionApproveRequest,
    ComisionCalculoRequest,
    ComisionCalculoResponse,
    ComisionDetailResponse,
    ComisionResponse,
    ComisionSummaryResponse,
)
from api.models.common import PaginatedResponse
from api.repositories.comision_repository import ComisionRepository
from api.repositories.devolucion_repository import DevolucionRepository
from api.repositories.pedido_repository import PedidoRepository
from api.services.comision_service import ComisionService

router = APIRouter(prefix="/api/commissions", tags=["comisiones"])


def _get_service(db: SessionDep) -> ComisionService:
    return ComisionService(
        comision_repo=ComisionRepository(db),
        pedido_repo=PedidoRepository(db),
        devolucion_repo=DevolucionRepository(db),
        session=db,
    )


# ------------------------------------------------------------------
# GET /api/commissions
# ------------------------------------------------------------------
@router.get("/", response_model=PaginatedResponse[ComisionResponse])
async def list_commissions(
    user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    distribuidor: Optional[str] = None,
    mes: Optional[int] = None,
    anio: Optional[int] = None,
    estado: Optional[str] = None,
    svc: ComisionService = Depends(_get_service),
) -> PaginatedResponse[ComisionResponse]:
    """List commission records with filters."""
    return await svc.list(
        skip=skip,
        limit=limit,
        distribuidor=distribuidor,
        mes=mes,
        anio=anio,
        estado=estado,
    )


# ------------------------------------------------------------------
# GET /api/commissions/calculate
# ------------------------------------------------------------------
@router.get("/calculate", response_model=ComisionCalculoResponse)
async def calculate_commissions(
    user: OnlyFinanzas,
    mes: Annotated[int, Query(ge=1, le=12)],
    anio: Annotated[int, Query(ge=2020, le=2100)],
    distribuidor: Optional[str] = None,
    svc: ComisionService = Depends(_get_service),
) -> ComisionCalculoResponse:
    """Execute commission calculation for a period."""
    data = ComisionCalculoRequest(mes=mes, anio=anio, distribuidor=distribuidor)
    return await svc.calculate(data, calculado_por_id=user.id)


# ------------------------------------------------------------------
# GET /api/commissions/summary
# ------------------------------------------------------------------
@router.get("/summary", response_model=ComisionSummaryResponse)
async def commissions_summary(
    user: CurrentUser,
    mes: Annotated[int, Query(ge=1, le=12)],
    anio: Annotated[int, Query(ge=2020, le=2100)],
    svc: ComisionService = Depends(_get_service),
) -> ComisionSummaryResponse:
    """Summary of commissions for a period across all distributors."""
    return await svc.summary(mes, anio)


# ------------------------------------------------------------------
# GET /api/commissions/export
# ------------------------------------------------------------------
@router.get("/export")
async def export_commissions(
    user: OnlyFinanzas,
    mes: Annotated[int, Query(ge=1, le=12)],
    anio: Annotated[int, Query(ge=2020, le=2100)],
) -> dict:
    """Export commission calculations to Excel (placeholder).

    In production this would generate an .xlsx file via openpyxl
    and return a StreamingResponse.
    """
    return {
        "message": f"Exportacion de comisiones {mes}/{anio} generada",
        "format": "xlsx",
        "status": "placeholder",
    }


# ------------------------------------------------------------------
# POST /api/commissions
# ------------------------------------------------------------------
@router.post("/", response_model=ComisionResponse, status_code=status.HTTP_201_CREATED)
async def save_commission(
    data: ComisionCalculoRequest,
    user: OnlyFinanzas,
    svc: ComisionService = Depends(_get_service),
) -> ComisionResponse:
    """Save commission calculation result."""
    return await svc.save(data, calculado_por_id=user.id)


# ------------------------------------------------------------------
# POST /api/commissions/{id}/approve
# ------------------------------------------------------------------
@router.post("/{comision_id}/approve", response_model=ComisionResponse)
async def approve_commission(
    comision_id: Annotated[uuid.UUID, Path()],
    data: ComisionApproveRequest,
    user: OnlyFinanzas,
    svc: ComisionService = Depends(_get_service),
) -> ComisionResponse:
    """Approve a calculated commission."""
    return await svc.approve(
        comision_id,
        aprobador_id=user.id,
        observaciones=data.observaciones,
    )


# ------------------------------------------------------------------
# GET /api/commissions/{id}/detail
# ------------------------------------------------------------------
@router.get("/{comision_id}/detail", response_model=ComisionDetailResponse)
async def commission_detail(
    comision_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    svc: ComisionService = Depends(_get_service),
) -> ComisionDetailResponse:
    """Get detailed breakdown of a commission calculation."""
    return await svc.get_detail(comision_id)
