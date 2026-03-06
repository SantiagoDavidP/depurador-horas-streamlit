# Database Setup - BONAPHARM

Este documento describe la configuración de la base de datos, migraciones y seed data para el proyecto BONAPHARM.

## Tecnologías

- **ORM:** SQLAlchemy 2.0 (async con `Mapped[]` type hints)
- **Migraciones:** Alembic (con soporte async)
- **DB Producción:** PostgreSQL (con asyncpg driver)
- **DB Desarrollo:** SQLite (opcional)

## Estructura de la Base de Datos

### Tablas Principales

1. **users** - Usuarios del sistema (Vendedor, AdminComercial, Finanzas, GerenteGeneral)
2. **productos** - Catálogo de productos farmacéuticos
3. **pedidos** - Pedidos de clientes
4. **detalles_pedido** - Líneas de detalle de cada pedido
5. **comentarios_pedido** - Comentarios/historial de pedidos
6. **devoluciones** - Devoluciones de productos
7. **comisiones** - Cálculo mensual de comisiones por distribuidor
8. **audit_logs** - Auditoría de todas las operaciones
9. **notifications** - Notificaciones del sistema

### Tablas de Configuración

10. **distribuidor_config** - Configuración de distribuidores (Dimexa 10%, Química Suiza 13%)
11. **condiciones_pago** - Condiciones de pago (Contado, Crédito 30/60/90)
12. **razones_devolucion** - Catálogo de razones de devolución permitidas

## Migraciones

### Estado Actual

La migración inicial `001_initial_schema_create_all_tables` crea todas las tablas del esquema.

**Archivo:** `alembic/versions/2026_03_05_1000-001_initial_schema_create_all_tables.py`

### Comandos de Alembic

```bash
# Ver historial de migraciones
alembic history

# Ver estado actual
alembic current

# Ejecutar todas las migraciones pendientes
alembic upgrade head

# Revertir una migración
alembic downgrade -1

# Generar nueva migración (autogenerate)
alembic revision --autogenerate -m "descripcion_cambio"

# Crear migración vacía
alembic revision -m "descripcion_cambio"
```

## Seed Data

### Script de Seed

**Archivo:** `scripts/seed.py`

El script carga datos iniciales para desarrollo y testing:

#### Usuarios de Prueba

| Email | Rol | Password |
|-------|-----|----------|
| vendedor@bonapharm.com | Vendedor | demo123 |
| admin@bonapharm.com | AdminComercial | demo123 |
| finanzas@bonapharm.com | Finanzas | demo123 |
| gerente@bonapharm.com | GerenteGeneral | demo123 |

#### Productos (12 productos)

- **Dimexa (5 productos):** Paracetamol, Ibuprofeno, Amoxicilina, Omeprazol, Loratadina
- **Química Suiza (5 productos):** Diclofenaco, Metformina, Enalapril, Losartan, Atorvastatina
- **Especiales (2 productos refrigerados):** Vacuna Influenza, Insulina Glargina (inafectos a devolución)

#### Configuración de Distribuidores

- **Dimexa:** 10% comisión, mínimo S/1,000
- **Química Suiza:** 13% comisión, mínimo S/1,500

#### Condiciones de Pago

- Contado (0 días)
- Crédito 30 (30 días)
- Crédito 60 (60 días)
- Crédito 90 (90 días)

#### Razones de Devolución (8 razones)

- Producto vencido
- Producto dañado
- Error en el pedido
- Producto no solicitado
- Falta de demanda
- Cambio de presentación
- Retiro de mercado
- Defecto de fabricación

### Ejecutar Seed Data

```bash
# Desde la raíz del proyecto
python scripts/seed.py
```

El script es **idempotente** - verifica si los datos ya existen antes de insertarlos.

## Configuración de Conexión

### Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# PostgreSQL (Producción)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bonapharm

# SQLite (Desarrollo - opcional)
# DATABASE_URL=sqlite+aiosqlite:///./bonapharm.db
```

### Configuración en Código

**Archivo:** `api/db/base.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)
```

## Setup Inicial Completo

### 1. Configurar Base de Datos

```bash
# Crear base de datos PostgreSQL
createdb bonapharm

