from __future__ import annotations

import logging
from io import BytesIO
from typing import Optional

from azure.core.exceptions import AzureError
from azure.storage.blob import BlobClient, BlobServiceClient

from config.settings import get_settings

logger = logging.getLogger(__name__)

_BLOB_SERVICE_CLIENT: Optional[BlobServiceClient] = None


def _build_blob_service_client() -> BlobServiceClient:
    settings = get_settings()
    storage_cfg = settings.azure_storage

    if storage_cfg.connection_string:
        return BlobServiceClient.from_connection_string(storage_cfg.connection_string)

    if storage_cfg.account_url and storage_cfg.credential:
        return BlobServiceClient(account_url=storage_cfg.account_url, credential=storage_cfg.credential)

    raise RuntimeError(
        "Azure Storage no está configurado. Defina AZURE_STORAGE_CONNECTION_STRING o (AZURE_STORAGE_ACCOUNT_URL y "
        "AZURE_STORAGE_ACCOUNT_KEY/SAS)."
    )


def _get_blob_service_client() -> BlobServiceClient:
    global _BLOB_SERVICE_CLIENT
    if _BLOB_SERVICE_CLIENT is None:
        _BLOB_SERVICE_CLIENT = _build_blob_service_client()
    return _BLOB_SERVICE_CLIENT


def _get_blob_client(blob_name: str) -> BlobClient:
    settings = get_settings()
    container = settings.azure_storage.container
    if not container:
        raise RuntimeError("Falta definir AZURE_STORAGE_CONTAINER.")
    service_client = _get_blob_service_client()
    return service_client.get_blob_client(container=container, blob=blob_name)


def download_blob_to_bytes(blob_name: str) -> bytes:
    """Download a blob and return its contents as bytes."""
    try:
        blob_client = _get_blob_client(blob_name)
        stream = BytesIO()
        download_stream = blob_client.download_blob()
        download_stream.readinto(stream)
        logger.info("Blob '%s' downloaded successfully (%d bytes).", blob_name, stream.tell())
        return stream.getvalue()
    except AzureError as exc:
        logger.exception("Azure Blob download failed for '%s': %s", blob_name, exc)
        raise


def upload_bytes_to_blob(blob_name: str, data: bytes, *, overwrite: bool = True) -> None:
    """Upload bytes to a blob."""
    try:
        blob_client = _get_blob_client(blob_name)
        blob_client.upload_blob(data, overwrite=overwrite)
        logger.info("Blob '%s' uploaded successfully.", blob_name)
    except AzureError as exc:
        logger.exception("Azure Blob upload failed for '%s': %s", blob_name, exc)
        raise