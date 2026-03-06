# Database Setup - Resumen Completo

## Archivos Generados

### 1. Migración Inicial de Alembic

**Archivo:** `alembic/versions/2026_03_05_1000-001_initial_schema_create_all_tables.py`

- Crea todas las 12 tablas del esquema
- Incluye índices para optimización de queries
- Foreign keys con cascadas apropiadas
- Timestamps automáticos en todas las tablas
- Soporta upgrade y downgrade

**Tablas creadas:**
- users (usuarios del sistema)
- productos (catálogo farmacéutico)
- pedidos (pedidos de clientes)
- detalles_pedido (líneas de detalle)
- comentarios_pedido (historial de comentarios)
- devoluciones (devoluciones de productos)
- comisiones (cálculo mensual)
- audit_logs (auditoría completa)
- notifications (notificaciones)
- distribuidor_config (config Dimexa/Química Suiza)
- condiciones_pago (Contado/Crédito)
- razones_devolucion (catálogo de razones)

### 2. Script de Seed Data

**Archivo:** `scripts/seed.py`

**Datos incluidos:**

- **4 Usuarios de prueba:**
  - vendedor@bonapharm.com (Vendedor)
  - admin@bonapharm.com (AdminComercial)
  - finanzas@bonapharm.com (Finanzas)
  - gerente@bonapharm.com (GerenteGeneral)
  - Password: demo123

- **12 Productos farmacéuticos:**
  - 5 productos Dimexa (comisión 10%)
  - 5 productos Química Suiza (comisión 13%)
  - 2 productos especiales refrigerados (inafectos a devolución)

- **2 Configuraciones de distribuidores:**
  - Dimexa: 10% comisión, mínimo S/1,000
  - Química Suiza: 13% comisión, mínimo S/1,500

- **4 Condiciones de pago:**
  - Contado (0 días)
  - Crédito 30/60/90 días

- **8 Razones de devolución:**
  - Producto vencido, dañado, error en pedido, etc.

**Características:**
- Idempotente (verifica antes de insertar)
- IDs UUID fijos para usuarios (facilita testing)
- Manejo de errores robusto

### 3. Database Helper Script

**Archivo:** `scripts/db_helper.py`

**Comandos disponibles:**
```bash
python scripts/db_helper.py reset      # Reset completo (drop + migrate + seed)
python scripts/db_helper.py migrate    # Ejecutar migraciones
python scripts/db_helper.py seed       # Solo seed data
python scripts/db_helper.py status     # Ver estado de DB
```

### 4. Script de Verificación

**Archivo:** `scripts/verify_setup.py`

Verifica:
- Todos los modelos SQLAlchemy son importables
- Archivos de migración existen
- Configuración de Alembic correcta
- Script de seed data completo
- Configuración de base de datos

### 5. Documentación

**Archivo:** `DATABASE.md`

Documentación completa que incluye:
- Estructura de la base de datos
- Guía de migraciones Alembic
- Detalle de seed data
- Setup inicial completo
- Troubleshooting
- Mejores prácticas

## Modelos SQLAlchemy Actualizados

**Archivo actualizado:** `api/db/models/__init__.py`

Se agregó `ComentarioPedidoModel` a las exportaciones para que Alembic lo detecte.

## Comandos de Ejecución

### Setup Inicial Completo

```bash
# 1. Verificar que todo está listo
python scripts/verify_setup.py

# 2. Ejecutar migraciones
alembic upgrade head

# 3. Cargar seed data
python scripts/seed.py

# 4. Verificar estado
python scripts/db_helper.py status
```

### Desarrollo Diario

```bash
# Ver estado de DB
python scripts/db_helper.py status

# Reset completo (desarrollo)
python scripts/db_helper.py reset

# Solo re-seed
python scripts/db_helper.py seed
```

### Crear Nueva Migración

```bash
# 1. Modificar modelo en api/db/models/

# 2. Generar migración automática
alembic revision --autogenerate -m "descripcion_cambio"

# 3. Revisar archivo generado en alembic/versions/

# 4. Aplicar migración
alembic upgrade head
```

## Índices Creados

Optimizaciones incluidas en la migración inicial:

- **users:** email (unique), entra_id (unique)
- **productos:** codigo_sap (unique), distribuidor
- **pedidos:** codigo_pedido (unique), cliente_ruc, estado, vendedor_id
- **devoluciones:** codigo_devolucion (unique), estado
- **comisiones:** distribuidor, (mes, anio) composite
- **audit_logs:** entidad, entidad_id, user_id
- **notifications:** user_id, leido

## Foreign Keys y Relaciones

Todas las relaciones están correctamente definidas:

- **pedidos → users:** vendedor_id, aprobador_id
- **detalles_pedido → pedidos:** CASCADE on delete
- **detalles_pedido → productos**
- **comentarios_pedido → pedidos:** CASCADE on delete
- **comentarios_pedido → users**
- **devoluciones → pedidos, productos, users**
- **comisiones → users:** calculado_por_id, aprobado_por_id
- **audit_logs → users**
- **notifications → users**

## Próximos Pasos

1. **Configurar .env:**
   ```env
   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/bonapharm
   ```

2. **Crear base de datos PostgreSQL:**
   ```bash
   createdb bonapharm
   # o usar Docker
   ```

3. **Ejecutar setup inicial:**
   ```bash
   python scripts/verify_setup.py
   alembic upgrade head
   python scripts/seed.py
   ```

4. **Iniciar desarrollo:**
   - Backend ya puede hacer queries a la DB
   - Frontend puede hacer peticiones a los endpoints
   - Todos los datos de prueba están disponibles

## Verificación Final

Ejecutar:
```bash
python scripts/verify_setup.py
```

Debe mostrar:
```
✓ Models               PASS
✓ Migrations           PASS
✓ Alembic Config       PASS
✓ Seed Data            PASS
✓ Database Config      PASS
✓ Base Configuration   PASS

Result: 6/6 checks passed
```

## Archivos Generados (Resumen)

```
DemoEnd2End/
├── alembic/
│   ├── versions/
│   │   └── 2026_03_05_1000-001_initial_schema_create_all_tables.py ✓ NUEVO
│   ├── env.py (ya existía, verificado)
│   └── alembic.ini (ya existía, verificado)
├── scripts/
│   ├── seed.py ✓ ACTUALIZADO (datos completos)
│   ├── db_helper.py ✓ NUEVO
│   └── verify_setup.py ✓ NUEVO
├── api/db/models/
│   └── __init__.py ✓ ACTUALIZADO (agregado ComentarioPedidoModel)
├── DATABASE.md ✓ NUEVO
└── DATABASE_SETUP_SUMMARY.md ✓ NUEVO
```

## Estado del Proyecto

✓ Modelos SQLAlchemy: COMPLETOS (8 archivos, 12 modelos)
✓ Migración inicial: CREADA
✓ Seed data: COMPLETO (con datos realistas)
✓ Scripts helper: CREADOS
✓ Documentación: COMPLETA

**Todo listo para ejecutar `alembic upgrade head` y `python scripts/seed.py`**
