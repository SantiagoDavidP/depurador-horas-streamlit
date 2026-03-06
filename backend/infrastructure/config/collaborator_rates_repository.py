from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from backend.domain.rates.collaborator_rates import CollaboratorRatesManager

logger = logging.getLogger(__name__)


def default_collaborator_rates_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "collaborator_rates.json"


class JsonCollaboratorRatesRepository:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._config_path = config_path or default_collaborator_rates_path()
        self._manager_cache: Optional[CollaboratorRatesManager] = None

    @property
    def path(self) -> Path:
        return self._config_path

    def load_manager(self, force_reload: bool = False) -> CollaboratorRatesManager:
        if self._manager_cache is not None and not force_reload:
            return self._manager_cache

        if not self._config_path.exists():
            logger.warning(
                "Collaborator rates file not found: %s. Using seniority defaults only.",
                self._config_path,
            )
            self._manager_cache = CollaboratorRatesManager()
            return self._manager_cache

        try:
            with self._config_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in collaborator rates file: %s", exc)
            self._manager_cache = CollaboratorRatesManager()
            return self._manager_cache
        except Exception as exc:
            logger.error("Error loading collaborator rates: %s", exc)
            self._manager_cache = CollaboratorRatesManager()
            return self._manager_cache

        self._manager_cache = CollaboratorRatesManager.from_payload(data)
        return self._manager_cache


@lru_cache(maxsize=1)
def get_collaborator_rates_manager() -> CollaboratorRatesManager:
    return JsonCollaboratorRatesRepository().load_manager()
