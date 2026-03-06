"""BONAPHARM - Pedidos y Devoluciones API.

FastAPI application entry point with:
- Health check endpoint (REQUIRED for Docker Compose healthcheck)
- CORS middleware
- Request logging middleware
- Global exception handlers
- All routers registered
- Lifespan for startup/shutdown
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import settings
from api.core.exceptions import register_exception_handlers
from api.core.middleware import RequestLoggingMiddleware
from api.db.base import engine

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bonapharm")


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    logger.info(
        "Starting %s v%s (env=%s)",
        settings.APP_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )

    # On startup: create tables if in development mode
    if settings.ENVIRONMENT == "development":
        from api.db.base import Base

        # Import all models so they are registered with Base.metadata
        import api.db.models  # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created (development mode)")

    yield

    # On shutdown
    logger.info("Shutting down %s", settings.APP_NAME)
    await engine.dispose()


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "API REST para gestion automatizada de pedidos, devoluciones, "
        "comisiones e integracion SAP"
    ),
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
register_exception_handlers(app)


# ---------------------------------------------------------------------------
# Health check -- MUST be BEFORE any router inclusion
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"], response_model=dict[str, Any])
async def health_check() -> dict[str, Any]:
    """Health check endpoint.

    Must respond WITHOUT database access.
    Used by Docker Compose healthcheck, load balancers, and validator_agent.
    """
    return {
        "status": "ok",
        "service": "bonapharm-api",
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "BONAPHARM - API de Pedidos y Devoluciones",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
    }


# ---------------------------------------------------------------------------
# Import and register all routers
# ---------------------------------------------------------------------------
from api.routers.auth import router as auth_router  # noqa: E402
from api.routers.users import router as users_router  # noqa: E402
from api.routers.users import roles_router  # noqa: E402
from api.routers.pedidos import router as pedidos_router  # noqa: E402
from api.routers.devoluciones import router as devoluciones_router  # noqa: E402
from api.routers.comisiones import router as comisiones_router  # noqa: E402
from api.routers.productos import router as productos_router  # noqa: E402
from api.routers.productos import clients_router  # noqa: E402
from api.routers.dashboard import router as dashboard_router  # noqa: E402
from api.routers.sap import router as sap_router  # noqa: E402
from api.routers.notificaciones import router as notificaciones_router  # noqa: E402
from api.routers.config_admin import router as config_router  # noqa: E402
from api.routers.audit import router as audit_router  # noqa: E402

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(pedidos_router)
app.include_router(devoluciones_router)
app.include_router(comisiones_router)
app.include_router(productos_router)
app.include_router(clients_router)
app.include_router(dashboard_router)
app.include_router(sap_router)
app.include_router(notificaciones_router)
app.include_router(config_router)
app.include_router(audit_router)
