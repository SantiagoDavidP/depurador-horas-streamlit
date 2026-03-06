"""Script de seed data para BONAPHARM.

Este script carga datos iniciales en la base de datos para desarrollo y testing.
Incluye:
- Usuarios de prueba (vendedor, admin comercial, finanzas, gerente general)
- Productos farmacéuticos de catálogo
- Configuraciones de distribuidores (Dimexa 10%, Química Suiza 13%)
- Condiciones de pago
- Razones de devolución

Uso:
    python scripts/seed.py
"""
import asyncio
import sys
import uuid
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.base import async_session_maker, engine, Base
from api.db.models import (
    UserModel,
    ProductoModel,
    DistribuidorConfigModel,
    CondicionPagoModel,
    RazonDevolucionModel,
)


async def init_db():
    """Crea todas las tablas si no existen."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Tablas creadas/verificadas")


async def seed_users(session: AsyncSession):
    """Crea usuarios de prueba."""
    users_data = [
        {
            "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
            "nombre_completo": "Juan Pérez",
            "email": "vendedor@bonapharm.com",
            "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYWfJ0xEZLi",  # password: demo123
            "rol": "Vendedor",
            "activo": True,
        },
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
            "nombre_completo": "María García",
            "email": "admin@bonapharm.com",
            "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYWfJ0xEZLi",
            "rol": "AdminComercial",
            "activo": True,
        },
        {
            "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
            "nombre_completo": "Carlos Rodríguez",
            "email": "finanzas@bonapharm.com",
            "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYWfJ0xEZLi",
            "rol": "Finanzas",
            "activo": True,
        },
        {
            "id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
            "nombre_completo": "Ana Martínez",
            "email": "gerente@bonapharm.com",
            "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYWfJ0xEZLi",
            "rol": "GerenteGeneral",
            "activo": True,
        },
    ]

    # Check if users already exist
    result = await session.execute(select(UserModel).limit(1))
    if result.scalar_one_or_none():
        print("✓ Usuarios ya existen, saltando seed de usuarios")
        return

    for user_data in users_data:
        user = UserModel(**user_data)
        session.add(user)

    await session.commit()
    print(f"✓ {len(users_data)} usuarios creados")


async def seed_productos(session: AsyncSession):
    """Crea productos farmacéuticos de catálogo."""
    productos_data = [
        # Productos Dimexa
        {
            "codigo_sap": "DIM001",
            "nombre": "Paracetamol 500mg x 100 tabletas",
            "molecula": "Paracetamol",
            "precio_vvf": 15.50,
            "precio_compra": 10.00,
            "distribuidor": "Dimexa",
            "stock_disponible": 500,
            "inafecto_devolucion": False,
        },
        {
            "codigo_sap": "DIM002",
            "nombre": "Ibuprofeno 400mg x 50 tabletas",
            "molecula": "Ibuprofeno",
            "precio_vvf": 22.80,
            "precio_compra": 15.20,
            "distribuidor": "Dimexa",
            "stock_disponible": 300,
            "inafecto_devolucion": False,
        },
        {
            "codigo_sap": "DIM003",
            "nombre": "Amoxicilina 500mg x 21 capsulas",
            "molecula": "Amoxicilina",
            "precio_vvf": 35.00,
            "precio_compra": 25.00,
            "distribuidor": "Dimexa",
            "stock_disponible": 200,
            "inafecto_devolucion": False,
        },
        {
            "codigo_sap": "DIM004",
            "nombre": "Omeprazol 20mg x 30 capsulas",
            "molecula": "Omeprazol",
            "precio_vvf": 28.50,
            "precio_compra": 19.00,
            "distribuidor": "Dimexa",
            "stock_disponible": 400,
            "inafecto_devolucion": False,
        },
        {
            "codigo_sap": "DIM005",
            "nombre": "Loratadina 10mg x 30 tabletas",
            "molecula": "Loratadina",
            "precio_vvf": 18.00,
            "precio_compra": 12.00,
            "distribuidor": "Dimexa",
            "stock_disponible": 350,
            "inafecto_devolucion": False,
        },
        # Productos Química Suiza
        {
            "codigo_sap": "QS001",
            "nombre": "Diclofenaco 50mg x 30 tabletas",
            "molecula": "Diclofenaco",
            "precio_vvf": 25.00,
            "precio_compra": 17.50,
            "distribuidor": "Quimica Suiza",
            "stock_disponible": 250,
            "inafecto_devolucion": False,
        },
        {
            "codigo_sap": "QS002",
            "nombre": "Metformina 850mg x 60 tabletas",
            "molecula": "Metformina",
            "precio_vvf": 32.00,
            "precio_compra": 22.00,
            "distribuidor": "Quimica Suiza",
            "stock_disponible": 180,
            "inafecto_devolucion": False,
        },
        {
            "codigo_sap": "QS003",
            "nombre": "Enalapril 10mg x 30 tabletas",
            "molecula": "Enalapril",
            "precio_vvf": 28.00,
            "precio_compra": 20.00,
            "distribuidor": "Quimica Suiza",
            "stock_disponible": 220,
            "inafecto_devolucion": False,
        },
        {
            "codigo_sap": "QS004",
            "nombre": "Losartan 50mg x 30 tabletas",
            "molecula": "Losartan",
            "precio_vvf": 35.00,
            "precio_compra": 24.50,
            "distribuidor": "Quimica Suiza",
            "stock_disponible": 200,
            "inafecto_devolucion": False,
        },
        {
            "codigo_sap": "QS005",
            "nombre": "Atorvastatina 20mg x 30 tabletas",
            "molecula": "Atorvastatina",
            "precio_vvf": 42.00,
            "precio_compra": 30.00,
            "distribuidor": "Quimica Suiza",
            "stock_disponible": 150,
            "inafecto_devolucion": False,
        },
        # Productos especiales (inafectos a devolución)
        {
            "codigo_sap": "DIM999",
            "nombre": "Vacuna Influenza (refrigerado)",
            "molecula": "Virus Influenza inactivado",
            "precio_vvf": 85.00,
            "precio_compra": 65.00,
            "distribuidor": "Dimexa",
            "stock_disponible": 50,
            "inafecto_devolucion": True,  # Producto refrigerado no se puede devolver
        },
        {
            "codigo_sap": "QS999",
            "nombre": "Insulina Glargina (refrigerado)",
            "molecula": "Insulina Glargina",
            "precio_vvf": 120.00,
            "precio_compra": 90.00,
            "distribuidor": "Quimica Suiza",
            "stock_disponible": 30,
            "inafecto_devolucion": True,  # Producto refrigerado no se puede devolver
        },
    ]

    # Check if productos already exist
    result = await session.execute(select(ProductoModel).limit(1))
    if result.scalar_one_or_none():
        print("✓ Productos ya existen, saltando seed de productos")
        return

    for producto_data in productos_data:
        producto = ProductoModel(**producto_data)
        session.add(producto)

    await session.commit()
    print(f"✓ {len(productos_data)} productos creados")


async def seed_distribuidor_config(session: AsyncSession):
    """Crea configuraciones de distribuidores."""
    distribuidores_data = [
        {
            "nombre": "Dimexa",
            "ruc": "20123456789",
            "porcentaje_comision": 10.0,
            "monto_minimo_pedido": 1000.00,
            "activo": True,
        },
        {
            "nombre": "Quimica Suiza",
            "ruc": "20987654321",
            "porcentaje_comision": 13.0,
            "monto_minimo_pedido": 1500.00,
            "activo": True,
        },
    ]

    # Check if config already exists
    result = await session.execute(select(DistribuidorConfigModel).limit(1))
    if result.scalar_one_or_none():
        print("✓ Configuración de distribuidores ya existe, saltando seed")
        return

    for distribuidor_data in distribuidores_data:
        distribuidor = DistribuidorConfigModel(**distribuidor_data)
        session.add(distribuidor)

    await session.commit()
    print(f"✓ {len(distribuidores_data)} distribuidores configurados")


async def seed_condiciones_pago(session: AsyncSession):
    """Crea condiciones de pago."""
    condiciones_data = [
        {"nombre": "Contado", "dias_credito": 0, "activo": True},
        {"nombre": "Credito 30", "dias_credito": 30, "activo": True},
        {"nombre": "Credito 60", "dias_credito": 60, "activo": True},
        {"nombre": "Credito 90", "dias_credito": 90, "activo": True},
    ]

    # Check if condiciones already exist
    result = await session.execute(select(CondicionPagoModel).limit(1))
    if result.scalar_one_or_none():
        print("✓ Condiciones de pago ya existen, saltando seed")
        return

    for condicion_data in condiciones_data:
        condicion = CondicionPagoModel(**condicion_data)
        session.add(condicion)

    await session.commit()
    print(f"✓ {len(condiciones_data)} condiciones de pago creadas")


async def seed_razones_devolucion(session: AsyncSession):
    """Crea razones de devolución."""
    razones_data = [
        {"nombre": "Producto vencido", "activo": True},
        {"nombre": "Producto dañado", "activo": True},
        {"nombre": "Error en el pedido", "activo": True},
        {"nombre": "Producto no solicitado", "activo": True},
        {"nombre": "Falta de demanda", "activo": True},
        {"nombre": "Cambio de presentación", "activo": True},
        {"nombre": "Retiro de mercado", "activo": True},
        {"nombre": "Defecto de fabricación", "activo": True},
    ]

    # Check if razones already exist
    result = await session.execute(select(RazonDevolucionModel).limit(1))
    if result.scalar_one_or_none():
        print("✓ Razones de devolución ya existen, saltando seed")
        return

    for razon_data in razones_data:
        razon = RazonDevolucionModel(**razon_data)
        session.add(razon)

    await session.commit()
    print(f"✓ {len(razones_data)} razones de devolución creadas")


async def main():
    """Ejecuta todos los seeds."""
    print("\n=== BONAPHARM Seed Data ===\n")

    try:
        # Initialize database
        await init_db()

        # Create session
        async with async_session_maker() as session:
            # Run all seed functions
            await seed_users(session)
            await seed_productos(session)
            await seed_distribuidor_config(session)
            await seed_condiciones_pago(session)
            await seed_razones_devolucion(session)

        print("\n✓ Seed data completado exitosamente!\n")
        print("Usuarios de prueba:")
        print("  - vendedor@bonapharm.com (Vendedor)")
        print("  - admin@bonapharm.com (Admin Comercial)")
        print("  - finanzas@bonapharm.com (Finanzas)")
        print("  - gerente@bonapharm.com (Gerente General)")
        print("  Password para todos: demo123\n")

    except Exception as e:
        print(f"\n✗ Error durante seed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
