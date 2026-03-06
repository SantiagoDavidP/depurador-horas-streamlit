from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from backend.application.tabular.table_data import TableData


@dataclass(frozen=True)
class ParsedSheet:
    """Hoja preparada para ser procesada, independiente del origen."""

    dataframe: TableData
    header_row: int
    row_offset: int
    sheet_name: str
    metadata: Dict[str, object] = field(default_factory=dict)
