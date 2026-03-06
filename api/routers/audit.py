"""Audit log router.

GET /api/audit/logs              List audit logs
GET /api/audit/logs/{entityId}   History of a specific entity
"""

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.dependencies import AdminOrFinanzas, SessionDep
from api.db.models.audit_log import AuditLogModel
from api.models.audit import AuditLogResponse
from api.models.common import PaginatedResponse

router = APIRouter(prefix="/api/audit", tags=["auditoria"])


# ------------------------------------------------------------------
# GET /api/audit/logs
# ------------------------------------------------------------------
@router.get("/logs", response_model=PaginatedResponse[AuditLogResponse])
async def list_logs(
    user: AdminOrFinanzas,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: Optional[uuid.UUID] = None,
    accion: Optional[str] = None,
    entidad: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    db: SessionDep = None,
) -> PaginatedResponse[AuditLogResponse]:
    """List audit logs with filters."""
    from sqlalchemy import func

    stmt = select(AuditLogModel).order_by(AuditLogModel.created_at.desc())
    count_stmt = select(func.count()).select_from(AuditLogModel)

    if user_id:
        stmt = stmt.where(AuditLogModel.user_id == user_id)
        count_stmt = count_stmt.where(AuditLogModel.user_id == user_id)
    if accion:
        stmt = stmt.where(AuditLogModel.accion == accion)
        count_stmt = count_stmt.where(AuditLogModel.accion == accion)
    if entidad:
        stmt = stmt.where(AuditLogModel.entidad == entidad)
        count_stmt = count_stmt.where(AuditLogModel.entidad == entidad)
    if fecha_desde:
        stmt = stmt.where(AuditLogModel.created_at >= fecha_desde)
        count_stmt = count_stmt.where(AuditLogModel.created_at >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(AuditLogModel.created_at <= fecha_hasta)
        count_stmt = count_stmt.where(AuditLogModel.created_at <= fecha_hasta)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    total_result = await db.execute(count_stmt)
    items = result.scalars().all()
    total = total_result.scalar_one()

    return PaginatedResponse(
        items=[AuditLogResponse.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


# ------------------------------------------------------------------
# GET /api/audit/logs/{entityId}
# ------------------------------------------------------------------
@router.get("/logs/{entity_id}", response_model=list[AuditLogResponse])
async def entity_history(
    entity_id: Annotated[uuid.UUID, Path()],
    db: SessionDep,
    user: AdminOrFinanzas,
) -> list[AuditLogResponse]:
    """Get change history for a specific entity."""
    stmt = (
        select(AuditLogModel)
        .where(AuditLogModel.entidad_id == entity_id)
        .order_by(AuditLogModel.created_at.desc())
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [AuditLogResponse.model_validate(i) for i in items]
