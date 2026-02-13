from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class PerfCollector:
    entries: List[Tuple[str, float]] = field(default_factory=list)

    def add(self, name: str, duration: float) -> None:
        self.entries.append((name, duration))

    def top(self, n: int = 10) -> List[Tuple[str, float]]:
        return sorted(self.entries, key=lambda x: x[1], reverse=True)[:n]
