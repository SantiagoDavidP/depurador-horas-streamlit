"""Authentication router -- 7 endpoints.

POST /api/auth/login
POST /api/auth/login/microsoft
POST /api/auth/logout
POST /api/auth/forgot-password
POST /api/auth/reset-password
GET  /api/auth/me
POST /api/auth/refresh-token
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.dependencies import CurrentUser, SessionDep, get_current_user
from api.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    verify_password_reset_token,
)
from api.models.common import MessageResponse, PaginatedResponse
from api.models.user import (
    ForgotPasswordRequest,
    LoginRequest,
    MicrosoftLoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    RoleResponse,
    PermissionResponse,
    TokenResponse,
    UserCreate,
    UserMeResponse,
    UserResponse,
    UserUpdate,
)
from api.repositories.user_repository import UserRepository

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_user_repo(db: SessionDep) -> UserRepository:
    return UserRepository(db)


# ------------------------------------------------------------------
# POST /api/auth/login
# ------------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    repo: UserRepository = Depends(_get_user_repo),
) -> TokenResponse:
    """Authenticate with email/password and return JWT tokens."""
    user = await repo.get_by_email(data.email)
    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")
    if not user.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")

    # Update last access
    user.ultimo_acceso = datetime.now(timezone.utc)
    await repo.update(user, {"ultimo_acceso": user.ultimo_acceso})

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ------------------------------------------------------------------
# POST /api/auth/login/microsoft
# ------------------------------------------------------------------
@router.post("/login/microsoft", response_model=TokenResponse)
async def login_microsoft(
    data: MicrosoftLoginRequest,
    repo: UserRepository = Depends(_get_user_repo),
) -> TokenResponse:
    """SSO login with Microsoft Entra ID token.

    In production this would validate the id_token against Azure AD.
    For now it accepts any valid Entra ID and creates tokens.
    """
    # TODO: validate id_token with Microsoft Entra ID in production
    # For development, we accept a stub
    user = await repo.get_by_entra_id(data.id_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario de Entra ID no registrado",
        )
    if not user.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")

    user.ultimo_acceso = datetime.now(timezone.utc)
    await repo.update(user, {"ultimo_acceso": user.ultimo_acceso})

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ------------------------------------------------------------------
# POST /api/auth/logout
# ------------------------------------------------------------------
@router.post("/logout", response_model=MessageResponse)
async def logout(user: CurrentUser) -> MessageResponse:
    """Invalidate session (client must discard tokens)."""
    return MessageResponse(message="Sesion cerrada exitosamente")


# ------------------------------------------------------------------
# POST /api/auth/forgot-password
# ------------------------------------------------------------------
@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    repo: UserRepository = Depends(_get_user_repo),
) -> MessageResponse:
    """Send a password-reset email with a temporary token."""
    user = await repo.get_by_email(data.email)
    if user and user.activo:
        token = create_password_reset_token(data.email)
        # In production: send email with token link
        import logging
        logging.getLogger("bonapharm").info(
            "Password reset token for %s: %s", data.email, token
        )
    # Always return success to prevent email enumeration
    return MessageResponse(
        message="Si el correo existe, recibira instrucciones para restablecer su contrasena"
    )


# ------------------------------------------------------------------
# POST /api/auth/reset-password
# ------------------------------------------------------------------
@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    data: ResetPasswordRequest,
    repo: UserRepository = Depends(_get_user_repo),
) -> MessageResponse:
    """Reset password using a temporary token."""
    email = verify_password_reset_token(data.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token invalido o expirado",
        )
    user = await repo.get_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    hashed = hash_password(data.new_password)
    await repo.update(user, {"password_hash": hashed})
    return MessageResponse(message="Contrasena actualizada exitosamente")


# ------------------------------------------------------------------
# GET /api/auth/me
# ------------------------------------------------------------------
@router.get("/me", response_model=UserMeResponse)
async def me(user: CurrentUser) -> UserMeResponse:
    """Get current authenticated user info."""
    return UserMeResponse.model_validate(user)


# ------------------------------------------------------------------
# POST /api/auth/refresh-token
# ------------------------------------------------------------------
@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    repo: UserRepository = Depends(_get_user_repo),
) -> TokenResponse:
    """Renew JWT access token using a valid refresh token."""
    from jose import JWTError
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido o expirado")

    user = await repo.get(uuid.UUID(user_id))
    if not user or not user.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh = create_refresh_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
