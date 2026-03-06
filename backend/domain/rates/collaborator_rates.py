"""
Collaborator Rates Manager

Manages collaborator-specific billing rates and information.
Provides lookup and resolution of rates based on collaborator names.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CollaboratorRate:
    """Rate information for a specific collaborator."""

    nombre_completo: str
    seniority: str
    dias_laborables_mes: int
    salario_mensual: float
    valor_diario: float
    valor_hora_extra: float
    activo: bool
    cargo: Optional[str] = None
    email: Optional[str] = None
    nombres_alternativos: List[str] = None
    notas: Optional[str] = None

    def __post_init__(self) -> None:
        if self.nombres_alternativos is None:
            self.nombres_alternativos = [self.nombre_completo]


@dataclass
class SeniorityDefaults:
    """Default rates for a seniority level."""

    seniority: str
    salario_mensual_default: float
    valor_hora_extra_default: float
    dias_laborables_default: int

    def calculate_valor_diario(self, dias: Optional[int] = None) -> float:
        """Calculate daily rate based on monthly salary and working days."""
        days = dias or self.dias_laborables_default
        return round(self.salario_mensual_default / days, 2)


class CollaboratorRatesManager:
    """
    Manages collaborator billing rates and information.

    Features:
    - Load rates from a provided payload
    - Fuzzy matching of collaborator names
    - Fallback to seniority-based defaults
    """

    def __init__(
        self,
        collaborators: Optional[Dict[str, CollaboratorRate]] = None,
        seniority_defaults: Optional[Dict[str, SeniorityDefaults]] = None,
    ) -> None:
        self._collaborators: Dict[str, CollaboratorRate] = dict(collaborators or {})
        self._seniority_defaults: Dict[str, SeniorityDefaults] = dict(seniority_defaults or {})
        self._name_index: Dict[str, str] = {}
        self._rebuild_name_index()

    @classmethod
    def from_payload(cls, data: Dict[str, object]) -> "CollaboratorRatesManager":
        collaborators: Dict[str, CollaboratorRate] = {}
        collaborators_data = dict(data.get("collaborators", {})) if isinstance(data, dict) else {}
        for key, collab_data_obj in collaborators_data.items():
            if not isinstance(collab_data_obj, dict):
                continue
            collab_data = collab_data_obj
            collaborators[str(key)] = CollaboratorRate(
                nombre_completo=collab_data["nombre_completo"],
                seniority=collab_data["seniority"],
                cargo=collab_data.get("cargo"),
                dias_laborables_mes=collab_data["dias_laborables_mes"],
                salario_mensual=collab_data["salario_mensual"],
                valor_diario=collab_data["valor_diario"],
                valor_hora_extra=collab_data["valor_hora_extra"],
                activo=collab_data.get("activo", True),
                email=collab_data.get("email"),
                nombres_alternativos=collab_data.get("nombres_alternativos", []),
                notas=collab_data.get("notas"),
            )

        defaults: Dict[str, SeniorityDefaults] = {}
        defaults_data = dict(data.get("seniority_defaults", {})) if isinstance(data, dict) else {}
        for seniority, default_data_obj in defaults_data.items():
            if not isinstance(default_data_obj, dict):
                continue
            default_data = default_data_obj
            defaults[str(seniority)] = SeniorityDefaults(
                seniority=str(seniority),
                salario_mensual_default=default_data["salario_mensual_default"],
                valor_hora_extra_default=default_data["valor_hora_extra_default"],
                dias_laborables_default=default_data["dias_laborables_default"],
            )

        return cls(collaborators=collaborators, seniority_defaults=defaults)

    def to_payload(self) -> Dict[str, object]:
        return {
            "collaborators": {
                key: {
                    "nombre_completo": collab.nombre_completo,
                    "seniority": collab.seniority,
                    "cargo": collab.cargo,
                    "dias_laborables_mes": collab.dias_laborables_mes,
                    "salario_mensual": collab.salario_mensual,
                    "valor_diario": collab.valor_diario,
                    "valor_hora_extra": collab.valor_hora_extra,
                    "activo": collab.activo,
                    "email": collab.email,
                    "nombres_alternativos": collab.nombres_alternativos,
                    "notas": collab.notas,
                }
                for key, collab in self._collaborators.items()
            },
            "seniority_defaults": {
                key: {
                    "salario_mensual_default": default.salario_mensual_default,
                    "valor_hora_extra_default": default.valor_hora_extra_default,
                    "dias_laborables_default": default.dias_laborables_default,
                }
                for key, default in self._seniority_defaults.items()
            },
        }

    def reload_data(self, data: Dict[str, object]) -> None:
        reloaded = self.from_payload(data)
        self._collaborators = reloaded._collaborators
        self._seniority_defaults = reloaded._seniority_defaults
        self._rebuild_name_index()

    def _rebuild_name_index(self) -> None:
        self._name_index.clear()
        for key, collab in self._collaborators.items():
            for name in collab.nombres_alternativos:
                normalized = self._normalize_name(name)
                self._name_index[normalized] = key

    @staticmethod
    def _normalize_name(name: str) -> str:
        """
        Normalize a name for matching.

        - Lowercase
        - Remove accents
        - Remove extra whitespace
        - Remove punctuation
        """
        if not name:
            return ""

        name = name.lower()

        replacements = {
            "\u00e1": "a",
            "\u00e9": "e",
            "\u00ed": "i",
            "\u00f3": "o",
            "\u00fa": "u",
            "\u00f1": "n",
            "\u00fc": "u",
        }
        for accented, plain in replacements.items():
            name = name.replace(accented, plain)

        name = re.sub(r"[^\w\s]", "", name)
        name = " ".join(name.split())
        return name

    def find_collaborator(self, name: str) -> Optional[CollaboratorRate]:
        if not name:
            return None

        normalized = self._normalize_name(name)

        if normalized in self._name_index:
            key = self._name_index[normalized]
            collab = self._collaborators[key]
            if collab.activo:
                return collab

        for indexed_name, key in self._name_index.items():
            if normalized in indexed_name or indexed_name in normalized:
                collab = self._collaborators[key]
                if collab.activo:
                    logger.info("Fuzzy matched '%s' to '%s'", name, collab.nombre_completo)
                    return collab

        logger.debug("No collaborator found for name: '%s'", name)
        return None

    def get_rate_by_seniority(
        self,
        seniority: str,
        dias_laborables: Optional[int] = None,
    ) -> Optional[Dict[str, float]]:
        defaults = self._seniority_defaults.get(seniority)
        if not defaults:
            logger.warning("No defaults found for seniority: %s", seniority)
            return None

        valor_diario = defaults.calculate_valor_diario(dias_laborables)

        return {
            "salario_mensual": defaults.salario_mensual_default,
            "valor_diario": valor_diario,
            "valor_hora_extra": defaults.valor_hora_extra_default,
            "dias_laborables": dias_laborables or defaults.dias_laborables_default,
        }

    def get_rate_for_collaborator(
        self,
        name: str,
        seniority_fallback: Optional[str] = None,
    ) -> Dict[str, object]:
        collab = self.find_collaborator(name)

        if collab:
            return {
                "source": "collaborator",
                "nombre_completo": collab.nombre_completo,
                "seniority": collab.seniority,
                "cargo": collab.cargo,
                "dias_laborables_mes": collab.dias_laborables_mes,
                "salario_mensual": collab.salario_mensual,
                "valor_diario": collab.valor_diario,
                "valor_hora_extra": collab.valor_hora_extra,
                "email": collab.email,
                "found_by_name": True,
            }

        if seniority_fallback:
            rates = self.get_rate_by_seniority(seniority_fallback)
            if rates:
                return {
                    "source": "seniority",
                    "nombre_completo": name,
                    "seniority": seniority_fallback,
                    "cargo": None,
                    "found_by_name": False,
                    **rates,
                }

        logger.warning(
            "Could not find rates for '%s' with seniority '%s'",
            name,
            seniority_fallback,
        )
        return {
            "source": "unknown",
            "nombre_completo": name,
            "seniority": seniority_fallback or "Unknown",
            "cargo": None,
            "found_by_name": False,
            "salario_mensual": 0.0,
            "valor_diario": 0.0,
            "valor_hora_extra": 0.0,
            "dias_laborables_mes": 21,
        }

    def list_all_collaborators(self, active_only: bool = True) -> List[CollaboratorRate]:
        collabs = list(self._collaborators.values())
        if active_only:
            collabs = [c for c in collabs if c.activo]
        return sorted(collabs, key=lambda c: c.nombre_completo)

    def list_by_seniority(self, seniority: str) -> List[CollaboratorRate]:
        return [
            c for c in self._collaborators.values()
            if c.seniority == seniority and c.activo
        ]
