# tests/backend/test_auth.py
"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from api.db.models.user import UserModel as User


@pytest.mark.asyncio
async def test_login_with_valid_credentials(
    client: AsyncClient,
    test_vendedor: User
) -> None:
    """Test login with correct email and password."""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "vendedor@test.com",
            "password": "password123",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_with_invalid_email(client: AsyncClient) -> None:
    """Test login with non-existent email."""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@test.com",
            "password": "password123",
        }
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_login_with_invalid_password(
    client: AsyncClient,
    test_vendedor: User
) -> None:
    """Test login with incorrect password."""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "vendedor@test.com",
            "password": "wrongpassword",
        }
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_login_with_inactive_user(
    client: AsyncClient,
    db_session: AsyncSession,
    test_vendedor: User
) -> None:
    """Test login with deactivated user."""
    test_vendedor.activo = False
    db_session.add(test_vendedor)
    await db_session.commit()

    response = await client.post(
        "/api/auth/login",
        json={
            "email": "vendedor@test.com",
            "password": "password123",
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(
    client: AsyncClient,
    test_vendedor: User,
    auth_headers_vendedor: dict
) -> None:
    """Test getting current authenticated user."""
    response = await client.get(
        "/api/auth/me",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nombre_completo"] == "Test Vendedor"
    assert data["email"] == "vendedor@test.com"
    assert data["rol"] == "Vendedor"


@pytest.mark.asyncio
async def test_get_current_user_without_token(client: AsyncClient) -> None:
    """Test accessing protected endpoint without authentication."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_with_invalid_token(client: AsyncClient) -> None:
    """Test accessing protected endpoint with invalid token."""
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(
    client: AsyncClient,
    auth_headers_vendedor: dict
) -> None:
    """Test logout endpoint."""
    response = await client.post(
        "/api/auth/logout",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_refresh_token(
    client: AsyncClient,
    test_vendedor: User,
) -> None:
    """Test token refresh endpoint."""
    from api.core.security import create_refresh_token
    refresh = create_refresh_token(data={"sub": str(test_vendedor.id)})
    response = await client.post(
        "/api/auth/refresh-token",
        json={"refresh_token": refresh}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data


@pytest.mark.asyncio
async def test_login_returns_user_tokens(
    client: AsyncClient,
    test_admin: User
) -> None:
    """Test that login returns proper token response."""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "admin@test.com",
            "password": "admin123",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


@pytest.mark.asyncio
async def test_login_validation_error_missing_fields(client: AsyncClient) -> None:
    """Test login with missing required fields."""
    response = await client.post(
        "/api/auth/login",
        json={}
    )
    assert response.status_code == 422
