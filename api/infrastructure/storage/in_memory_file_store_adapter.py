from __future__ import annotations

from typing import Sequence

from api.storage import get_batch, get_file, store_batch, store_file
from backend.batch_processor import BatchFileResult


class InMemoryFileStoreAdapter:
    def store_file(self, data: bytes, filename: str, content_type: str) -> str:
        return store_file(data, filename, content_type)

    def get_file(self, file_id: str):
        return get_file(file_id)

    def store_batch(self, results: Sequence[BatchFileResult], source: str) -> str:
        return store_batch(results, source)

    def get_batch(self, batch_id: str):
        return get_batch(batch_id)