# O usar Docker
docker run --name bonapharm-postgres \
  -e POSTGRES_DB=bonapharm \
  -e POSTGRES_USER=bonapharm \
  -e POSTGRES_PASSWORD=bonapharm123 \
  -p 5432:5432 \
  -d postgres:15
```

### 2. Configurar Variables de Entorno

```bash
# Copiar ejemplo
cp .env.example .env

# Editar .env con tu configuración
DATABASE_URL=postgresql+asyncpg://bonapharm:bonapharm123@localhost:5432/bonapharm
```

### 3. Ejecutar Migraciones

```bash
# Aplicar migración inicial
alembic upgrade head
```

### 4. Cargar Seed Data

```bash
# Cargar datos iniciales
python scripts/seed.py
```

### 5. Verificar

```bash
# Conectarse a la DB y verificar
psql -U bonapharm -d bonapharm

# Ver tablas
\dt

# Ver usuarios
SELECT email, rol FROM users;

# Ver productos
SELECT codigo_sap, nombre, distribuidor FROM productos LIMIT 5;
```

## Desarrollo: Crear Nueva Migración

### Flujo de Trabajo

1. **Modificar modelo SQLAlchemy** en `api/db/models/`

```python
# Ejemplo: agregar campo a ProductoModel
class ProductoModel(Base):
    # ... campos existentes ...

    # Nuevo campo
    categoria: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

2. **Generar migración automática**

```bash
alembic revision --autogenerate -m "add_categoria_to_productos"
```

3. **Revisar migración generada** en `alembic/versions/`

```python
def upgrade() -> None:
    op.add_column('productos', sa.Column('categoria', sa.String(100), nullable=True))

def downgrade() -> None:
    op.drop_column('productos', 'categoria')
```

4. **Aplicar migración**

```bash
alembic upgrade head
```

5. **Actualizar seed data** si es necesario

## Índices y Optimizaciones

La migración inicial incluye índices en:

- `users.email` (unique)
- `users.entra_id` (unique)
- `productos.codigo_sap` (unique)
- `productos.distribuidor`
- `pedidos.codigo_pedido` (unique)
- `pedidos.cliente_ruc`
- `pedidos.estado`
- `pedidos.vendedor_id`
- `devoluciones.codigo_devolucion` (unique)
- `devoluciones.estado`
- `comisiones.distribuidor`
- `comisiones.mes, anio` (composite)
- `audit_logs.entidad`
- `audit_logs.entidad_id`
- `audit_logs.user_id`
- `notifications.user_id`
- `notifications.leido`

## Foreign Keys y Cascadas

Todas las relaciones están definidas con:

- `CASCADE` en deletes donde aplica (detalles_pedido, comentarios_pedido)
- Timestamps automáticos (`created_at`, `updated_at`)
- UUID como primary keys para mejor distribución

## Troubleshooting

### Error: No module named 'asyncpg'

```bash
pip install asyncpg
```

### Error: No module named 'psycopg2'

```bash
pip install psycopg2-binary
```

### Error: Permission denied en Alembic

```bash
# Usar python -m alembic en lugar de alembic directamente
python -m alembic upgrade head
```

### Error: Can't locate revision

```bash
# Verificar que existe la tabla alembic_version
psql -U bonapharm -d bonapharm -c "SELECT * FROM alembic_version;"

# Si no existe, crear manualmente
psql -U bonapharm -d bonapharm -c "CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY);"
```

## Modelos SQLAlchemy

Ubicación: `api/db/models/`

- `user.py` - UserModel
- `producto.py` - ProductoModel
- `pedido.py` - PedidoModel, DetallePedidoModel, ComentarioPedidoModel
- `devolucion.py` - DevolucionModel
- `comision.py` - ComisionModel
- `audit_log.py` - AuditLogModel
- `notification.py` - NotificationModel
- `config.py` - DistribuidorConfigModel, CondicionPagoModel, RazonDevolucionModel

## Próximos Pasos

- [ ] Implementar soft deletes (campo `deleted_at`)
- [ ] Agregar índices GIN para búsqueda full-text en productos
- [ ] Implementar particionamiento en `audit_logs` por fecha
- [ ] Configurar replicación para reporting
- [ ] Implementar backup automático diario
