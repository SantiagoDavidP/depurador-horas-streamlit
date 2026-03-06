"""SAP integration router -- 6 endpoints.

GET    /api/sap/inventory               Query SAP inventory
GET    /api/sap/clients/{ruc}           Query client by RUC
POST   /api/sap/orders/{orderId}/sync   Sync order to SAP
GET    /api/sap/invoices                Query invoices
GET    /api/sap/products/sync           Sync product catalog
POST   /api/sap/returns/{returnId}/sync Sync return to SAP
"""

import uuid
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, Path, Query

from api.core.dependencies import AdminOrFinanzas, CurrentUser, OnlyAdmin, SessionDep
from api.repositories.producto_repository import ProductoRepository
from api.services.sap_service import SAPService

router = APIRouter(prefix="/api/sap", tags=["sap"])


def _get_sap_service() -> SAPService:
    return SAPService()


# ------------------------------------------------------------------
# GET /api/sap/inventory
# ------------------------------------------------------------------
@router.get("/inventory")
async def get_inventory(
    user: CurrentUser,
    sap: SAPService = Depends(_get_sap_service),
) -> dict[str, Any]:
    """Query inventory from SAP (stock, lots, prices)."""
    return await sap.get_inventory()


# ------------------------------------------------------------------
# GET /api/sap/clients/{ruc}
# ------------------------------------------------------------------
@router.get("/clients/{ruc}")
async def get_client(
    user: CurrentUser,
    ruc: Annotated[str, Path(min_length=11, max_length=11, pattern=r"^\d{11}$")],
    sap: SAPService = Depends(_get_sap_service),
) -> dict[str, Any]:
    """Query client information by RUC from SAP."""
    return await sap.get_client_by_ruc(ruc)


# ------------------------------------------------------------------
# POST /api/sap/orders/{orderId}/sync
# ------------------------------------------------------------------
@router.post("/orders/{order_id}/sync")
async def sync_order(
    order_id: Annotated[uuid.UUID, Path()],
    user: AdminOrFinanzas,
    sap: SAPService = Depends(_get_sap_service),
) -> dict[str, Any]:
    """Send an approved order to SAP for invoicing."""
    return await sap.sync_order(str(order_id), {"order_id": str(order_id)})


# ------------------------------------------------------------------
# GET /api/sap/invoices
# ------------------------------------------------------------------
@router.get("/invoices")
async def get_invoices(
    user: CurrentUser,
    pedido_id: Optional[uuid.UUID] = None,
    sap: SAPService = Depends(_get_sap_service),
) -> dict[str, Any]:
    """Query invoices associated with an order."""
    pid = str(pedido_id) if pedido_id else ""
    return await sap.get_invoices(pid)


# ------------------------------------------------------------------
# GET /api/sap/products/sync
# ------------------------------------------------------------------
@router.get("/products/sync")
async def sync_products(
    db: SessionDep,
    user: OnlyAdmin,
    sap: SAPService = Depends(_get_sap_service),
) -> dict[str, Any]:
    """Synchronize product catalog from SAP to local database.

    For each product in the SAP response, creates or updates the
    local ProductoModel.
    """
    data = await sap.sync_products()
    items = data.get("items", [])
    repo = ProductoRepository(db)
    created = 0
    updated = 0
    for item in items:
        codigo_sap = item.get("codigo_sap", "")
        if not codigo_sap:
            continue
        existing = await repo.get_by_codigo_sap(codigo_sap)
        product_data = {
            "nombre": item.get("nombre", ""),
            "molecula": item.get("molecula", ""),
            "precio_vvf": float(item.get("precio_vvf", 0)),
            "precio_compra": float(item.get("precio_compra", 0)),
            "distribuidor": item.get("distribuidor", ""),
            "stock_disponible": int(item.get("stock", 0)),
        }
        if existing:
            await repo.update(existing, product_data)
            updated += 1
        else:
            from api.db.models.producto import ProductoModel
            producto = ProductoModel(codigo_sap=codigo_sap, **product_data)
            await repo.create(producto)
            created += 1

    return {
        "message": "Sincronizacion completada",
        "created": created,
        "updated": updated,
        "total_items": len(items),
    }


# ------------------------------------------------------------------
# POST /api/sap/returns/{returnId}/sync
# ------------------------------------------------------------------
@router.post("/returns/{return_id}/sync")
async def sync_return(
    return_id: Annotated[uuid.UUID, Path()],
    user: AdminOrFinanzas,
    sap: SAPService = Depends(_get_sap_service),
) -> dict[str, Any]:
    """Send an approved return to SAP."""
    return await sap.sync_return(str(return_id), {"return_id": str(return_id)})
