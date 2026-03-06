from __future__ import annotations

from typing import Dict, Optional, Protocol

from backend.domain.rates.collaborator_rates import CollaboratorRate


class CollaboratorRatesPort(Protocol):
    def find_collaborator(self, name: str) -> Optional[CollaboratorRate]:
        ...

    def get_rate_for_collaborator(
        self,
        name: str,
        seniority_fallback: Optional[str] = None,
    ) -> Dict[str, object]:
        ...
