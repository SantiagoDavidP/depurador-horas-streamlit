from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.domain.models import ColumnMapping

logger = logging.getLogger(__name__)


@dataclass
class ClientProfile:
    """Perfil reutilizable que agrupa configuraciones y mapeo por cliente."""

    client_id: str
    name: str
    mapping: Dict[str, str]
    settings: Dict[str, object]
    keywords: List[str] = field(default_factory=list)
    company_aliases: List[str] = field(default_factory=list)

    def to_column_mapping(self) -> Optional[ColumnMapping]:
        """Convierte la definicion del perfil en un ColumnMapping validado."""
        required = {"date", "hours", "description"}
        missing = required - self.mapping.keys()
        if missing:
            logger.warning(
                "Perfil %s incompleto, faltan columnas obligatorias: %s",
                self.client_id,
                ", ".join(sorted(missing)),
            )
            return None
        return ColumnMapping(
            date=self.mapping["date"],
            hours=self.mapping["hours"],
            description=self.mapping["description"],
            project=self.mapping.get("project"),
        )


class ClientProfileManager:
    """Administra perfiles de clientes ya cargados en memoria."""

    def __init__(self, profiles: Optional[Dict[str, ClientProfile]] = None) -> None:
        self._profiles_cache: Dict[str, ClientProfile] = dict(profiles or {})

    @classmethod
    def from_payload(cls, raw_data: Dict[str, object]) -> "ClientProfileManager":
        profiles: Dict[str, ClientProfile] = {}
        for client_id, payload_obj in raw_data.items():
            if not isinstance(payload_obj, dict):
                continue
            payload = payload_obj
            mapping = (
                payload.get("mapeo_columnas")
                or payload.get("mapeo")
                or payload.get("mapping")
                or {}
            )
            base_settings = (
                payload.get("configuraciones")
                or payload.get("config")
                or {}
            )
            extra_settings = {
                key: payload[key]
                for key in (
                    "rol_default",
                    "horas_esperadas_dia",
                    "duplicate_similarity_threshold",
                    "duplicate_min_occurrences",
                    "hours_tolerance_factor",
                    "correct_spelling",
                )
                if key in payload
            }
            combined_settings = {**base_settings, **extra_settings}
            keywords = payload.get("keywords") or combined_settings.get("keywords") or []
            company_aliases = payload.get("company_aliases") or combined_settings.get("company_aliases") or []
            profiles[str(client_id)] = ClientProfile(
                client_id=str(client_id),
                name=str(payload.get("nombre") or payload.get("name") or client_id),
                mapping={
                    key: str(value)
                    for key, value in dict(mapping).items()
                    if value is not None
                },
                settings=dict(combined_settings),
                keywords=[str(item).lower() for item in keywords],
                company_aliases=[str(item).lower() for item in company_aliases],
            )
        return cls(profiles)

    def to_payload(self) -> Dict[str, object]:
        return {
            pid: {
                "nombre": p.name,
                "mapeo_columnas": p.mapping,
                **({"configuraciones": p.settings} if p.settings else {}),
                "keywords": p.keywords,
                "company_aliases": p.company_aliases,
            }
            for pid, p in self._profiles_cache.items()
        }

    def load_profiles(self, force_reload: bool = False) -> Dict[str, ClientProfile]:
        return self._profiles_cache

    def list_profiles(self) -> List[ClientProfile]:
        return list(self._profiles_cache.values())

    def get_profile(self, client_id: str) -> Optional[ClientProfile]:
        return self._profiles_cache.get(client_id)

    def get_mapping(self, client_id: str) -> Optional[ColumnMapping]:
        profile = self.get_profile(client_id)
        if profile is None:
            return None
        return profile.to_column_mapping()

    def save_profile(self, profile: ClientProfile) -> None:
        self._profiles_cache[profile.client_id] = profile
