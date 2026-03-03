from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ColumnMapping:
    date: str
    hours: str
    description: str
    project: Optional[str] = None
