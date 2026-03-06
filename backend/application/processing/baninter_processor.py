from __future__ import annotations

import logging
import unicodedata
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

from backend.domain.models import ColumnMapping
from backend.application.validation.validators import _coerce_hours_series

logger = logging.getLogger(__name__)

BANINTER_CORE_COLUMNS = ["Fecha", "Proyecto", "Actividad", "Horas"]
BANINTER_PHASE_COLUMN = "Fase/Ciclo Desarrollo/ Tipo Actividad"
BANINTER_OPTIONAL_COLUMNS = ["ID", BANINTER_PHASE_COLUMN]


def _normalize_header(text: object) -> str:
    raw = str(text or "").strip().lower()
    if not raw:
        return ""
    raw = unicodedata.normalize("NFKD", raw)
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = re.sub(r"\s+", " ", raw)
    return raw


def _normalize_compact(text: object) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_header(text))


def _find_column(columns: List[object], keywords: List[str]) -> Optional[str]:
    normalized = {col: _normalize_header(col) for col in columns}
    for col, norm in normalized.items():
        for keyword in keywords:
            if keyword in norm:
                return str(col)
    return None


def _find_phase_column(columns: List[object]) -> Optional[str]:
    for col in columns:
        norm = _normalize_header(col)
        compact = _normalize_compact(col)
        if "faseciclodesarrollo" in compact:
            return str(col)
        if ("fase" in norm or "ciclo" in norm) and (
            "desarrollo" in norm or "tipo" in norm or "actividad" in norm
        ):
            return str(col)
    return None


def _find_id_column(columns: List[object]) -> Optional[str]:
    for col in columns:
        norm = _normalize_header(col)
        compact = _normalize_compact(col)
        if norm == "id" or compact == "id":
            return str(col)
    return None


def prepare_baninter_dataframe(
    df: pd.DataFrame,
    mapping: ColumnMapping,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """
    Aplica tolerancia BANINTER:
    - forward-fill de fecha/proyecto/fase
    - columnas opcionales solo si existen (no crear columnas extra)
    - reporte de imputaciones y cobertura
    """
    work_df = df.copy()
    columns = list(work_df.columns)

    date_src = mapping.date if mapping.date in work_df.columns else _find_column(columns, ["fecha", "date", "dia"])
    hours_src = mapping.hours if mapping.hours in work_df.columns else _find_column(columns, ["horas", "hora", "hrs"])
    desc_src = (
        mapping.description
        if mapping.description in work_df.columns
        else _find_column(columns, ["actividad", "tareas", "tarea", "descripcion", "detalle"])
    )
    project_src = (
        mapping.project
        if mapping.project and mapping.project in work_df.columns
        else _find_column(columns, ["proyecto"])
    )
    phase_src = _find_phase_column(columns)
    id_src = _find_id_column(columns)

    missing_core = [
        name
        for name, col in [
            ("Fecha", date_src),
            ("Horas", hours_src),
            ("Actividad", desc_src),
            ("Proyecto", project_src),
        ]
        if not col
    ]
    if missing_core:
        raise ValueError(
            "BANINTER: No se encontraron columnas minimas ("
            + ", ".join(missing_core)
            + ")."
        )

    rename_map = {
        str(date_src): "Fecha",
        str(hours_src): "Horas",
        str(desc_src): "Actividad",
        str(project_src): "Proyecto",
    }
    if phase_src:
        rename_map[str(phase_src)] = BANINTER_PHASE_COLUMN
    if id_src:
        rename_map[str(id_src)] = "ID"

    work_df = work_df.rename(columns=rename_map)

    output_columns = ["Fecha", "Proyecto"]
    if id_src and "ID" in work_df.columns:
        output_columns.append("ID")
    output_columns.extend(["Actividad", "Horas"])
    if phase_src and BANINTER_PHASE_COLUMN in work_df.columns:
        output_columns.append(BANINTER_PHASE_COLUMN)

    work_df = work_df[[col for col in output_columns if col in work_df.columns]]

    missing_optional: List[str] = []
    if not phase_src:
        missing_optional.append(BANINTER_PHASE_COLUMN)

    pre_df = work_df.copy()
    date_col = "Fecha"
    hours_col = "Horas"
    desc_col = "Actividad"
    project_col = "Proyecto"
    phase_col = BANINTER_PHASE_COLUMN if phase_src else None

    desc_series = pre_df[desc_col].fillna("").astype(str).str.strip()
    hours_numeric = _coerce_hours_series(pre_df[hours_col])
    has_payload = (desc_series.ne("")) | (hours_numeric.notna() & (hours_numeric != 0))
    payload_count = int(has_payload.sum())
    if payload_count == 0:
        raise ValueError("BANINTER: El dataset no contiene filas con Horas/Tareas.")

    def _empty_mask(series: pd.Series) -> pd.Series:
        return series.isna() | series.astype(str).str.strip().eq("")

    def _ffill_column(col_name: str) -> int:
        if not col_name or col_name not in work_df.columns:
            return 0
        series = work_df[col_name]
        before_empty = _empty_mask(series)
        filled = series.copy()
        if has_payload.any():
            filled.loc[has_payload] = filled.loc[has_payload].ffill()
        work_df[col_name] = filled
        after_empty = _empty_mask(filled)
        filled_count = int((before_empty & ~after_empty & has_payload).sum())
        return filled_count

    parsed_dates_before = pd.to_datetime(pre_df[date_col], errors="coerce", dayfirst=True)
    project_series_before = (
        pre_df[project_col].fillna("").astype(str).str.strip()
        if project_col
        else pd.Series("", index=pre_df.index)
    )

    filled_fecha = _ffill_column(date_col)
    filled_proyecto = _ffill_column(project_col) if project_col else 0
    filled_fase = _ffill_column(phase_col) if phase_col else 0

    parsed_dates_after = pd.to_datetime(work_df[date_col], errors="coerce", dayfirst=True)
    project_series_after = (
        work_df[project_col].fillna("").astype(str).str.strip()
        if project_col
        else pd.Series("", index=work_df.index)
    )

    valid_before = (
        desc_series.ne("")
        & hours_numeric.notna()
        & (hours_numeric > 0)
        & parsed_dates_before.notna()
        & project_series_before.ne("")
    )

    valid_after = (
        desc_series.ne("")
        & hours_numeric.notna()
        & (hours_numeric > 0)
        & parsed_dates_after.notna()
        & project_series_after.ne("")
    )

    total_rows = len(work_df)
    valid_before_count = int(valid_before.sum())
    valid_after_count = int(valid_after.sum())
    coverage_before = float(valid_before_count / total_rows) if total_rows else 0.0
    coverage_after = float(valid_after_count / total_rows) if total_rows else 0.0

    report: Dict[str, object] = {
        "missing_optional_columns": sorted(set(missing_optional)),
        "filled_fecha": filled_fecha,
        "filled_proyecto": filled_proyecto,
        "filled_fase": filled_fase,
        "valid_before": valid_before_count,
        "valid_after": valid_after_count,
        "coverage_before": coverage_before,
        "coverage_after": coverage_after,
        "project_col": project_col,
        "phase_col": phase_col,
        "id_col": "ID" if id_src else None,
        "resolved_mapping": {
            "date": date_col,
            "hours": hours_col,
            "description": desc_col,
            "project": project_col,
            "phase": phase_col,
            "id": "ID" if id_src else None,
        },
        "output_columns": output_columns,
        "warnings": [],
    }

    if coverage_after < 0.8:
        report["warnings"].append(
            f"Solo el {coverage_after:.0%} de las filas contiene datos validos despues de imputar."
        )

    return work_df, report

