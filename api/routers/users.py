"""Users and Roles management router.

GET    /api/users
GET    /api/users/{id}
POST   /api/users
PUT    /api/users/{id}
DELETE /api/users/{id}
GET    /api/roles
GET    /api/roles/{id}/permissions
"""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from api.core.dependencies import CurrentUser, OnlyAdmin, SessionDep
from api.core.security import hash_password
from api.db.models.user import UserModel
from api.models.common import PaginatedResponse
from api.models.user import (
    PermissionResponse,
    RoleResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from api.repositories.user_repository import UserRepository

router = APIRouter(prefix="/api/users", tags=["users"])

ROLES_DATA = [
    RoleResponse(id="Vendedor", nombre="Vendedor", descripcion="Registra pedidos y consulta estado"),
    RoleResponse(id="AdminComercial", nombre="Admin Comercial", descripcion="Aprueba pedidos y gestiona devoluciones"),
    RoleResponse(id="Finanzas", nombre="Finanzas", descripcion="Calcula y aprueba comisiones"),
    RoleResponse(id="GerenteGeneral", nombre="Gerente General", descripcion="Acceso completo a reportes y supervision"),
]

PERMISSIONS_MAP: dict[str, list[PermissionResponse]] = {
    "Vendedor": [
        PermissionResponse(modulo="pedidos", puede_leer=True, puede_escribir=True, puede_aprobar=False),
        PermissionResponse(modulo="devoluciones", puede_leer=True, puede_escribir=False, puede_aprobar=False),
        PermissionResponse(modulo="comisiones", puede_leer=False, puede_escribir=False, puede_aprobar=False),
        PermissionResponse(modulo="reportes", puede_leer=True, puede_escribir=False, puede_aprobar=False),
    ],
    "AdminComercial": [
        PermissionResponse(modulo="pedidos", puede_leer=True, puede_escribir=True, puede_aprobar=True),
        PermissionResponse(modulo="devoluciones", puede_leer=True, puede_escribir=True, puede_aprobar=True),
        PermissionResponse(modulo="comisiones", puede_leer=True, puede_escribir=False, puede_aprobar=False),
        PermissionResponse(modulo="reportes", puede_leer=True, puede_escribir=False, puede_aprobar=False),
    ],
    "Finanzas": [
        PermissionResponse(modulo="pedidos", puede_leer=True, puede_escribir=False, puede_aprobar=False),
        PermissionResponse(modulo="devoluciones", puede_leer=True, puede_escribir=False, puede_aprobar=False),
        PermissionResponse(modulo="comisiones", puede_leer=True, puede_escribir=True, puede_aprobar=True),
        PermissionResponse(modulo="reportes", puede_leer=True, puede_escribir=False, puede_aprobar=False),
    ],
    "GerenteGeneral": [
        PermissionResponse(modulo="pedidos", puede_leer=True, puede_escribir=True, puede_aprobar=True),
        PermissionResponse(modulo="devoluciones", puede_leer=True, puede_escribir=True, puede_aprobar=True),
        PermissionResponse(modulo="comisiones", puede_leer=True, puede_escribir=True, puede_aprobar=True),
        PermissionResponse(modulo="reportes", puede_leer=True, puede_escribir=True, puede_aprobar=True),
    ],
}


def _get_repo(db: SessionDep) -> UserRepository:
    return UserRepository(db)


# ------------------------------------------------------------------
@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    rol: Optional[str] = None,
    activo: Optional[bool] = None,
    search: Optional[str] = None,
    repo: UserRepository = Depends(_get_repo),
) -> PaginatedResponse[UserResponse]:
    """List users with pagination and filters."""
    items = await repo.get_multi(skip=skip, limit=limit, rol=rol, activo=activo, search=search)
    total = await repo.count(rol=rol, activo=activo, search=search)
    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
        skip=skip,
        limit=limit,
    )


# ------------------------------------------------------------------
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    repo: UserRepository = Depends(_get_repo),
) -> UserResponse:
    """Get user by ID."""
    target = await repo.get(user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return UserResponse.model_validate(target)


# ------------------------------------------------------------------
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    admin: OnlyAdmin,
    repo: UserRepository = Depends(_get_repo),
) -> UserResponse:
    """Create a new user (admin only)."""
    existing = await repo.get_by_email(data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ya registrado")

    user_model = UserModel(
        nombre_completo=data.nombre_completo,
        email=data.email,
        rol=data.rol,
        password_hash=hash_password(data.password) if data.password else None,
        entra_id=data.entra_id,
    )
    user_model = await repo.create(user_model)
    return UserResponse.model_validate(user_model)


# ------------------------------------------------------------------
@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: Annotated[uuid.UUID, Path()],
    data: UserUpdate,
    user: CurrentUser,
    repo: UserRepository = Depends(_get_repo),
) -> UserResponse:
    """Update user information."""
    target = await repo.get(user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return UserResponse.model_validate(target)
    target = await repo.update(target, update_data)
    return UserResponse.model_validate(target)


# ------------------------------------------------------------------
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: Annotated[uuid.UUID, Path()],
    admin: OnlyAdmin,
    repo: UserRepository = Depends(_get_repo),
) -> None:
    """Soft-delete (deactivate) a user."""
    target = await repo.get(user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    await repo.soft_delete(target)


# ------------------------------------------------------------------
# Roles endpoints (mounted at /api prefix via main.py)
# ------------------------------------------------------------------
roles_router = APIRouter(prefix="/api/roles", tags=["roles"])


@roles_router.get("/", response_model=list[RoleResponse])
async def list_roles(user: CurrentUser) -> list[RoleResponse]:
    """List available roles."""
    return ROLES_DATA


@roles_router.get("/{role_id}/permissions", response_model=list[PermissionResponse])
async def get_role_permissions(
    role_id: str,
    user: CurrentUser,
) -> list[PermissionResponse]:
    """Get permissions for a role."""
    perms = PERMISSIONS_MAP.get(role_id)
    if perms is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    return perms
