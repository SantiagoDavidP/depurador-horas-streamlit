from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from backend.domain.roles.role_validator import RoleActivityValidator

logger = logging.getLogger(__name__)


def default_role_taxonomy_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "role_taxonomy.json"


def load_role_validator(path: Optional[Path] = None) -> Optional[RoleActivityValidator]:
    taxonomy_path = path or default_role_taxonomy_path()
    if not taxonomy_path.exists():
        logger.warning("No se encontro role_taxonomy.json, se omite validacion de rol.")
        return None
    try:
        with taxonomy_path.open("r", encoding="utf-8") as handle:
            taxonomy = json.load(handle)
        return RoleActivityValidator(taxonomy)
    except Exception as exc:
        logger.warning("No se pudo cargar la taxonomia de roles: %s", exc)
        return None
