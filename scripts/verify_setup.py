"""Script de verificación de setup de base de datos.

Verifica que:
1. Todos los modelos SQLAlchemy están correctamente definidos
2. Las migraciones Alembic están presentes
3. La configuración de base de datos es correcta
4. Los archivos de seed data están listos

Uso:
    python scripts/verify_setup.py
"""
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_models():
    """Verify all models are importable."""
    print("\n=== Checking Models ===")

    try:
        from api.db.models import (
            UserModel,
            ProductoModel,
            PedidoModel,
            DetallePedidoModel,
            ComentarioPedidoModel,
            DevolucionModel,
            ComisionModel,
            AuditLogModel,
            NotificationModel,
            DistribuidorConfigModel,
            CondicionPagoModel,
            RazonDevolucionModel,
        )

        models = [
            ("UserModel", UserModel),
            ("ProductoModel", ProductoModel),
            ("PedidoModel", PedidoModel),
            ("DetallePedidoModel", DetallePedidoModel),
            ("ComentarioPedidoModel", ComentarioPedidoModel),
            ("DevolucionModel", DevolucionModel),
            ("ComisionModel", ComisionModel),
            ("AuditLogModel", AuditLogModel),
            ("NotificationModel", NotificationModel),
            ("DistribuidorConfigModel", DistribuidorConfigModel),
            ("CondicionPagoModel", CondicionPagoModel),
            ("RazonDevolucionModel", RazonDevolucionModel),
        ]

        for name, model in models:
            table_name = model.__tablename__
            print(f"  ✓ {name:30s} -> {table_name}")

        print(f"\n✓ All {len(models)} models imported successfully")
        return True

    except ImportError as e:
        print(f"\n✗ Error importing models: {e}")
        return False


def check_migrations():
    """Verify migration files exist."""
    print("\n=== Checking Migrations ===")

    migrations_dir = project_root / "alembic" / "versions"

    if not migrations_dir.exists():
        print(f"✗ Migrations directory not found: {migrations_dir}")
        return False

    migration_files = list(migrations_dir.glob("*.py"))

    if not migration_files:
        print("✗ No migration files found")
        return False

    print(f"\nFound {len(migration_files)} migration(s):")
    for migration_file in migration_files:
        print(f"  ✓ {migration_file.name}")

    # Check for initial migration
    initial_migration = [f for f in migration_files if "001" in f.name or "initial" in f.name.lower()]
    if initial_migration:
        print(f"\n✓ Initial migration found: {initial_migration[0].name}")
    else:
        print("\n⚠ Warning: No initial migration found")

    return True


def check_alembic_config():
    """Verify Alembic configuration."""
    print("\n=== Checking Alembic Config ===")

    alembic_ini = project_root / "alembic.ini"
    env_py = project_root / "alembic" / "env.py"

    if not alembic_ini.exists():
        print(f"✗ alembic.ini not found: {alembic_ini}")
        return False

    print(f"  ✓ alembic.ini exists")

    if not env_py.exists():
        print(f"✗ env.py not found: {env_py}")
        return False

    print(f"  ✓ env.py exists")

    # Check env.py imports models
    with open(env_py, 'r', encoding='utf-8') as f:
        env_content = f.read()
        if "import api.db.models" in env_content:
            print("  ✓ env.py imports models correctly")
        else:
            print("  ⚠ Warning: env.py may not import models")

    return True


def check_seed_data():
    """Verify seed data script exists."""
    print("\n=== Checking Seed Data ===")

    seed_script = project_root / "scripts" / "seed.py"

    if not seed_script.exists():
        print(f"✗ seed.py not found: {seed_script}")
        return False

    print(f"  ✓ seed.py exists")

    # Check seed script has required functions
    with open(seed_script, 'r', encoding='utf-8') as f:
        seed_content = f.read()
        required_functions = [
            "seed_users",
            "seed_productos",
            "seed_distribuidor_config",
            "seed_condiciones_pago",
            "seed_razones_devolucion",
        ]

        missing_functions = []
        for func_name in required_functions:
            if f"async def {func_name}" in seed_content:
                print(f"  ✓ Function {func_name}() found")
            else:
                missing_functions.append(func_name)
                print(f"  ✗ Function {func_name}() missing")

        if missing_functions:
            return False

    return True


def check_database_config():
    """Verify database configuration."""
    print("\n=== Checking Database Config ===")

    try:
        from api.core.config import settings

        print(f"  ✓ Settings imported")

        # Check if DATABASE_URL is set (don't print actual value for security)
        if hasattr(settings, 'DATABASE_URL') and settings.DATABASE_URL:
            # Mask the password in the URL
            db_url = str(settings.DATABASE_URL)
            if '@' in db_url:
                protocol, rest = db_url.split('://', 1)
                if '@' in rest:
                    credentials, host_db = rest.split('@', 1)
                    if ':' in credentials:
                        user, _ = credentials.split(':', 1)
                        masked_url = f"{protocol}://{user}:***@{host_db}"
                    else:
                        masked_url = f"{protocol}://{credentials}@{host_db}"
                else:
                    masked_url = db_url
            else:
                masked_url = db_url

            print(f"  ✓ DATABASE_URL configured: {masked_url}")
        else:
            print("  ⚠ Warning: DATABASE_URL not configured")

        return True

    except ImportError as e:
        print(f"  ✗ Error importing settings: {e}")
        return False


def check_base():
    """Verify Base class is properly configured."""
    print("\n=== Checking Base Configuration ===")

    try:
        from api.db.base import Base, engine, async_session_maker

        print(f"  ✓ Base class imported")
        print(f"  ✓ Engine created")
        print(f"  ✓ Session maker created")

        # Check metadata has tables
        table_count = len(Base.metadata.tables)
        if table_count > 0:
            print(f"  ✓ Base.metadata has {table_count} tables registered")
        else:
            print(f"  ⚠ Warning: Base.metadata has no tables")

        return True

    except ImportError as e:
        print(f"  ✗ Error importing base: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("BONAPHARM Database Setup Verification")
    print("=" * 60)

    checks = [
        ("Models", check_models),
        ("Migrations", check_migrations),
        ("Alembic Config", check_alembic_config),
        ("Seed Data", check_seed_data),
        ("Database Config", check_database_config),
        ("Base Configuration", check_base),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n✗ Error during {name} check: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:20s} {status}")

    print(f"\nResult: {passed}/{total} checks passed")

    if passed == total:
        print("\n✓ All checks passed! Database setup is ready.")
        print("\nNext steps:")
        print("  1. Configure DATABASE_URL in .env")
        print("  2. Run migrations: alembic upgrade head")
        print("  3. Load seed data: python scripts/seed.py")
        return 0
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
