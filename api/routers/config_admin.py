"""Administration configuration router.

GET    /api/config/distributors              List distributor configs
PUT    /api/config/distributors/{id}         Update distributor config
GET    /api/config/payment-terms             List payment terms
POST   /api/config/payment-terms             Create payment term
GET    /api/config/return-reasons            List return reasons
POST   /api/config/return-reasons            Add return reason
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.dependencies import CurrentUser, OnlyAdmin, SessionDep
from api.db.models.config import (
    CondicionPagoModel,
    DistribuidorConfigModel,
    RazonDevolucionModel,
)
from api.models.config_schema import (
    CondicionPagoCreate,
    CondicionPagoResponse,
    DistribuidorConfigResponse,
    DistribuidorConfigUpdate,
    RazonDevolucionCreate,
)
from api.models.devolucion import RazonDevolucionResponse

router = APIRouter(prefix="/api/config", tags=["configuracion"])


# ------------------------------------------------------------------
# Distributors
# ------------------------------------------------------------------
@router.get("/distributors", response_model=list[DistribuidorConfigResponse])
async def list_distributors(
    db: SessionDep,
    user: CurrentUser,
) -> list[DistribuidorConfigResponse]:
    """List configured distributors with commission percentages and minimums."""
    stmt = select(DistribuidorConfigModel).order_by(DistribuidorConfigModel.nombre)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [DistribuidorConfigResponse.model_validate(r) for r in rows]


@router.put("/distributors/{dist_id}", response_model=DistribuidorConfigResponse)
async def update_distributor(
    dist_id: Annotated[uuid.UUID, Path()],
    data: DistribuidorConfigUpdate,
    db: SessionDep,
    admin: OnlyAdmin,
) -> DistribuidorConfigResponse:
    """Update distributor configuration (minimum order, commission %)."""
    dist = await db.get(DistribuidorConfigModel, dist_id)
    if not dist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distribuidor no encontrado",
        )
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dist, key, value)
    await db.commit()
    await db.refresh(dist)
    return DistribuidorConfigResponse.model_validate(dist)


# ------------------------------------------------------------------
# Payment terms
# ------------------------------------------------------------------
@router.get("/payment-terms", response_model=list[CondicionPagoResponse])
async def list_payment_terms(
    db: SessionDep,
    user: CurrentUser,
) -> list[CondicionPagoResponse]:
    """List available payment terms."""
    stmt = select(CondicionPagoModel).where(CondicionPagoModel.activo == True).order_by(CondicionPagoModel.nombre)  # noqa: E712
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [CondicionPagoResponse.model_validate(r) for r in rows]


@router.post(
    "/payment-terms",
    response_model=CondicionPagoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment_term(
    data: CondicionPagoCreate,
    db: SessionDep,
    admin: OnlyAdmin,
) -> CondicionPagoResponse:
    """Create a new payment term."""
    model = CondicionPagoModel(nombre=data.nombre, dias_credito=data.dias_credito)
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return CondicionPagoResponse.model_validate(model)


# ------------------------------------------------------------------
# Return reasons
# ------------------------------------------------------------------
@router.get("/return-reasons", response_model=list[RazonDevolucionResponse])
async def list_return_reasons(
    db: SessionDep,
    user: CurrentUser,
) -> list[RazonDevolucionResponse]:
    """List return reasons."""
    stmt = select(RazonDevolucionModel).where(RazonDevolucionModel.activo == True).order_by(RazonDevolucionModel.nombre)  # noqa: E712
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [RazonDevolucionResponse.model_validate(r) for r in rows]


@router.post(
    "/return-reasons",
    response_model=RazonDevolucionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_return_reason(
    data: RazonDevolucionCreate,
    db: SessionDep,
    admin: OnlyAdmin,
) -> RazonDevolucionResponse:
    """Add a new return reason."""
    model = RazonDevolucionModel(nombre=data.nombre)
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return RazonDevolucionResponse.model_validate(model)
