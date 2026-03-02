from __future__ import annotations

from typing import Protocol


class BlobStoragePort(Protocol):
    def upload_bytes_to_blob(self, blob_name: str, data: bytes, *, overwrite: bool = True) -> None: ...
    def download_blob_to_bytes(self, blob_name: str) -> bytes: ...
