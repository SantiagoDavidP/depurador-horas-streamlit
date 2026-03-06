# tests/backend/test_devoluciones.py
"""Tests for devoluciones endpoints."""
import pytest
from httpx import AsyncClient
from datetime import date
from api.db.models.devolucion import DevolucionModel as Devolucion
from api.db.models.pedido import PedidoModel as Pedido
from api.db.models.producto import ProductoModel as Producto


@pytest.mark.asyncio
async def test_list_devoluciones(
    client: AsyncClient,
    test_devolucion: Devolucion,
    auth_headers_vendedor: dict
) -> None:
    """Test listing devoluciones."""
    response = await client.get(
        "/api/returns/",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_devolucion_by_id(
    client: AsyncClient,
    test_devolucion: Devolucion,
    auth_headers_vendedor: dict
) -> None:
    """Test getting devolucion by ID."""
    response = await client.get(
        f"/api/returns/{test_devolucion.id}",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_devolucion.id)


@pytest.mark.asyncio
async def test_create_devolucion(
    client: AsyncClient,
    test_pedido_aprobado: Pedido,
    test_productos: list,
    auth_headers_vendedor: dict
) -> None:
    """Test creating a devolucion."""
    payload = {
        "pedido_id": str(test_pedido_aprobado.id),
        "numero_factura": "F001-00012345",
        "producto_id": str(test_productos[0].id),
        "cantidad": 5,
        "lote": "LOTE001",
        "razon": "Producto daniado",
    }

    response = await client.post(
        "/api/returns/",
        json=payload,
        headers=auth_headers_vendedor
    )
    assert response.status_code == 201
    data = response.json()
    assert data["estado"] == "En Proceso"
    assert "codigo_devolucion" in data


@pytest.mark.asyncio
async def test_create_devolucion_has_valorizado(
    client: AsyncClient,
    test_pedido_aprobado: Pedido,
    test_productos: list,
    auth_headers_vendedor: dict
) -> None:
    """Test devolucion valorizado is calculated."""
    payload = {
        "pedido_id": str(test_pedido_aprobado.id),
        "numero_factura": "F001-00098765",
        "producto_id": str(test_productos[0].id),
        "cantidad": 10,
        "lote": "LOTE002",
        "razon": "Producto vencido",
    }

    response = await client.post(
        "/api/returns/",
        json=payload,
        headers=auth_headers_vendedor
    )
    assert response.status_code == 201
    data = response.json()
    # valorizado should be calculated: 10 * 10.50 = 105.00
    assert data["valorizado"] == 105.00


@pytest.mark.asyncio
async def test_approve_devolucion(
    client: AsyncClient,
    test_devolucion: Devolucion,
    auth_headers_admin: dict
) -> None:
    """Test approving a devolucion."""
    response = await client.post(
        f"/api/returns/{test_devolucion.id}/approve",
        json={"comentarios": "Aprobada por test"},
        headers=auth_headers_admin
    )
    assert response.status_code == 200
    data = response.json()
    assert data["estado"] == "Aprobada"


@pytest.mark.asyncio
async def test_reject_devolucion(
    client: AsyncClient,
    test_devolucion: Devolucion,
    auth_headers_admin: dict
) -> None:
    """Test rejecting a devolucion."""
    response = await client.post(
        f"/api/returns/{test_devolucion.id}/reject",
        json={"motivo_rechazo": "No cumple condiciones"},
        headers=auth_headers_admin
    )
    assert response.status_code == 200
    data = response.json()
    assert data["estado"] == "Rechazada"


@pytest.mark.asyncio
async def test_filter_devoluciones_by_estado(
    client: AsyncClient,
    test_devolucion: Devolucion,
    auth_headers_vendedor: dict
) -> None:
    """Test filtering devoluciones by estado."""
    response = await client.get(
        "/api/returns/?estado=En Proceso",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert all(item["estado"] == "En Proceso" for item in data["items"])


@pytest.mark.asyncio
async def test_get_nonexistent_devolucion(
    client: AsyncClient,
    auth_headers_vendedor: dict
) -> None:
    """Test getting non-existent devolucion."""
    import uuid
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"/api/returns/{fake_id}",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_devolucion_validation_error(
    client: AsyncClient,
    auth_headers_vendedor: dict
) -> None:
    """Test devolucion creation with invalid data."""
    payload = {
        "pedido_id": "not-a-uuid",
        "numero_factura": "invalid-format",
        "producto_id": "not-a-uuid",
        "cantidad": -1,
        "razon": "",
    }

    response = await client.post(
        "/api/returns/",
        json=payload,
        headers=auth_headers_vendedor
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_devoluciones_requires_authentication(client: AsyncClient) -> None:
    """Test that listing devoluciones requires auth."""
    response = await client.get("/api/returns/")
    assert response.status_code == 401
