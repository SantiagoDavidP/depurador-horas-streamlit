from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

from backend.domain.profiles.client_profiles import ClientProfile, ClientProfileManager
from backend.domain.rates.collaborator_rates import get_collaborator_rates_manager
from backend.domain.profiles.detectors import auto_detect_profile as detect_profile_basic
from backend.domain.parsing.excel_parser import ParsedSheet, load_multiple_sheets
from backend.domain.models import ColumnMapping


def get_profile_catalog() -> Dict[str, ClientProfile]:
    manager = ClientProfileManager()
    return {p.client_id: p for p in manager.list_profiles()}


def detect_area_from_names(names: List[str]) -> Optional[str]:
    try:
        manager = get_collaborator_rates_manager()
        cd_count = 0
        ti_count = 0
        for name in names:
            if not name:
                continue
            collab = manager.find_collaborator(str(name))
            if collab and collab.cargo:
                cd_count += 1
            else:
                ti_count += 1
        if cd_count or ti_count:
            return "CD" if cd_count > ti_count else "TI"
    except Exception:
        return None
    return None


def build_mapping_from_values(values: Dict[str, str]) -> Optional[ColumnMapping]:
    def _safe_strip(value: object) -> str:
        if value is None:
            return ""
        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass
        return str(value).strip()

    date_col = _safe_strip(values.get("date"))
    hours_col = _safe_strip(values.get("hours"))
    desc_col = _safe_strip(values.get("description"))
    proj_col = _safe_strip(values.get("project"))

    if not date_col or not hours_col or not desc_col:
        return None

    return ColumnMapping(
        date=date_col,
        hours=hours_col,
        description=desc_col,
        project=proj_col or None,
    )


def auto_detect_profile_from_parsed(
    parsed: ParsedSheet, profiles: Dict[str, ClientProfile]
) -> Optional[str]:
    metadata = parsed.metadata or {}
    company = str(metadata.get("company", "")).lower()

    # 1) match by profile name or aliases
    for pid, profile in profiles.items():
        if profile.name.lower() in company:
            return pid
        aliases = profile.company_aliases or []
        if isinstance(aliases, str):
            aliases = [aliases]
        for alias in aliases:
            if str(alias).lower() in company:
                return pid

    # 2) fallback by columns
    df = parsed.dataframe
    df_columns = [str(c).lower() for c in df.columns]
    best_match = None
    best_score = 0
    for pid, profile in profiles.items():
        expected_cols = [str(v).lower() for v in (profile.mapping or {}).values() if v]
        matches = sum(1 for col in expected_cols if any(col in df_col for df_col in df_columns))
        if matches > best_score:
            best_score = matches
            best_match = pid
    if best_match and best_score >= 3:
        return best_match
    return None


def auto_detect_profile_from_files(
    file_bytes: bytes,
    filename: str,
    profiles: Sequence[ClientProfile],
) -> Tuple[Optional[str], Dict[str, object]]:
    sheets = load_multiple_sheets(file_bytes)
    parsed = next((s for s in sheets if not s.dataframe.empty), None)
    if not parsed:
        return None, {}

    metadata = parsed.metadata or {}

    basic = detect_profile_basic(filename, metadata, profiles)
    if basic:
        return basic, metadata

    profiles_map = {p.client_id: p for p in profiles}
    fallback = auto_detect_profile_from_parsed(parsed, profiles_map)
    return fallback, metadata


def is_baninter_result(file_name: str, metadata: Optional[Dict[str, object]], client_id: Optional[str]) -> bool:
    if client_id == "cliente_talent":
        return True
    metadata = metadata or {}
    company = str(metadata.get("company", "")).lower()
    if "baninter" in company or "banco internacional" in company:
        return True
    filename = str(file_name or "").lower()
    if "banco internacional" in filename:
        return True
    if "resumen actividades recursos" in filename:
        return True
    return False


def infer_client_name_from_results(
    results: Sequence[object],
    profiles: Dict[str, ClientProfile],
) -> str:
    detected_name = None
    for r in results:
        if not getattr(r, "success", False):
            continue
        client_id = getattr(r, "client_id", None)
        metadata = getattr(r, "metadata", {}) or {}
        if client_id and client_id in profiles:
            detected_name = profiles[client_id].name
            break
        company = metadata.get("company")
        if company:
            detected_name = str(company)
            break
    return detected_name or "NOVA - TI"


def build_default_output_filename(default_client_name: str, results: Sequence[object]) -> str:
    default_filename = "Consolidado.xlsx"
    first_valid = next((r for r in results if getattr(r, "metadata", None)), None)
    if first_valid:
        meta = getattr(first_valid, "metadata", {}) or {}
        mes = meta.get("month_name", "Mes")
        year = meta.get("year", "2025")
        default_filename = f"Consolidado_{default_client_name.replace(' ', '_')}_{mes}_{year}.xlsx"
    return default_filename


def resolve_employee(metadata: Dict[str, object], filename: str) -> Dict[str, Optional[str]]:
    employee_metadata = metadata.get("employee") or metadata.get("empleado")
    filename_stem = Path(filename).stem
    return {
        "metadata": employee_metadata,
        "filename": filename_stem,
        "final": employee_metadata or filename_stem,
    }
