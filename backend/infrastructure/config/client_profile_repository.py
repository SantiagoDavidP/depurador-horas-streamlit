from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from backend.domain.profiles.client_profiles import ClientProfile, ClientProfileManager

logger = logging.getLogger(__name__)


def default_profiles_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "client_profiles.json"


class JsonClientProfileRepository:
    def __init__(self, profiles_path: Optional[Path] = None) -> None:
        self._profiles_path = profiles_path or default_profiles_path()
        self._manager_cache: Optional[ClientProfileManager] = None

    @property
    def path(self) -> Path:
        return self._profiles_path

    def load_manager(self, force_reload: bool = False) -> ClientProfileManager:
        if self._manager_cache is not None and not force_reload:
            return self._manager_cache

        if not self._profiles_path.exists():
            logger.info(
                "Archivo de perfiles no encontrado en %s. Se utilizaran configuraciones vacias.",
                self._profiles_path,
            )
            self._manager_cache = ClientProfileManager()
            return self._manager_cache

        try:
            raw_data = json.loads(self._profiles_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.error("Archivo de perfiles invalido: %s", exc)
            self._manager_cache = ClientProfileManager()
            return self._manager_cache

        self._manager_cache = ClientProfileManager.from_payload(raw_data)
        return self._manager_cache

    def list_profiles(self):
        return self.load_manager().list_profiles()

    def get_profile(self, client_id: str):
        return self.load_manager().get_profile(client_id)

    def get_mapping(self, client_id: str):
        return self.load_manager().get_mapping(client_id)

    def save_profile(self, profile: ClientProfile) -> None:
        manager = self.load_manager()
        manager.save_profile(profile)
        self._profiles_path.parent.mkdir(parents=True, exist_ok=True)
        self._profiles_path.write_text(
            json.dumps(manager.to_payload(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._manager_cache = manager


@lru_cache(maxsize=1)
def get_client_profile_repository() -> JsonClientProfileRepository:
    return JsonClientProfileRepository()
