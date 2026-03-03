from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

from backend.application.batch.batch_processor import BatchFileResult


@dataclass
class StoredFile:
    id: str
    filename: str
    content_type: str
    data: bytes
    created_at: float


@dataclass
class StoredBatch:
    id: str
    created_at: float
    results: Sequence[BatchFileResult]
    source: str


_DOWNLOAD_STORE: Dict[str, StoredFile] = {}
_BATCH_STORE: Dict[str, StoredBatch] = {}
_MAX_FILES = 200
_MAX_BATCHES = 40


def _prune_store(store: Dict[str, object], max_items: int) -> None:
    if len(store) <= max_items:
        return
    items = sorted(
        store.items(),
        key=lambda kv: getattr(kv[1], "created_at", 0),
    )
    for key, _ in items[: max(0, len(items) - max_items)]:
        store.pop(key, None)


def store_file(data: bytes, filename: str, content_type: str) -> str:
    file_id = uuid.uuid4().hex
    _DOWNLOAD_STORE[file_id] = StoredFile(
        id=file_id,
        filename=filename,
        content_type=content_type,
        data=data,
        created_at=time.time(),
    )
    _prune_store(_DOWNLOAD_STORE, _MAX_FILES)
    return file_id


def get_file(file_id: str) -> Optional[StoredFile]:
    return _DOWNLOAD_STORE.get(file_id)


def store_batch(results: Sequence[BatchFileResult], source: str) -> str:
    batch_id = uuid.uuid4().hex
    _BATCH_STORE[batch_id] = StoredBatch(
        id=batch_id,
        created_at=time.time(),
        results=list(results),
        source=source,
    )
    _prune_store(_BATCH_STORE, _MAX_BATCHES)
    return batch_id


def get_batch(batch_id: str) -> Optional[StoredBatch]:
    return _BATCH_STORE.get(batch_id)
