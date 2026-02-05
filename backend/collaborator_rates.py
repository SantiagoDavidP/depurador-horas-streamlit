"""
Collaborator Rates Manager

Manages collaborator-specific billing rates and information.
Provides lookup and resolution of rates based on collaborator names.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
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
    
    def __post_init__(self):
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
    - Load rates from JSON configuration
    - Fuzzy matching of collaborator names
    - Fallback to seniority-based defaults
    - Cache for performance
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the rates manager.
        
        Args:
            config_path: Path to collaborator_rates.json. If None, uses default location.
        """
        self.config_path = config_path or self._default_config_path()
        self._collaborators: Dict[str, CollaboratorRate] = {}
        self._seniority_defaults: Dict[str, SeniorityDefaults] = {}
        self._name_index: Dict[str, str] = {}  # normalized_name -> collaborator_key
        
        self._load_config()
    
    def _default_config_path(self) -> Path:
        """Get default path to collaborator_rates.json."""
        return Path(__file__).resolve().parent.parent / "config" / "collaborator_rates.json"
    
    def _load_config(self):
        """Load collaborator rates from JSON file."""
        if not self.config_path.exists():
            logger.warning(
                f"Collaborator rates file not found: {self.config_path}. "
                "Using seniority defaults only."
            )
            return
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Load collaborators
            collaborators_data = data.get("collaborators", {})
            for key, collab_data in collaborators_data.items():
                self._collaborators[key] = CollaboratorRate(
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
            
            # Build name index for fast lookup
            for key, collab in self._collaborators.items():
                # Add all alternative names to index
                for name in collab.nombres_alternativos:
                    normalized = self._normalize_name(name)
                    self._name_index[normalized] = key
            
            # Load seniority defaults
            defaults_data = data.get("seniority_defaults", {})
            for seniority, default_data in defaults_data.items():
                self._seniority_defaults[seniority] = SeniorityDefaults(
                    seniority=seniority,
                    salario_mensual_default=default_data["salario_mensual_default"],
                    valor_hora_extra_default=default_data["valor_hora_extra_default"],
                    dias_laborables_default=default_data["dias_laborables_default"],
                )
            
            logger.info(
                f"Loaded {len(self._collaborators)} collaborators and "
                f"{len(self._seniority_defaults)} seniority defaults"
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in collaborator rates file: {e}")
        except Exception as e:
            logger.error(f"Error loading collaborator rates: {e}")
    
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
        
        # Lowercase
        name = name.lower()
        
        # Remove accents
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u'
        }
        for accented, plain in replacements.items():
            name = name.replace(accented, plain)
        
        # Remove punctuation and extra spaces
        name = re.sub(r'[^\w\s]', '', name)
        name = ' '.join(name.split())
        
        return name
    
    def find_collaborator(self, name: str) -> Optional[CollaboratorRate]:
        """
        Find a collaborator by name with fuzzy matching.
        
        Args:
            name: Collaborator name (can be partial or with variations)
        
        Returns:
            CollaboratorRate if found, None otherwise
        """
        if not name:
            return None
        
        normalized = self._normalize_name(name)
        
        # Exact match in index
        if normalized in self._name_index:
            key = self._name_index[normalized]
            collab = self._collaborators[key]
            if collab.activo:
                return collab
        
        # Fuzzy match: check if normalized name is contained in any indexed name
        for indexed_name, key in self._name_index.items():
            if normalized in indexed_name or indexed_name in normalized:
                collab = self._collaborators[key]
                if collab.activo:
                    logger.info(f"Fuzzy matched '{name}' to '{collab.nombre_completo}'")
                    return collab
        
        logger.debug(f"No collaborator found for name: '{name}'")
        return None
    
    def get_rate_by_seniority(
        self,
        seniority: str,
        dias_laborables: Optional[int] = None
    ) -> Optional[Dict[str, float]]:
        """
        Get default rates for a seniority level.
        
        Args:
            seniority: Seniority level (Senior, Semisenior, Junior)
            dias_laborables: Number of working days (if different from default)
        
        Returns:
            Dict with salario_mensual, valor_diario, valor_hora_extra
        """
        defaults = self._seniority_defaults.get(seniority)
        if not defaults:
            logger.warning(f"No defaults found for seniority: {seniority}")
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
        seniority_fallback: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Get rate information for a collaborator.
        
        Tries to find by name first, falls back to seniority if not found.
        
        Args:
            name: Collaborator name
            seniority_fallback: Seniority to use if collaborator not found by name
        
        Returns:
            Dict with rate information including source ('collaborator' or 'seniority')
        """
        # Try to find by name
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
        
        # Fallback to seniority
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
        
        # No match found
        logger.warning(
            f"Could not find rates for '{name}' with seniority '{seniority_fallback}'"
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
        """
        Get list of all collaborators.
        
        Args:
            active_only: If True, only return active collaborators
        
        Returns:
            List of CollaboratorRate objects
        """
        collabs = list(self._collaborators.values())
        
        if active_only:
            collabs = [c for c in collabs if c.activo]
        
        return sorted(collabs, key=lambda c: c.nombre_completo)
    
    def list_by_seniority(self, seniority: str) -> List[CollaboratorRate]:
        """Get all collaborators of a specific seniority level."""
        return [
            c for c in self._collaborators.values()
            if c.seniority == seniority and c.activo
        ]
    
    def reload_config(self):
        """Reload configuration from file."""
        self._collaborators.clear()
        self._seniority_defaults.clear()
        self._name_index.clear()
        self._load_config()


# Global instance (cached)
_manager: Optional[CollaboratorRatesManager] = None


@lru_cache(maxsize=1)
def get_collaborator_rates_manager() -> CollaboratorRatesManager:
    """Get singleton instance of CollaboratorRatesManager."""
    global _manager
    if _manager is None:
        _manager = CollaboratorRatesManager()
    return _manager
