# tests/backend/conftest.py
"""Pytest configuration and fixtures for backend tests."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from datetime import datetime, timezone
from decimal import Decimal

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Override DATABASE_URL before importing app so it uses SQLite for tests
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_temp.db"
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ENVIRONMENT", "test")

from api.main import app
from api.db.base import Base
from api.core.dependencies import get_db
from api.db.models.user import UserModel
from api.db.models.producto import ProductoModel
from api.db.models.pedido import PedidoModel, DetallePedidoModel
from api.db.models.devolucion import DevolucionModel
from api.db.models.comision import ComisionModel
from api.core.security import hash_password

# Test database (SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_temp.db"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use asyncio event loop for all tests."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a test database engine for each test function."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Provide a clean database session for each test."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """Provide an HTTP test client with overridden DB session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def client_no_db():
    """Test client without database override (for endpoints that don't use DB)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


# ========== DATA FIXTURES ==========

@pytest_asyncio.fixture
async def test_vendedor(db_session: AsyncSession) -> UserModel:
    """Create a test vendedor user."""
    user = UserModel(
        nombre_completo="Test Vendedor",
        email="vendedor@test.com",
        password_hash=hash_password("password123"),
        rol="Vendedor",
        activo=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> UserModel:
    """Create a test admin user."""
    user = UserModel(
        nombre_completo="Test Admin",
        email="admin@test.com",
        password_hash=hash_password("admin123"),
        rol="AdminComercial",
        activo=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_finanzas(db_session: AsyncSession) -> UserModel:
    """Create a test finanzas user."""
    user = UserModel(
        nombre_completo="Test Finanzas",
        email="finanzas@test.com",
        password_hash=hash_password("finanzas123"),
        rol="Finanzas",
        activo=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_productos(db_session: AsyncSession) -> list:
    """Create test productos."""
    productos = [
        ProductoModel(
            codigo_sap="SAP001",
            nombre="PARACETAMOL 500MG",
            molecula="Paracetamol",
            distribuidor="Dimexa",
            precio_vvf=10.50,
            precio_compra=8.00,
            stock_disponible=500,
            activo=True,
        ),
        ProductoModel(
            codigo_sap="SAP002",
            nombre="IBUPROFENO 400MG",
            molecula="Ibuprofeno",
            distribuidor="Quimica Suiza",
            precio_vvf=15.00,
            precio_compra=11.00,
            stock_disponible=300,
            activo=True,
        ),
        ProductoModel(
            codigo_sap="SAP003",
            nombre="AMOXICILINA 500MG",
            molecula="Amoxicilina",
            distribuidor="Dimexa",
            precio_vvf=20.00,
            precio_compra=15.00,
            stock_disponible=200,
            activo=True,
        ),
    ]
    for producto in productos:
        db_session.add(producto)
    await db_session.commit()
    for producto in productos:
        await db_session.refresh(producto)
    return productos


@pytest_asyncio.fixture
async def test_pedido(
    db_session: AsyncSession,
    test_vendedor: UserModel,
    test_productos: list
) -> PedidoModel:
    """Create a test pedido with detalle."""
    pedido = PedidoModel(
        codigo_pedido="PED-2026-TEST-0001",
        vendedor_id=test_vendedor.id,
        cliente_ruc="20123456789",
        cliente_razon_social="FARMACIA TEST SAC",
        condicion_pago="Contado",
        estado="Borrador",
        subtotal=525.00,
        igv=94.50,
        total=619.50,
    )
    db_session.add(pedido)
    await db_session.commit()
    await db_session.refresh(pedido)

    # Add detalle
    detalle = DetallePedidoModel(
        pedido_id=pedido.id,
        producto_id=test_productos[0].id,
        cantidad=50,
        precio_unitario=test_productos[0].precio_vvf,
        subtotal=525.00,
    )
    db_session.add(detalle)
    await db_session.commit()

    return pedido


@pytest_asyncio.fixture
async def test_pedido_aprobado(
    db_session: AsyncSession,
    test_vendedor: UserModel,
    test_productos: list
) -> PedidoModel:
    """Create an approved test pedido."""
    pedido = PedidoModel(
        codigo_pedido="PED-2026-TEST-0002",
        vendedor_id=test_vendedor.id,
        cliente_ruc="20987654321",
        cliente_razon_social="BOTICA TEST EIRL",
        condicion_pago="Credito",
        estado="Aprobado",
        subtotal=2000.00,
        igv=360.00,
        total=2360.00,
    )
    db_session.add(pedido)
    await db_session.commit()
    await db_session.refresh(pedido)

    # Add detalle
    detalle = DetallePedidoModel(
        pedido_id=pedido.id,
        producto_id=test_productos[0].id,
        cantidad=100,
        precio_unitario=test_productos[0].precio_vvf,
        subtotal=1050.00,
    )
    db_session.add(detalle)
    await db_session.commit()

    return pedido


@pytest_asyncio.fixture
async def test_devolucion(
    db_session: AsyncSession,
    test_pedido_aprobado: PedidoModel,
    test_productos: list
) -> DevolucionModel:
    """Create a test devolucion."""
    devolucion = DevolucionModel(
        codigo_devolucion="DEV-2026-TEST-0001",
        pedido_id=test_pedido_aprobado.id,
        numero_factura="F001-00012345",
        producto_id=test_productos[0].id,
        cantidad=10,
        lote="LOTE001",
        razon="producto_vencido",
        estado="En Proceso",
        valorizado=105.00,
        solicitante_id=test_pedido_aprobado.vendedor_id,
    )
    db_session.add(devolucion)
    await db_session.commit()
    await db_session.refresh(devolucion)
    return devolucion


@pytest_asyncio.fixture
async def test_comision(
    db_session: AsyncSession,
    test_vendedor: UserModel,
    test_pedido_aprobado: PedidoModel
) -> ComisionModel:
    """Create a test comision."""
    comision = ComisionModel(
        distribuidor="Dimexa",
        mes=3,
        anio=2026,
        ventas_totales=2000.00,
        porcentaje=10.0,
        comision_bruta=200.00,
        recuperos=0.0,
        neto_a_pagar=200.00,
        estado="Calculada",
        calculado_por_id=test_vendedor.id,
    )
    db_session.add(comision)
    await db_session.commit()
    await db_session.refresh(comision)
    return comision


@pytest.fixture
def auth_headers_vendedor(test_vendedor: UserModel) -> dict:
    """Generate auth headers for vendedor."""
    from api.core.security import create_access_token
    token = create_access_token({"sub": str(test_vendedor.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_admin(test_admin: UserModel) -> dict:
    """Generate auth headers for admin."""
    from api.core.security import create_access_token
    token = create_access_token({"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_finanzas(test_finanzas: UserModel) -> dict:
    """Generate auth headers for finanzas."""
    from api.core.security import create_access_token
    token = create_access_token({"sub": str(test_finanzas.id)})
    return {"Authorization": f"Bearer {token}"}
