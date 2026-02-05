from __future__ import annotations

import logging
from typing import List, Optional, Sequence, Tuple

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
) -> Tuple[pd.DataFrame, Optional[List[int]], int]:
    """Filtra filas de metadata y devuelve DF limpio + filas originales restantes."""
    if df.empty:
        return df.copy(), list(row_numbers) if row_numbers is not None else None, 0

    work_df = df.copy()
    original_count = len(work_df)
    valid_mask = pd.Series(True, index=work_df.index)

    # ---------------------------------------------------------
    # 1) Eliminar filas totalmente vacías (NaN, "", " ", "-", "---")
    # ---------------------------------------------------------
    empty_tokens = {"", "-", "---"}
    empty_like_cols = []
    for col in work_df.columns:
        col_series = work_df[col]
        col_empty = col_series.isna()
        col_stripped = col_series.astype(str).str.strip()
        col_empty |= col_stripped.isin(empty_tokens)
        empty_like_cols.append(col_empty)
    all_empty_mask = pd.concat(empty_like_cols, axis=1).all(axis=1)
    valid_mask &= ~all_empty_mask

    # ---------------------------------------------------------
    # 2) Filas sin descripción válida (aunque tengan fecha/horas)
    # ---------------------------------------------------------
    desc_series = work_df[description_column].astype(str)
    desc_clean = desc_series.str.strip()
    desc_is_empty = desc_series.isna() | desc_clean.isin(empty_tokens) | desc_clean.eq("")
    valid_mask &= ~desc_is_empty

    # ---------------------------------------------------------
    # 3) Filas de resumen (según descripción)
    # ---------------------------------------------------------
    summary_keywords = ["total", "resumen", "suma", "acumulado"]
    desc_lower = desc_clean.str.lower()
    is_summary = pd.Series(False, index=work_df.index)
    for keyword in summary_keywords:
        is_summary |= desc_lower.str.contains(keyword, na=False)
    valid_mask &= ~is_summary

    # ---------------------------------------------------------
    # 4) Metadata por columna fecha (mantener lógica existente)
    # ---------------------------------------------------------
    date_series = work_df[date_column].astype(str).str.lower()
    for keyword in _METADATA_KEYWORDS:
        valid_mask &= ~date_series.str.contains(keyword, na=False)

    parsed_dates = pd.to_datetime(
        work_df[date_column], errors="coerce", dayfirst=True
    )
    valid_mask &= parsed_dates.notna()

    numeric_hours = pd.to_numeric(work_df[hours_column], errors="coerce")
    valid_mask &= numeric_hours.notna()

    # Definición estricta de fila válida:
    # fecha válida AND horas numéricas AND descripción no vacía

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
    logger.info("Registros válidos a procesar: %d", len(cleaned_df))

    return cleaned_df, cleaned_row_numbers, removed_count
