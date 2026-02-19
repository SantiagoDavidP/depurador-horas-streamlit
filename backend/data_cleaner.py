from __future__ import annotations

import logging
import re
import time
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

from backend.perf import PerfCollector

logger = logging.getLogger(__name__)

_METADATA_KEYWORDS = [
    "total",
    "elaborado",
    "aprobado",
    "cargo",
    "recurso",
    "tipo hora",
    "repositorio",
    "sharepoint",
    "documentacion",
    "documentación",
    "firma",
    "revision",
    "revisión",
    "nombre",
]

_RE_NUMERIC = re.compile(r"^\d+(\.\d+)?$")
_RE_SUMMARY = re.compile(r"^(?:total|resumen|suma|acumulado)(?:\s|$)", flags=re.IGNORECASE)
_RE_METADATA = re.compile("|".join(re.escape(k) for k in _METADATA_KEYWORDS), flags=re.IGNORECASE)


def detect_and_remove_metadata_rows(
    df: pd.DataFrame,
    *,
    date_column: str,
    hours_column: str,
    description_column: str,
    row_numbers: Optional[Sequence[int]] = None,
    used_range: Optional[Dict[str, int]] = None,
    perf: Optional[PerfCollector] = None,
) -> Tuple[pd.DataFrame, Optional[List[int]], int]:
    """Filtra filas de metadata y devuelve DF limpio + filas originales restantes."""
    if df.empty:
        return df.copy(), list(row_numbers) if row_numbers is not None else None, 0

    t_start = time.perf_counter()
    work_df = df.copy()
    logger.info(
        "TIMING: data_cleaner.start rows=%d cols=%d used_range=%s",
        len(work_df),
        len(work_df.columns),
        used_range or {},
    )

    # 0) Precalcular strings/trim para evitar múltiples astype(str)
    t0 = time.perf_counter()
    drop_cols = []
    object_cols = work_df.select_dtypes(include=["object", "string"]).columns
    stripped_df = pd.DataFrame(index=work_df.index)
    if len(object_cols) > 0:
        stripped_df = work_df[object_cols].astype(str).apply(lambda s: s.str.strip())
    try:
        all_nan = work_df.isna().all()
        all_empty_str = pd.Series(False, index=work_df.columns)
        if len(object_cols) > 0:
            all_empty_str.loc[object_cols] = stripped_df.eq("").all()
        drop_cols = list(work_df.columns[all_nan | all_empty_str])
        if drop_cols:
            work_df = work_df.drop(columns=drop_cols)
            if not stripped_df.empty:
                stripped_df = stripped_df.drop(columns=drop_cols, errors="ignore")
    except Exception:
        drop_cols = []
    if drop_cols:
        logger.info("TIMING: data_cleaner.drop_empty_cols removed=%d", len(drop_cols))
    if perf:
        perf.add("data_cleaner.drop_empty_cols", time.perf_counter() - t0)
    original_count = len(work_df)
    valid_mask = pd.Series(True, index=work_df.index)

    cells_iterated = len(work_df) * len(work_df.columns)
    logger.info("TIMING: data_cleaner.cells_iterated=%d", cells_iterated)

    empty_tokens = {"", "-", "---", "SN", "S/N"}

    # 1) Eliminar filas totalmente vacias (NaN, "", " ", "-", "---")
    t0 = time.perf_counter()
    empty_like = work_df.isna()
    if len(object_cols) > 0 and not stripped_df.empty:
        obj_empty_like = stripped_df.isin(empty_tokens) | stripped_df.eq("")
        empty_like.loc[:, object_cols] = empty_like.loc[:, object_cols] | obj_empty_like
    all_empty_mask = empty_like.all(axis=1)
    valid_mask &= ~all_empty_mask
    if perf:
        perf.add("data_cleaner.all_empty_rows", time.perf_counter() - t0)

    # 2) Filas sin descripcion valida
    t0 = time.perf_counter()
    if description_column in stripped_df.columns:
        desc_clean = stripped_df[description_column]
    else:
        desc_clean = work_df[description_column].astype(str).str.strip()
    desc_is_empty = work_df[description_column].isna() | desc_clean.isin(empty_tokens) | desc_clean.eq("")
    valid_mask &= ~desc_is_empty
    if perf:
        perf.add("data_cleaner.desc_empty", time.perf_counter() - t0)

    # 3) Filas de resumen (segun descripcion)
    t0 = time.perf_counter()
    desc_lower = desc_clean.str.lower()
    is_summary = desc_lower.str.contains(_RE_SUMMARY, na=False)
    valid_mask &= ~is_summary
    if perf:
        perf.add("data_cleaner.summary_rows", time.perf_counter() - t0)

    # 4) Metadata por columna fecha (mantener logica existente)
    t0 = time.perf_counter()
    if date_column in stripped_df.columns:
        date_series = stripped_df[date_column].str.lower()
    else:
        date_series = work_df[date_column].astype(str).str.lower()
    valid_mask &= ~date_series.str.contains(_RE_METADATA, na=False)
    if perf:
        perf.add("data_cleaner.metadata_rows", time.perf_counter() - t0)

    t0 = time.perf_counter()
    parsed_dates = pd.to_datetime(work_df[date_column], errors="coerce", dayfirst=True)
    valid_mask &= parsed_dates.notna()
    if perf:
        perf.add("data_cleaner.parse_dates", time.perf_counter() - t0)

    # Normalizar horas para no perder filas con formatos como "7,5" o "8h"
    t0 = time.perf_counter()
    hours_series = work_df[hours_column]
    if hours_series.dtype == object:
        hours_series = (
            hours_series.astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace(r"[^0-9\.\-]", "", regex=True)
        )
    numeric_hours = pd.to_numeric(hours_series, errors="coerce")
    if perf:
        perf.add("data_cleaner.coerce_hours", time.perf_counter() - t0)

    # 5) Si no hay descripcion y no hay horas reales, excluir (footer/totales)
    t0 = time.perf_counter()
    no_hours = numeric_hours.isna() | (numeric_hours == 0)
    invalid_payload = desc_is_empty & no_hours
    valid_mask &= ~invalid_payload
    if perf:
        perf.add("data_cleaner.invalid_payload", time.perf_counter() - t0)

    # 6) Filas tipo footer: fecha + numero suelto (ej: 176, 0)
    t0 = time.perf_counter()
    hours_missing_or_zero = numeric_hours.isna() | (numeric_hours == 0)
    desc_numeric = desc_clean.str.fullmatch(_RE_NUMERIC, na=False)
    non_core_cols = [
        col
        for col in work_df.columns
        if col not in {date_column, hours_column, description_column}
    ]
    non_core_non_empty_count = pd.Series(0, index=work_df.index)
    if non_core_cols:
        non_core = work_df[non_core_cols]
        non_empty = non_core.notna()
        non_core_obj_cols = [col for col in non_core_cols if col in stripped_df.columns]
        if non_core_obj_cols:
            non_core_stripped = stripped_df[non_core_obj_cols]
            non_empty.loc[:, non_core_obj_cols] = (
                non_empty.loc[:, non_core_obj_cols]
                & non_core_stripped.ne("")
                & ~non_core_stripped.isin(empty_tokens)
            )
        non_core_non_empty_count = non_empty.sum(axis=1).astype(int)

    footer_like = (
        hours_missing_or_zero
        & (desc_is_empty | desc_numeric)
        & (non_core_non_empty_count <= 1)
    )
    valid_mask &= ~footer_like
    if perf:
        perf.add("data_cleaner.footer_like", time.perf_counter() - t0)

    cleaned_df = work_df[valid_mask].reset_index(drop=True)
    cleaned_row_numbers: Optional[List[int]] = None
    if row_numbers is not None:
        cleaned_row_numbers = [
            row_numbers[idx]
            for idx in range(len(valid_mask))
            if valid_mask.iloc[idx]
        ]

    removed_count = original_count - len(cleaned_df)
    logger.info("Filas de metadata removidas: %d", removed_count)
    logger.info("Registros validos a procesar: %d", len(cleaned_df))
    logger.info("TIMING: data_cleaner.total %.2fs", time.perf_counter() - t_start)
    if perf:
        perf.add("data_cleaner.total", time.perf_counter() - t_start)

    return cleaned_df, cleaned_row_numbers, removed_count
