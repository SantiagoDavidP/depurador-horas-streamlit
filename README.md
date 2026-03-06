# BONAPHARM - Sistema de Pedidos y Devoluciones

Sistema de automatización y optimización de procesos de toma y aprobación de pedidos, cálculo de comisiones y recuperos, y gestión de devoluciones para BONAPHARM DEL PERU.

## Inicio Rápido

### Con Make (Recomendado)

```bash
# Ver todos los comandos disponibles
make help

# Levantar entorno de desarrollo completo
make dev
```

### Manual

```bash
# 1. Variables de entorno
cp .env.development .env

# 2. Levantar base de datos
docker-compose up -d db

# 3. Backend (en una terminal)
pip install -r api/requirements.txt
alembic upgrade head
uvicorn api.main:app --reload --port 8000

# 4. Frontend (en otra terminal)
npm install
npm run dev
```

### Con Docker Compose (Todo en uno)

```bash
# Levantar stack completo
make docker-up

# O manualmente
docker-compose up --build
```

## URLs

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

## Tests

```bash
make test          # Todos los tests
make test-fe       # Frontend (Vitest)
make test-be       # Backend (pytest)
make test-coverage # Con cobertura
```

## Stack Tecnológico

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic
- **Base de datos**: PostgreSQL 16
- **Tests**: Vitest + React Testing Library (FE), pytest + httpx (BE)
- **Infraestructura**: Docker, Docker Compose

## Estructura del Proyecto

```
DemoEnd2End/
├── api/                      # Backend FastAPI
│   ├── routers/             # Endpoints de la API
│   ├── models/              # Modelos Pydantic
│   ├── services/            # Lógica de negocio
│   ├── repositories/        # Acceso a datos
│   ├── db/                  # Configuración de base de datos
│   ├── core/                # Configuración y seguridad
│   └── main.py              # Punto de entrada
├── src/                      # Frontend React
│   ├── components/          # Componentes reutilizables
│   ├── pages/               # Páginas/vistas
│   ├── hooks/               # Custom hooks
│   ├── services/            # API clients
│   ├── store/               # Estado global (Zustand)
│   ├── types/               # TypeScript types
│   └── utils/               # Utilidades
├── tests/                    # Tests
│   ├── frontend/            # Tests de React/Vitest
│   └── backend/             # Tests de pytest
├── alembic/                  # Migraciones de base de datos
├── docker/                   # Dockerfiles
├── scripts/                  # Scripts de utilidad
├── docs/                     # Documentación
├── design/                   # Diseños y mockups
└── docker-compose.yml
```

## Módulos Principales

### 1. Registro de Pedidos
- Registro de solicitudes de venta por vendedores
- Cálculo automático de totales y bonificaciones
- Validación según distribuidores (Dimexa/Quimica)

### 2. Aprobación de Pedidos
- Revisión y aprobación por administradores comerciales
- Notificaciones automáticas a distribuidores
- Integración con SAP

### 3. Gestión de Devoluciones
- Registro de devoluciones de productos
- Valorización automática
- Workflow de aprobación

### 4. Cálculo de Comisiones
- Cálculo automático mensual
- Diferenciación por distribuidor (10% Dimexa, 13% Quimica)
- Generación de reportes

## Modelos de Datos

- **Pedido**: Solicitudes de venta
- **DetallePedido**: Líneas de productos en pedidos
- **Devolucion**: Solicitudes de devolución
- **Producto**: Catálogo de productos
- **Comision**: Cálculo de comisiones por distribuidor

## Variables de Entorno

Ver `.env.example` para la lista completa de variables requeridas.

Las principales son:
- `DATABASE_URL`: Conexión a PostgreSQL
- `SECRET_KEY`: Clave secreta para tokens JWT
- `ENTRA_ID_*`: Credenciales de Microsoft Entra ID (Azure AD)
- `SAP_API_*`: Configuración de API de SAP
- `DATAVERSE_ENVIRONMENT_URL`: URL del entorno Dataverse

## Comandos Útiles

```bash
# Desarrollo
make dev                    # Levantar entorno local
make build                  # Build de producción

# Tests
make test                   # Ejecutar todos los tests
make test-fe                # Tests de frontend
make test-be                # Tests de backend
make test-coverage          # Tests con cobertura

# Base de datos
make migrate                # Aplicar migraciones
make migrate-create         # Crear nueva migración
make seed                   # Cargar datos de prueba

# Docker
make docker-up              # Levantar containers
make docker-down            # Parar containers
make docker-logs            # Ver logs

# Limpieza
make clean                  # Limpiar archivos temporales
```

## Desarrollo

### Agregar un nuevo endpoint

1. Crear el router en `api/routers/`
2. Definir los modelos Pydantic en `api/models/`
3. Implementar la lógica en `api/services/`
4. Registrar el router en `api/main.py`
5. Crear tests en `tests/backend/`

### Agregar un nuevo componente

1. Crear el componente en `src/components/`
2. Definir los tipos en `src/types/`
3. Crear tests en `tests/frontend/components/`
4. Actualizar mocks en `tests/frontend/mocks/handlers.ts`

## Seguridad

- Autenticación con Microsoft Entra ID (Azure AD)
- OAuth 2.0 y OpenID Connect
- Soporte para MFA
- Cifrado AES-256 y TLS 1.2+
- RBAC con roles y permisos

## Requerimientos

- Node.js 20+
- Python 3.11+
- PostgreSQL 16+
- Docker y Docker Compose (opcional)

## Licencia

Propietario - BONAPHARM DEL PERU

## Soporte

Para problemas o preguntas, contactar al equipo de desarrollo.
