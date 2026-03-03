from __future__ import annotations

from backend.infrastructure.storage import azure_storage


class AzureBlobStorageAdapter:
    def upload_bytes_to_blob(self, blob_name: str, data: bytes, *, overwrite: bool = True) -> None:
        azure_storage.upload_bytes_to_blob(blob_name, data, overwrite=overwrite)

    def download_blob_to_bytes(self, blob_name: str) -> bytes:
        return azure_storage.download_blob_to_bytes(blob_name)
