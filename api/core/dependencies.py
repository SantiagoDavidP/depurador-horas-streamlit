"""FastAPI dependency injection: DB session, current user, service factories."""

import uuid
from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.security import decode_token
from api.db.base import async_session_maker
from api.db.models.user import UserModel

# ---------------------------------------------------------------------------
# DB session
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session with automatic rollback on error."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

SessionDep = Annotated[AsyncSession, Depends(get_db)]

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security_scheme)
    ],
    db: SessionDep,
) -> UserModel:
    """Decode JWT and return the authenticated UserModel."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autorizacion requerido",
        )
    try:
        payload = decode_token(credentials.credentials)
        user_id_str: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id_str is None or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalido",
            )
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado",
        )

    user = await db.get(UserModel, user_id)
    if user is None or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )
    return user


CurrentUser = Annotated[UserModel, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Optional auth (for endpoints that work with or without token)
# ---------------------------------------------------------------------------

async def get_current_user_optional(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security_scheme)
    ],
    db: SessionDep,
) -> UserModel | None:
    """Return user if token present and valid, else None."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Role-based access
# ---------------------------------------------------------------------------

def require_roles(*allowed_roles: str):
    """Return a dependency that checks the user's role against an allow-list."""

    async def _check(user: CurrentUser) -> UserModel:
        if user.rol not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol '{user.rol}' no tiene acceso a este recurso",
            )
        return user

    return _check


# Convenient typed aliases
AdminOrFinanzas = Annotated[
    UserModel,
    Depends(require_roles("AdminComercial", "Finanzas", "GerenteGeneral")),
]
OnlyFinanzas = Annotated[
    UserModel,
    Depends(require_roles("Finanzas", "GerenteGeneral")),
]
OnlyAdmin = Annotated[
    UserModel,
    Depends(require_roles("AdminComercial", "GerenteGeneral")),
]
