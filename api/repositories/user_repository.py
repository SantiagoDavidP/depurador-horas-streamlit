"""Repository for User data access. Only SQL, no business logic."""

import uuid
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models.user import UserModel


class UserRepository:
    """Data-access layer for Users."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID) -> Optional[UserModel]:
        """Get a user by primary key."""
        return await self.session.get(UserModel, user_id)

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        """Get a user by email address."""
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_entra_id(self, entra_id: str) -> Optional[UserModel]:
        """Get a user by Microsoft Entra ID."""
        stmt = select(UserModel).where(UserModel.entra_id == entra_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 20,
        rol: Optional[str] = None,
        activo: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Sequence[UserModel]:
        """List users with optional filters."""
        stmt = select(UserModel).order_by(UserModel.created_at.desc())
        if rol:
            stmt = stmt.where(UserModel.rol == rol)
        if activo is not None:
            stmt = stmt.where(UserModel.activo == activo)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                UserModel.nombre_completo.ilike(pattern)
                | UserModel.email.ilike(pattern)
            )
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(
        self,
        rol: Optional[str] = None,
        activo: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> int:
        """Count users with optional filters."""
        stmt = select(func.count()).select_from(UserModel)
        if rol:
            stmt = stmt.where(UserModel.rol == rol)
        if activo is not None:
            stmt = stmt.where(UserModel.activo == activo)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                UserModel.nombre_completo.ilike(pattern)
                | UserModel.email.ilike(pattern)
            )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, user: UserModel) -> UserModel:
        """Persist a new user."""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, user: UserModel, data: dict) -> UserModel:
        """Update fields on an existing user."""
        for key, value in data.items():
            setattr(user, key, value)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def soft_delete(self, user: UserModel) -> UserModel:
        """Deactivate a user (soft delete)."""
        user.activo = False
        await self.session.commit()
        await self.session.refresh(user)
        return user
