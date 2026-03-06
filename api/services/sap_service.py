"""SAP integration service -- HTTP client for external SAP API.

Handles:
- Inventory synchronization
- Client lookup by RUC
- Order sync to SAP
- Invoice queries
- Product catalog sync
- Return sync
"""

from __future__ import annotations


import logging
from typing import Any, Optional

import httpx

from api.core.config import settings
from api.core.exceptions import BadRequestException

logger = logging.getLogger("bonapharm.sap_service")

_MAX_RETRIES = 3
_TIMEOUT_SECONDS = 10.0


class SAPService:
    """Async HTTP client wrapper for the SAP REST API."""

    def __init__(self) -> None:
        self.base_url = settings.SAP_API_BASE_URL
        self.api_key = settings.SAP_API_KEY
        self._headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        """Create a new httpx async client for each call."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=_TIMEOUT_SECONDS,
        )

    async def _request_with_retries(
        self,
        method: str,
        path: str,
        json_body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request with exponential-backoff retries."""
        import asyncio

        last_exc: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with self._client() as client:
                    response = await client.request(method, path, json=json_body)
                    response.raise_for_status()
                    return response.json()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning(
                    "SAP request %s %s failed (attempt %d/%d): %s -- retrying in %ds",
                    method, path, attempt + 1, _MAX_RETRIES, exc, wait,
                )
                await asyncio.sleep(wait)

        logger.error("SAP request %s %s failed after %d retries", method, path, _MAX_RETRIES)
        raise BadRequestException(
            f"Error de comunicacion con SAP: {last_exc}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_inventory(self) -> dict[str, Any]:
        """GET /api/sap/inventory -- query stock, lots, prices from SAP."""
        if not self.base_url:
            logger.warning("SAP_API_BASE_URL not configured; returning mock data")
            return {"items": []}
        return await self._request_with_retries("GET", "/inventory")

    async def get_client_by_ruc(self, ruc: str) -> dict[str, Any]:
        """GET /api/sap/clients/{ruc} -- lookup client by RUC."""
        if not self.base_url:
            return {"ruc": ruc, "razon_social": "Cliente de prueba", "direccion": ""}
        return await self._request_with_retries("GET", f"/clients/{ruc}")

    async def sync_order(self, order_id: str, order_data: dict[str, Any]) -> dict[str, Any]:
        """POST /api/sap/orders/{orderId}/sync -- send approved order to SAP."""
        if not self.base_url:
            logger.info("SAP sync skipped (not configured) for order %s", order_id)
            return {"success": True, "sap_id": "MOCK-SAP-001"}
        return await self._request_with_retries(
            "POST", f"/orders/{order_id}/sync", json_body=order_data
        )

    async def get_invoices(self, pedido_id: str) -> dict[str, Any]:
        """GET /api/sap/invoices?pedido_id={pedidoId}."""
        if not self.base_url:
            return {"invoices": []}
        return await self._request_with_retries(
            "GET", f"/invoices?pedido_id={pedido_id}"
        )

    async def sync_products(self) -> dict[str, Any]:
        """GET /api/sap/products/sync -- fetch product catalog from SAP."""
        if not self.base_url:
            return {"items": []}
        return await self._request_with_retries("GET", "/products/sync")

    async def sync_return(self, return_id: str, return_data: dict[str, Any]) -> dict[str, Any]:
        """POST /api/sap/returns/{returnId}/sync -- send approved return to SAP."""
        if not self.base_url:
            logger.info("SAP return sync skipped for %s", return_id)
            return {"success": True}
        return await self._request_with_retries(
            "POST", f"/returns/{return_id}/sync", json_body=return_data
        )
