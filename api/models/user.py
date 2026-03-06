"""Pydantic schemas for User, authentication, and tokens."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    """Credentials for local login."""
    email: EmailStr
    password: str = Field(..., min_length=6)


class MicrosoftLoginRequest(BaseModel):
    """Payload from Microsoft Entra ID SSO callback."""
    id_token: str


class TokenResponse(BaseModel):
    """JWT token pair returned after successful authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Payload for token refresh."""
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Request payload for forgotten password."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request payload for password reset."""
    token: str
    new_password: str = Field(..., min_length=8)


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    """Shared fields for User."""
    nombre_completo: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    rol: str = Field(
        ...,
        pattern=r"^(Vendedor|AdminComercial|Finanzas|GerenteGeneral)$",
        examples=["Vendedor"],
    )


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: Optional[str] = Field(None, min_length=8)
    entra_id: Optional[str] = None


class UserUpdate(BaseModel):
    """Partial update for user."""
    nombre_completo: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    rol: Optional[str] = Field(
        None,
        pattern=r"^(Vendedor|AdminComercial|Finanzas|GerenteGeneral)$",
    )
    activo: Optional[bool] = None


class UserResponse(UserBase):
    """User response schema returned to clients."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activo: bool
    entra_id: Optional[str] = None
    ultimo_acceso: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class UserMeResponse(BaseModel):
    """Minimal user info for /auth/me."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre_completo: str
    email: str
    rol: str
    activo: bool


# ---------------------------------------------------------------------------
# Roles & permissions
# ---------------------------------------------------------------------------

class RoleResponse(BaseModel):
    """Role descriptor."""
    id: str
    nombre: str
    descripcion: str


class PermissionResponse(BaseModel):
    """Permission for a role."""
    modulo: str
    puede_leer: bool
    puede_escribir: bool
    puede_aprobar: bool
