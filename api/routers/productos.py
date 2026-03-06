"""Productos router -- 6 endpoints.

GET    /api/products                      List products
GET    /api/products/{id}                 Get product detail
POST   /api/products                      Create product (admin)
PUT    /api/products/{id}                 Update product (admin)
GET    /api/clients/search                Search client by RUC in SAP
"""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from api.core.dependencies import CurrentUser, OnlyAdmin, SessionDep
from api.db.models.producto import ProductoModel
from api.models.common import PaginatedResponse
from api.models.producto import ProductoCreate, ProductoResponse, ProductoUpdate
from api.repositories.producto_repository import ProductoRepository
from api.services.sap_service import SAPService

router = APIRouter(prefix="/api/products", tags=["productos"])
clients_router = APIRouter(prefix="/api/clients", tags=["clientes"])


def _get_repo(db: SessionDep) -> ProductoRepository:
    return ProductoRepository(db)


# ------------------------------------------------------------------
# GET /api/products
# ------------------------------------------------------------------
@router.get("/", response_model=PaginatedResponse[ProductoResponse])
async def list_products(
    user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    distribuidor: Optional[str] = None,
    molecula: Optional[str] = None,
    search: Optional[str] = None,
    repo: ProductoRepository = Depends(_get_repo),
) -> PaginatedResponse[ProductoResponse]:
    """List products with filters and pagination."""
    items = await repo.get_multi(
        skip=skip, limit=limit,
        distribuidor=distribuidor,
        molecula=molecula,
        search=search,
    )
    total = await repo.count(
        distribuidor=distribuidor,
        molecula=molecula,
        search=search,
    )
    return PaginatedResponse(
        items=[ProductoResponse.model_validate(p) for p in items],
        total=total,
        skip=skip,
        limit=limit,
    )


# ------------------------------------------------------------------
# GET /api/products/{id}
# ------------------------------------------------------------------
@router.get("/{product_id}", response_model=ProductoResponse)
async def get_product(
    product_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    repo: ProductoRepository = Depends(_get_repo),
) -> ProductoResponse:
    """Get product detail including price, stock, distribuidor."""
    producto = await repo.get(product_id)
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    return ProductoResponse.model_validate(producto)


# ------------------------------------------------------------------
# POST /api/products
# ------------------------------------------------------------------
@router.post("/", response_model=ProductoResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductoCreate,
    admin: OnlyAdmin,
    repo: ProductoRepository = Depends(_get_repo),
) -> ProductoResponse:
    """Create a new product (admin only)."""
    existing = await repo.get_by_codigo_sap(data.codigo_sap)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un producto con codigo SAP {data.codigo_sap}",
        )
    producto = ProductoModel(**data.model_dump())
    producto = await repo.create(producto)
    return ProductoResponse.model_validate(producto)


# ------------------------------------------------------------------
# PUT /api/products/{id}
# ------------------------------------------------------------------
@router.put("/{product_id}", response_model=ProductoResponse)
async def update_product(
    product_id: Annotated[uuid.UUID, Path()],
    data: ProductoUpdate,
    admin: OnlyAdmin,
    repo: ProductoRepository = Depends(_get_repo),
) -> ProductoResponse:
    """Update a product (admin only)."""
    producto = await repo.get(product_id)
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return ProductoResponse.model_validate(producto)
    producto = await repo.update(producto, update_data)
    return ProductoResponse.model_validate(producto)


# ------------------------------------------------------------------
# GET /api/clients/search?ruc={ruc}
# ------------------------------------------------------------------
@clients_router.get("/search")
async def search_client(
    user: CurrentUser,
    ruc: Annotated[str, Query(min_length=11, max_length=11, pattern=r"^\d{11}$")],
) -> dict:
    """Search client by RUC in SAP, returns razon social and data."""
    sap = SAPService()
    result = await sap.get_client_by_ruc(ruc)
    return result
