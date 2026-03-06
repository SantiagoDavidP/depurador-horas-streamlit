# Arquitectura del Sistema

## Visión General

Sistema de automatización de pedidos y devoluciones para BONAPHARM, implementado con arquitectura de tres capas y patrón de microservicios.

## Stack Tecnológico

### Frontend
- **Framework**: React 18 con TypeScript
- **Build Tool**: Vite
- **Estilos**: Tailwind CSS
- **Estado**: Zustand
- **Formularios**: React Hook Form + Zod
- **Testing**: Vitest + React Testing Library

### Backend
- **Framework**: FastAPI (Python 3.11)
- **ORM**: SQLAlchemy 2.0 (async)
- **Migraciones**: Alembic
- **Validación**: Pydantic v2
- **Testing**: pytest + pytest-asyncio

### Base de Datos
- **Principal**: PostgreSQL 16
- **Conexión**: asyncpg (driver async)

### Infraestructura
- **Containerización**: Docker + Docker Compose
- **CI/CD**: TBD
- **Monitoreo**: TBD

## Arquitectura de Capas

### Capa de Presentación (Frontend)
```
src/
├── components/    # Componentes reutilizables
├── pages/         # Vistas principales
├── hooks/         # Custom hooks
├── services/      # Clientes API
├── store/         # Estado global
└── types/         # Tipos TypeScript
```

### Capa de Aplicación (Backend)
```
api/
├── routers/       # Endpoints HTTP
├── services/      # Lógica de negocio
├── repositories/  # Acceso a datos
├── models/        # Modelos Pydantic
└── core/          # Configuración
```

### Capa de Datos
```
api/db/
├── models/        # Modelos SQLAlchemy
├── session.py     # Gestión de sesiones
└── base.py        # Base declarativa
```

## Patrones de Diseño

### Repository Pattern
Separación entre lógica de negocio y acceso a datos.

### Dependency Injection
FastAPI maneja dependencias automáticamente.

### DTO Pattern
Modelos Pydantic para request/response.

## Flujo de Datos

1. **Request** → Router → Service → Repository → Database
2. **Response** → Database → Repository → Service → Router → Response Model

## Seguridad

- Autenticación: Microsoft Entra ID (Azure AD)
- Autorización: RBAC con roles
- Tokens: JWT (access + refresh)
- Comunicación: HTTPS/TLS 1.2+
- CORS: Configurado en FastAPI

## Integraciones Externas

- **SAP API**: Inventario y facturación
- **Dataverse**: Sincronización de datos
- **SharePoint**: Almacenamiento de documentos
- **Power BI**: Reportes y dashboards

## Escalabilidad

- Base de datos: Conexiones async con pool
- Backend: Stateless, escala horizontalmente
- Frontend: Build estático, CDN ready
- Cache: Redis (futura implementación)

## Monitoreo y Logging

- Health checks en `/health`
- Logs estructurados (JSON)
- Métricas de performance (futuro)
- Error tracking (futuro)
