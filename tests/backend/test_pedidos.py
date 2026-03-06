# tests/backend/test_pedidos.py
"""Tests for pedidos endpoints."""
import pytest
from httpx import AsyncClient
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from api.db.models.user import UserModel as User
from api.db.models.pedido import PedidoModel as Pedido
from api.db.models.producto import ProductoModel as Producto


@pytest.mark.asyncio
async def test_list_pedidos(
    client: AsyncClient,
    test_pedido: Pedido,
    auth_headers_vendedor: dict
) -> None:
    """Test listing pedidos."""
    response = await client.get(
        "/api/orders/",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["codigo_pedido"] == "PED-2026-TEST-0001"


@pytest.mark.asyncio
async def test_list_pedidos_filter_by_estado(
    client: AsyncClient,
    test_pedido: Pedido,
    test_pedido_aprobado: Pedido,
    auth_headers_vendedor: dict
) -> None:
    """Test filtering pedidos by estado."""
    response = await client.get(
        "/api/orders/?estado=Borrador",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert all(item["estado"] == "Borrador" for item in data["items"])


@pytest.mark.asyncio
async def test_get_pedido_by_id(
    client: AsyncClient,
    test_pedido: Pedido,
    auth_headers_vendedor: dict
) -> None:
    """Test getting a specific pedido by ID."""
    response = await client.get(
        f"/api/orders/{test_pedido.id}",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_pedido.id)
    assert data["codigo_pedido"] == test_pedido.codigo_pedido
    assert "detalles" in data


@pytest.mark.asyncio
async def test_get_nonexistent_pedido(
    client: AsyncClient,
    auth_headers_vendedor: dict
) -> None:
    """Test getting a non-existent pedido."""
    import uuid
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"/api/orders/{fake_id}",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_pedido(
    client: AsyncClient,
    test_vendedor: User,
    test_productos: list,
    auth_headers_vendedor: dict
) -> None:
    """Test creating a new pedido."""
    payload = {
        "cliente_ruc": "20111222333",
        "cliente_razon_social": "FARMACIA NUEVA SAC",
        "condicion_pago": "Contado",
        "estado": "Borrador",
        "detalles": [
            {
                "producto_id": str(test_productos[0].id),
                "cantidad": 20,
            }
        ]
    }

    response = await client.post(
        "/api/orders/",
        json=payload,
        headers=auth_headers_vendedor
    )
    assert response.status_code == 201
    data = response.json()
    assert data["cliente_razon_social"] == "FARMACIA NUEVA SAC"
    assert data["estado"] == "Borrador"
    assert "codigo_pedido" in data


@pytest.mark.asyncio
async def test_create_pedido_calculates_totals_correctly(
    client: AsyncClient,
    test_vendedor: User,
    test_productos: list,
    auth_headers_vendedor: dict
) -> None:
    """Test that pedido creation calculates IGV and total correctly."""
    payload = {
        "cliente_ruc": "20111222333",
        "cliente_razon_social": "FARMACIA NUEVA SAC",
        "condicion_pago": "Contado",
        "estado": "Borrador",
        "detalles": [
            {
                "producto_id": str(test_productos[0].id),
                "cantidad": 100,
            }
        ]
    }

    response = await client.post(
        "/api/orders/",
        json=payload,
        headers=auth_headers_vendedor
    )
    assert response.status_code == 201
    data = response.json()

    # subtotal = 100 * 10.50 = 1050
    # igv = 1050 * 0.18 = 189
    # total = 1050 + 189 = 1239
    assert data["subtotal"] == 1050.00
    assert data["igv"] == 189.00
    assert data["total"] == 1239.00


@pytest.mark.asyncio
async def test_create_pedido_validation_error(
    client: AsyncClient,
    auth_headers_vendedor: dict
) -> None:
    """Test creating pedido with invalid data."""
    payload = {
        "cliente_ruc": "",  # Invalid: not 11 digits
        "cliente_razon_social": "",
        "condicion_pago": "invalid_type",
    }

    response = await client.post(
        "/api/orders/",
        json=payload,
        headers=auth_headers_vendedor
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_pedido(
    client: AsyncClient,
    test_pedido: Pedido,
    auth_headers_vendedor: dict
) -> None:
    """Test updating a pedido."""
    # First change estado to Enviado so update_sent works
    # Actually, the update endpoint requires estado=Enviado
    # Let's update the pedido to Enviado first via DB or test the draft update
    payload = {
        "cliente_razon_social": "FARMACIA UPDATED SAC",
    }

    # Use the draft update endpoint instead
    response = await client.put(
        f"/api/orders/{test_pedido.id}/draft",
        json=payload,
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cliente_razon_social"] == "FARMACIA UPDATED SAC"


@pytest.mark.asyncio
async def test_approve_pedido(
    client: AsyncClient,
    test_pedido: Pedido,
    db_session: AsyncSession,
    auth_headers_admin: dict
) -> None:
    """Test approving a pedido."""
    # Set pedido to Enviado first (approve requires Enviado estado)
    test_pedido.estado = "Enviado"
    db_session.add(test_pedido)
    await db_session.commit()

    response = await client.post(
        f"/api/orders/{test_pedido.id}/approve",
        json={"comentarios": "Aprobado por test"},
        headers=auth_headers_admin
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["new_status"] == "Aprobado"


@pytest.mark.asyncio
async def test_approve_pedido_requires_admin(
    client: AsyncClient,
    test_pedido: Pedido,
    db_session: AsyncSession,
    auth_headers_vendedor: dict
) -> None:
    """Test that only admin can approve pedidos."""
    test_pedido.estado = "Enviado"
    db_session.add(test_pedido)
    await db_session.commit()

    response = await client.post(
        f"/api/orders/{test_pedido.id}/approve",
        json={},
        headers=auth_headers_vendedor
    )
    # Should return 403 Forbidden
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_reject_pedido(
    client: AsyncClient,
    test_pedido: Pedido,
    db_session: AsyncSession,
    auth_headers_admin: dict
) -> None:
    """Test rejecting a pedido."""
    # Set pedido to Enviado first
    test_pedido.estado = "Enviado"
    db_session.add(test_pedido)
    await db_session.commit()

    payload = {
        "motivo_rechazo": "Stock insuficiente"
    }

    response = await client.post(
        f"/api/orders/{test_pedido.id}/reject",
        json=payload,
        headers=auth_headers_admin
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new_status"] == "Rechazado"


@pytest.mark.asyncio
async def test_reject_pedido_requires_motivo(
    client: AsyncClient,
    test_pedido: Pedido,
    db_session: AsyncSession,
    auth_headers_admin: dict
) -> None:
    """Test that rejecting requires a motivo."""
    test_pedido.estado = "Enviado"
    db_session.add(test_pedido)
    await db_session.commit()

    response = await client.post(
        f"/api/orders/{test_pedido.id}/reject",
        json={},
        headers=auth_headers_admin
    )
    # Should require motivo_rechazo field
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_pedidos_pagination(
    client: AsyncClient,
    test_pedido: Pedido,
    test_pedido_aprobado: Pedido,
    auth_headers_vendedor: dict
) -> None:
    """Test pedidos pagination."""
    response = await client.get(
        "/api/orders/?skip=0&limit=1",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert len(data["items"]) <= 1


@pytest.mark.asyncio
async def test_list_pedidos_requires_authentication(client: AsyncClient) -> None:
    """Test that listing pedidos requires authentication."""
    response = await client.get("/api/orders/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_pedido_generates_code(
    client: AsyncClient,
    test_vendedor: User,
    test_productos: list,
    auth_headers_vendedor: dict
) -> None:
    """Test that pedido creation generates a code."""
    payload = {
        "cliente_ruc": "20111222333",
        "cliente_razon_social": "FARMACIA TEST",
        "condicion_pago": "Contado",
        "estado": "Borrador",
        "detalles": [
            {
                "producto_id": str(test_productos[0].id),
                "cantidad": 10,
            }
        ]
    }

    response = await client.post(
        "/api/orders/",
        json=payload,
        headers=auth_headers_vendedor
    )
    assert response.status_code == 201
    data = response.json()
    assert data["codigo_pedido"].startswith("PED-")
