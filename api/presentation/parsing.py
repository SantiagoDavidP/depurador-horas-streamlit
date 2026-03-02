from __future__ import annotations

import json
from typing import Dict, Optional

from fastapi import HTTPException

from api.serializers import sanitize_payload

_SAFE_META_KEYS = (
    "company",
    "employee",
    "empleado",
    "period_start",
    "period_end",
    "month_name",
    "year",
    "report_date",
    "period_source",
    "metadata_warning",
    "baninter_report",
    "llm_enabled",
    "llm_corrections_count",
)


def parse_payload(payload: Optional[str]) -> Dict[str, object]:
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc


def to_bool(value: object, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
    return bool(value)


def compact_metadata(raw_meta: Optional[Dict[str, object]]) -> Dict[str, object]:
    meta = raw_meta or {}
    compact = {key: meta.get(key) for key in _SAFE_META_KEYS if key in meta}
    return sanitize_payload(compact)
