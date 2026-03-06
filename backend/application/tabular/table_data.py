from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class TableData:
    columns: Tuple[Any, ...]
    rows: Tuple[Tuple[Any, ...], ...]
    attrs: Dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def empty(self) -> bool:
        return len(self.rows) == 0
