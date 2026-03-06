# tests/backend/test_comisiones.py
"""Tests for comisiones endpoints."""
import pytest
from httpx import AsyncClient
from api.db.models.comision import ComisionModel as Comision
from api.db.models.user import UserModel as User


@pytest.mark.asyncio
async def test_list_comisiones(
    client: AsyncClient,
    test_comision: Comision,
    auth_headers_finanzas: dict
) -> None:
    """Test listing comisiones."""
    response = await client.get(
        "/api/commissions/",
        headers=auth_headers_finanzas
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_filter_comisiones_by_distribuidor(
    client: AsyncClient,
    test_comision: Comision,
    auth_headers_finanzas: dict
) -> None:
    """Test filtering comisiones by distribuidor."""
    response = await client.get(
        "/api/commissions/?distribuidor=Dimexa",
        headers=auth_headers_finanzas
    )
    assert response.status_code == 200
    data = response.json()
    assert all(item["distribuidor"] == "Dimexa" for item in data["items"])


@pytest.mark.asyncio
async def test_filter_comisiones_by_periodo(
    client: AsyncClient,
    test_comision: Comision,
    auth_headers_finanzas: dict
) -> None:
    """Test filtering comisiones by mes/anio."""
    response = await client.get(
        "/api/commissions/?mes=3&anio=2026",
        headers=auth_headers_finanzas
    )
    assert response.status_code == 200
    data = response.json()
    assert all(item["mes"] == 3 and item["anio"] == 2026 for item in data["items"])


@pytest.mark.asyncio
async def test_calculate_comisiones(
    client: AsyncClient,
    test_pedido_aprobado,
    test_productos,
    auth_headers_finanzas: dict
) -> None:
    """Test calculating comisiones for a period."""
    response = await client.get(
        "/api/commissions/calculate?mes=3&anio=2026",
        headers=auth_headers_finanzas
    )
    assert response.status_code == 200
    data = response.json()
    assert "mes" in data
    assert "anio" in data
    assert "commissions" in data


@pytest.mark.asyncio
async def test_calculate_comisiones_for_specific_distribuidor(
    client: AsyncClient,
    test_pedido_aprobado,
    auth_headers_finanzas: dict
) -> None:
    """Test calculating comisiones for specific distribuidor."""
    response = await client.get(
        "/api/commissions/calculate?mes=3&anio=2026&distribuidor=Dimexa",
        headers=auth_headers_finanzas
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_comision_dimexa_percentage(
    client: AsyncClient,
    test_comision: Comision,
    auth_headers_finanzas: dict
) -> None:
    """Test that Dimexa has 10% commission."""
    response = await client.get(
        "/api/commissions/?distribuidor=Dimexa",
        headers=auth_headers_finanzas
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        if item["distribuidor"] == "Dimexa":
            assert item["porcentaje"] == 10.0


@pytest.mark.asyncio
async def test_get_comision_detail(
    client: AsyncClient,
    test_comision: Comision,
    auth_headers_finanzas: dict
) -> None:
    """Test getting comision detail."""
    response = await client.get(
        f"/api/commissions/{test_comision.id}/detail",
        headers=auth_headers_finanzas
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_comision.id)


@pytest.mark.asyncio
async def test_approve_comision(
    client: AsyncClient,
    test_comision: Comision,
    auth_headers_finanzas: dict
) -> None:
    """Test approving comision."""
    response = await client.post(
        f"/api/commissions/{test_comision.id}/approve",
        json={"observaciones": "Aprobada por test"},
        headers=auth_headers_finanzas
    )
    assert response.status_code == 200
    data = response.json()
    assert data["estado"] == "Aprobada"


@pytest.mark.asyncio
async def test_comision_calculation_accuracy(
    client: AsyncClient,
    test_comision: Comision,
    auth_headers_finanzas: dict
) -> None:
    """Test that comision calculation is accurate."""
    response = await client.get(
        f"/api/commissions/{test_comision.id}/detail",
        headers=auth_headers_finanzas
    )
    assert response.status_code == 200
    data = response.json()

    # Verify: comision_bruta = ventas_totales * (porcentaje / 100)
    expected = data["ventas_totales"] * (data["porcentaje"] / 100)
    assert abs(data["comision_bruta"] - expected) < 0.01


@pytest.mark.asyncio
async def test_list_comisiones_requires_authentication(client: AsyncClient) -> None:
    """Test that comisiones require authentication."""
    response = await client.get("/api/commissions/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_commissions_summary(
    client: AsyncClient,
    test_comision: Comision,
    auth_headers_finanzas: dict
) -> None:
    """Test commissions summary endpoint."""
    response = await client.get(
        "/api/commissions/summary?mes=3&anio=2026",
        headers=auth_headers_finanzas
    )
    assert response.status_code == 200
    data = response.json()
    assert "mes" in data
    assert "anio" in data
    assert "ventas_totales" in data
