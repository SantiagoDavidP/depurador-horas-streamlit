from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from backend.domain.models import ColumnMapping

logger = logging.getLogger(__name__)


def _default_profiles_path() -> Path:
    # Conserva la ruta original del repositorio: <repo>/config/client_profiles.json
    return Path(__file__).resolve().parents[3] / "config" / "client_profiles.json"


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
        """Convierte la definici�n del perfil en un ColumnMapping validado."""
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
    """Administra persistencia y recuperaci�n de perfiles de clientes."""

    def __init__(self, profiles_path: Optional[Path] = None) -> None:
        self._profiles_path = profiles_path or _default_profiles_path()
        self._profiles_cache: Optional[Dict[str, ClientProfile]] = None

    @property
    def path(self) -> Path:
        return self._profiles_path

    def load_profiles(self, force_reload: bool = False) -> Dict[str, ClientProfile]:
        if self._profiles_cache is not None and not force_reload:
            return self._profiles_cache

        if not self._profiles_path.exists():
            logger.info(
                "Archivo de perfiles no encontrado en %s. Se utilizar�n configuraciones vac�as.",
                self._profiles_path,
            )
            self._profiles_cache = {}
            return self._profiles_cache

        try:
            raw_data = json.loads(self._profiles_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.error("Archivo de perfiles inv�lido: %s", exc)
            self._profiles_cache = {}
            return self._profiles_cache

        profiles: Dict[str, ClientProfile] = {}
        for client_id, payload in raw_data.items():
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
            profiles[client_id] = ClientProfile(
                client_id=client_id,
                name=payload.get("nombre") or payload.get("name") or client_id,
                mapping={
                    key: str(value)
                    for key, value in mapping.items()
                    if value is not None
                },
                settings=combined_settings,
                keywords=[str(item).lower() for item in keywords],
                company_aliases=[str(item).lower() for item in company_aliases],
            )

        self._profiles_cache = profiles
        return profiles

    def list_profiles(self) -> List[ClientProfile]:
        return list(self.load_profiles().values())

    def get_profile(self, client_id: str) -> Optional[ClientProfile]:
        return self.load_profiles().get(client_id)

    def get_mapping(self, client_id: str) -> Optional[ColumnMapping]:
        profile = self.get_profile(client_id)
        if profile is None:
            return None
        return profile.to_column_mapping()

    def save_profile(self, profile: ClientProfile) -> None:
        profiles = self.load_profiles()
        profiles[profile.client_id] = profile
        serializable = {
            pid: {
                "nombre": p.name,
                "mapeo_columnas": p.mapping,
                **({"configuraciones": p.settings} if p.settings else {}),
                "keywords": p.keywords,
                "company_aliases": p.company_aliases,
            }
            for pid, p in profiles.items()
        }
        self._profiles_path.parent.mkdir(parents=True, exist_ok=True)
        self._profiles_path.write_text(
            json.dumps(serializable, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._profiles_cache = profiles
