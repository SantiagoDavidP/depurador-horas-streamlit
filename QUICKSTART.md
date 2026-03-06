# Guia de Inicio Rapido

> Validado por el agente validator. Si sigues estos pasos en orden, el proyecto arranca a la primera.

## Prerequisitos

- Node.js 20+ (`node --version`)
- Python 3.10+ (`python --version`)
- Docker y Docker Compose (`docker --version`)

## Opcion A: Desarrollo Local (Recomendado)

### 1. Variables de entorno

```bash
cp .env.example .env
# Edita .env con tus valores reales (base de datos, secretos, etc.)
```

### 2. Base de datos con Docker

```bash
docker-compose up -d db
# Esperar ~5 segundos a que PostgreSQL este listo
```

### 3. Backend

```bash
# Instalar dependencias
pip install -r api/requirements.txt

# Ejecutar migraciones
alembic upgrade head

# Arrancar servidor (puerto 8000)
uvicorn api.main:app --reload --port 8000
```

### 4. Frontend (en nueva terminal)

```bash
# Instalar dependencias
npm install

# Arrancar servidor de desarrollo (puerto 5173)
npm run dev
```

### URLs

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |

---

## Opcion B: Docker Completo

```bash
cp .env.example .env
# Editar .env con tus valores

docker-compose up --build
```

---

## Opcion C: Makefile

```bash
make dev          # Levanta todo en modo desarrollo
make build        # Build de produccion
make test         # Ejecuta todos los tests
make test-fe      # Tests de frontend (Vitest)
make test-be      # Tests de backend (pytest)
make docker-up    # Levanta con Docker
make docker-down  # Para Docker Compose
make lint         # Ejecuta linters
make clean        # Limpia archivos temporales
```

---

## Tests

```bash
# Frontend
npx vitest run --reporter=verbose

# Backend
python -m pytest tests/backend/ -v

# Cobertura
npx vitest run --coverage
python -m pytest tests/backend/ --cov=api --cov-report=term-missing
```

---

## Estructura del Proyecto

```
DemoEnd2End/
  api/                    # Backend FastAPI
    core/                 # Config, security, middleware, dependencies
    db/                   # SQLAlchemy engine, Base, models
    models/               # Pydantic schemas (request/response)
    repositories/         # Data access layer
    routers/              # API endpoints
    services/             # Business logic
    main.py               # FastAPI app entry point
  src/                    # Frontend React + TypeScript
    components/           # UI components
    pages/                # Page components
    hooks/                # Custom React hooks
    services/             # API client services
    store/                # Zustand state management
    types/                # TypeScript type definitions
  tests/
    backend/              # pytest async tests
    frontend/             # Vitest + RTL tests
  docker/                 # Dockerfiles
  alembic/                # Database migrations
  docker-compose.yml      # Full stack orchestration
```

---

## API Endpoints Principales

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /api/auth/login | Login con email/password |
| POST | /api/auth/login/microsoft | Login SSO Microsoft Entra |
| GET | /api/auth/me | Usuario actual |
| POST | /api/auth/refresh-token | Renovar token |
| GET | /api/orders/ | Listar pedidos |
| POST | /api/orders/ | Crear pedido |
| GET | /api/products/ | Listar productos |
| GET | /api/returns/ | Listar devoluciones |
| POST | /api/returns/ | Crear devolucion |
| GET | /api/commissions/ | Listar comisiones |
| POST | /api/commissions/calculate | Calcular comisiones |
| GET | /api/dashboard/vendedor/{id} | Dashboard vendedor |
| GET | /api/dashboard/gerencia | Dashboard gerencia |
| GET | /api/users/ | Listar usuarios |
| GET | /api/roles/ | Listar roles |

---

## Solucion de Problemas

| Error | Solucion |
|-------|----------|
| `connection refused :5432` | Ejecutar `docker-compose up -d db` primero |
| `ModuleNotFoundError` | Ejecutar `pip install -r api/requirements.txt` |
| `Cannot find module` | Ejecutar `npm install` |
| Puerto 8000 en uso | `lsof -i :8000` (Linux/Mac) o `netstat -ano \| findstr 8000` (Windows) |
| Puerto 5173 en uso | `lsof -i :5173` (Linux/Mac) o `netstat -ano \| findstr 5173` (Windows) |
| `pool_size invalid for SQLite` | El backend detecta SQLite automaticamente y omite pool params |
| `.env not found` en Docker | Ejecutar `cp .env.example .env` antes de `docker-compose up` |
| Error de migraciones | `alembic current` para verificar estado, `alembic upgrade head` para aplicar |

---

## URLs de Referencia

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## Ayuda Adicional

- README completo: [README.md](./README.md)
- Guia de desarrollo: [docs/development.md](./docs/development.md)
- Arquitectura: [docs/architecture.md](./docs/architecture.md)
- API: [docs/api.md](./docs/api.md)
