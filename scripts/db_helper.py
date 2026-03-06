"""Database helper scripts para operaciones comunes.

Este script proporciona comandos útiles para:
- Resetear la base de datos
- Verificar el estado de las migraciones
- Re-seed data
- Backup y restore

Uso:
    python scripts/db_helper.py reset      # Reset completo (drop + migrate + seed)
    python scripts/db_helper.py migrate    # Solo ejecutar migraciones
    python scripts/db_helper.py seed       # Solo seed data
    python scripts/db_helper.py status     # Ver estado de DB y migraciones
"""
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def drop_all_tables():
    """Drop all tables from the database."""
    from api.db.base import engine, Base

    print("\nDropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("✓ All tables dropped")


async def create_all_tables():
    """Create all tables in the database."""
    from api.db.base import engine, Base

    print("\nCreating all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ All tables created")


async def run_seed():
    """Run seed data script."""
    print("\nRunning seed data...")
    from scripts.seed import main as seed_main
    await seed_main()


async def check_db_status():
    """Check database connection and table status."""
    from api.db.base import engine, async_session_maker
    from sqlalchemy import text

    print("\n=== Database Status ===\n")

    try:
        # Test connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        print("✓ Database connection: OK")

        # Check tables
        async with async_session_maker() as session:
            from api.db.models import UserModel, ProductoModel, PedidoModel

            # Count records
            from sqlalchemy import select, func

            user_count = await session.scalar(select(func.count()).select_from(UserModel))
            product_count = await session.scalar(select(func.count()).select_from(ProductoModel))
            pedido_count = await session.scalar(select(func.count()).select_from(PedidoModel))

            print(f"\nRecords:")
            print(f"  - Users: {user_count}")
            print(f"  - Products: {product_count}")
            print(f"  - Pedidos: {pedido_count}")

        # Check Alembic version
        async with engine.connect() as conn:
            try:
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar_one_or_none()
                if version:
                    print(f"\n✓ Alembic version: {version}")
                else:
                    print("\n⚠ No Alembic version found - run migrations")
            except Exception:
                print("\n⚠ Alembic version table not found - run migrations")

    except Exception as e:
        print(f"✗ Database error: {e}")
        sys.exit(1)


async def reset_database():
    """Complete database reset: drop, create, migrate, seed."""
    print("\n=== BONAPHARM Database Reset ===")
    print("\nWARNING: This will delete ALL data!")
    response = input("\nAre you sure? Type 'yes' to continue: ")

    if response.lower() != 'yes':
        print("Aborted.")
        return

    try:
        # Drop all tables
        await drop_all_tables()

        # Create all tables (this will also create alembic_version)
        await create_all_tables()

        # Mark current migration as applied
        print("\nMarking migration as applied...")
        from api.db.base import engine
        from sqlalchemy import text

        async with engine.begin() as conn:
            # Create alembic_version table if it doesn't exist
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))

            # Insert current revision
            await conn.execute(text("""
                INSERT INTO alembic_version (version_num)
                VALUES ('001')
                ON CONFLICT (version_num) DO NOTHING
            """))

        print("✓ Migration marked as applied")

        # Run seed data
        await run_seed()

        print("\n✓ Database reset completed successfully!")

    except Exception as e:
        print(f"\n✗ Error during reset: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def print_help():
    """Print help message."""
    print("""
Database Helper Script - BONAPHARM

Commands:
    reset       Complete database reset (drop + create + seed)
    migrate     Run pending migrations (alembic upgrade head)
    seed        Run seed data only
    status      Check database status and connection
    help        Show this help message

Examples:
    python scripts/db_helper.py reset
    python scripts/db_helper.py status
    python scripts/db_helper.py seed
""")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == 'reset':
        await reset_database()
    elif command == 'migrate':
        import subprocess
        print("\nRunning migrations...")
        result = subprocess.run(['alembic', 'upgrade', 'head'])
        if result.returncode == 0:
            print("\n✓ Migrations completed")
        else:
            print("\n✗ Migration failed")
            sys.exit(1)
    elif command == 'seed':
        await run_seed()
    elif command == 'status':
        await check_db_status()
    elif command == 'help':
        print_help()
    else:
        print(f"Unknown command: {command}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
