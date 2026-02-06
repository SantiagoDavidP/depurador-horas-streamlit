from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

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


def detect_and_remove_metadata_rows(
    df: pd.DataFrame,
    *,
    date_column: str,
    hours_column: str,
    description_column: str,
    row_numbers: Optional[Sequence[int]] = None,
    used_range: Optional[Dict[str, int]] = None,
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

    # 0) Eliminar columnas 100% vacías (NaN o strings vacíos)
    drop_cols = []
    for col in work_df.columns:
        series = work_df[col]
        if series.isna().all():
            drop_cols.append(col)
            continue
        try:
            if series.astype(str).str.strip().eq("").all():
                drop_cols.append(col)
        except Exception:
            continue
    if drop_cols:
        work_df = work_df.drop(columns=drop_cols)
        logger.info("TIMING: data_cleaner.drop_empty_cols removed=%d", len(drop_cols))
    original_count = len(work_df)
    valid_mask = pd.Series(True, index=work_df.index)

    cells_iterated = len(work_df) * len(work_df.columns)
    logger.info("TIMING: data_cleaner.cells_iterated=%d", cells_iterated)

    empty_tokens = {"", "-", "---", "SN", "S/N"}

    # 1) Eliminar filas totalmente vacias (NaN, "", " ", "-", "---")
    empty_like_cols = []
    for col in work_df.columns:
        col_series = work_df[col]
        col_empty = col_series.isna()
        col_stripped = col_series.astype(str).str.strip()
        col_empty |= col_stripped.isin(empty_tokens)
        empty_like_cols.append(col_empty)
    all_empty_mask = pd.concat(empty_like_cols, axis=1).all(axis=1)
    valid_mask &= ~all_empty_mask

    # 2) Filas sin descripcion valida
    desc_series = work_df[description_column].astype(str)
    desc_clean = desc_series.str.strip()
    desc_is_empty = desc_series.isna() | desc_clean.isin(empty_tokens) | desc_clean.eq("")
    valid_mask &= ~desc_is_empty

    # 3) Filas de resumen (segun descripcion)
    summary_keywords = ["total", "resumen", "suma", "acumulado"]
    desc_lower = desc_clean.str.lower()
    summary_pattern = r"^(?:%s)(?:\s|$)" % "|".join(summary_keywords)
    is_summary = desc_lower.str.contains(summary_pattern, na=False, regex=True)
    valid_mask &= ~is_summary

    # 4) Metadata por columna fecha (mantener logica existente)
    date_series = work_df[date_column].astype(str).str.lower()
    for keyword in _METADATA_KEYWORDS:
        valid_mask &= ~date_series.str.contains(keyword, na=False)

    parsed_dates = pd.to_datetime(
        work_df[date_column], errors="coerce", dayfirst=True
    )
    valid_mask &= parsed_dates.notna()

    # Normalizar horas para no perder filas con formatos como "7,5" o "8h"
    hours_series = work_df[hours_column]
    if hours_series.dtype == object:
        hours_series = (
            hours_series.astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace(r"[^0-9\.\-]", "", regex=True)
        )
    numeric_hours = pd.to_numeric(hours_series, errors="coerce")

    # 5) Si no hay descripcion y no hay horas reales, excluir (footer/totales)
    no_hours = numeric_hours.isna() | (numeric_hours == 0)
    invalid_payload = desc_is_empty & no_hours
    valid_mask &= ~invalid_payload

    # 6) Filas tipo footer: fecha + numero suelto (ej: 176, 0)
    hours_missing_or_zero = numeric_hours.isna() | (numeric_hours == 0)
    desc_numeric = desc_clean.str.fullmatch(r"\d+(\.\d+)?", na=False)
    non_core_cols = [
        col
        for col in work_df.columns
        if col not in {date_column, hours_column, description_column}
    ]
    non_core_non_empty_count = pd.Series(0, index=work_df.index)
    if non_core_cols:
        for col in non_core_cols:
            series = work_df[col]
            non_empty = (
                series.notna()
                & series.astype(str).str.strip().ne("")
                & ~series.astype(str).str.strip().isin(empty_tokens)
            )
            non_core_non_empty_count += non_empty.astype(int)

    footer_like = (
        hours_missing_or_zero
        & (desc_is_empty | desc_numeric)
        & (non_core_non_empty_count <= 1)
    )
    valid_mask &= ~footer_like

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

    return cleaned_df, cleaned_row_numbers, removed_count
