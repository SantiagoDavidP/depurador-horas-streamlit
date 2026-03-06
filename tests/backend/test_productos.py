# tests/backend/test_productos.py
"""Tests for productos endpoints."""
import pytest
from httpx import AsyncClient
from decimal import Decimal
from api.db.models.producto import ProductoModel as Producto


@pytest.mark.asyncio
async def test_list_productos(
    client: AsyncClient,
    test_productos: list,
    auth_headers_vendedor: dict
) -> None:
    """Test listing productos."""
    response = await client.get(
        "/api/products/",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 3


@pytest.mark.asyncio
async def test_search_productos_by_name(
    client: AsyncClient,
    test_productos: list,
    auth_headers_vendedor: dict
) -> None:
    """Test searching productos by name."""
    response = await client.get(
        "/api/products/?search=PARACETAMOL",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert any("PARACETAMOL" in item["nombre"] for item in data["items"])


@pytest.mark.asyncio
async def test_search_productos_by_codigo_sap(
    client: AsyncClient,
    test_productos: list,
    auth_headers_vendedor: dict
) -> None:
    """Test searching productos by SAP code."""
    response = await client.get(
        "/api/products/?search=SAP001",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert any(item["codigo_sap"] == "SAP001" for item in data["items"])


@pytest.mark.asyncio
async def test_filter_productos_by_distribuidor(
    client: AsyncClient,
    test_productos: list,
    auth_headers_vendedor: dict
) -> None:
    """Test filtering productos by distribuidor."""
    response = await client.get(
        "/api/products/?distribuidor=Dimexa",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert all(item["distribuidor"] == "Dimexa" for item in data["items"])


@pytest.mark.asyncio
async def test_get_producto_by_id(
    client: AsyncClient,
    test_productos: list,
    auth_headers_vendedor: dict
) -> None:
    """Test getting producto by ID."""
    producto = test_productos[0]
    response = await client.get(
        f"/api/products/{producto.id}",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(producto.id)
    assert data["codigo_sap"] == producto.codigo_sap


@pytest.mark.asyncio
async def test_get_nonexistent_producto(
    client: AsyncClient,
    auth_headers_vendedor: dict
) -> None:
    """Test getting non-existent producto."""
    import uuid
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"/api/products/{fake_id}",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_producto(
    client: AsyncClient,
    auth_headers_admin: dict
) -> None:
    """Test creating a new producto."""
    payload = {
        "codigo_sap": "SAP999",
        "nombre": "NUEVO PRODUCTO",
        "distribuidor": "Dimexa",
        "precio_vvf": 25.50,
        "precio_compra": 18.00,
        "stock_disponible": 100,
    }

    response = await client.post(
        "/api/products/",
        json=payload,
        headers=auth_headers_admin
    )
    assert response.status_code == 201
    data = response.json()
    assert data["codigo_sap"] == "SAP999"
    assert data["nombre"] == "NUEVO PRODUCTO"


@pytest.mark.asyncio
async def test_update_producto(
    client: AsyncClient,
    test_productos: list,
    auth_headers_admin: dict
) -> None:
    """Test updating a producto."""
    producto = test_productos[0]
    payload = {
        "precio_vvf": 12.00,
        "stock_disponible": 600,
    }

    response = await client.put(
        f"/api/products/{producto.id}",
        json=payload,
        headers=auth_headers_admin
    )
    assert response.status_code == 200
    data = response.json()
    assert data["precio_vvf"] == 12.00
    assert data["stock_disponible"] == 600


@pytest.mark.asyncio
async def test_deactivate_producto_via_update(
    client: AsyncClient,
    test_productos: list,
    auth_headers_admin: dict
) -> None:
    """Test deactivating a producto via update endpoint."""
    producto = test_productos[0]
    response = await client.put(
        f"/api/products/{producto.id}",
        json={"activo": False},
        headers=auth_headers_admin
    )
    assert response.status_code == 200
    data = response.json()
    assert data["activo"] is False


@pytest.mark.asyncio
async def test_activate_producto_via_update(
    client: AsyncClient,
    test_productos: list,
    db_session,
    auth_headers_admin: dict
) -> None:
    """Test activating a producto via update endpoint."""
    producto = test_productos[0]
    producto.activo = False
    db_session.add(producto)
    await db_session.commit()

    response = await client.put(
        f"/api/products/{producto.id}",
        json={"activo": True},
        headers=auth_headers_admin
    )
    assert response.status_code == 200
    data = response.json()
    assert data["activo"] is True


@pytest.mark.asyncio
async def test_list_productos_with_search_filter(
    client: AsyncClient,
    test_productos: list,
    db_session,
    auth_headers_vendedor: dict
) -> None:
    """Test listing productos with search filter."""
    response = await client.get(
        "/api/products/?search=IBUPROFENO",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert any("IBUPROFENO" in item["nombre"] for item in data["items"])


@pytest.mark.asyncio
async def test_create_producto_validation_error(
    client: AsyncClient,
    auth_headers_admin: dict
) -> None:
    """Test producto creation with invalid data."""
    payload = {
        "codigo_sap": "",  # Invalid: empty
        "nombre": "",  # Invalid: empty
        "precio_vvf": -10,  # Invalid: negative
        "distribuidor": "Dimexa",
    }

    response = await client.post(
        "/api/products/",
        json=payload,
        headers=auth_headers_admin
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_vendedor_cannot_create_producto(
    client: AsyncClient,
    auth_headers_vendedor: dict
) -> None:
    """Test that vendedor cannot create productos."""
    payload = {
        "codigo_sap": "SAP888",
        "nombre": "TEST",
        "distribuidor": "Dimexa",
        "precio_vvf": 10.00,
        "stock_disponible": 100,
    }

    response = await client.post(
        "/api/products/",
        json=payload,
        headers=auth_headers_vendedor
    )
    # Should be 403 Forbidden
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_productos_pagination(
    client: AsyncClient,
    test_productos: list,
    auth_headers_vendedor: dict
) -> None:
    """Test productos pagination."""
    response = await client.get(
        "/api/products/?skip=0&limit=2",
        headers=auth_headers_vendedor
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_list_productos_requires_authentication(client: AsyncClient) -> None:
    """Test that productos require authentication."""
    response = await client.get("/api/products/")
    assert response.status_code == 401
