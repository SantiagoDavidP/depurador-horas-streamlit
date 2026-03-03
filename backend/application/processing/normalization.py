from __future__ import annotations

import logging
import re
from typing import List, Optional, Sequence

import pandas as pd

from backend.domain.models import ColumnMapping
from backend.domain.validation.validators import ValidationIssue

from .constants import _ERROR_PRIORITY, _ERROR_PRIORITY_INDEX

logger = logging.getLogger(__name__)


class ProcessingNormalizationMixin:
    @staticmethod
    def _fill_grouped_dates_for_payload(
        df: pd.DataFrame,
        *,
        date_column: str,
        hours_column: str,
        description_column: Optional[str],
    ) -> int:
        """Fill grouped/merged date cells only for rows that look like real payload."""
        if date_column not in df.columns or df.empty:
            return 0

        date_series = df[date_column]
        before_missing = date_series.isna() | date_series.astype(str).str.strip().eq("")

        if description_column and description_column in df.columns:
            desc_clean = df[description_column].fillna("").astype(str).str.strip()
        else:
            desc_clean = pd.Series("", index=df.index, dtype="object")
        desc_lower = desc_clean.str.lower()

        desc_has_text = desc_clean.ne("") & ~desc_clean.isin({"-", "---"})
        desc_is_summary = desc_lower.str.startswith(("total", "resumen", "suma", "acumulado"))
        desc_has_metadata_token = desc_lower.str.contains(
            r"(?:elaborado|aprobado|firma|periodo|fecha del informe|cliente|consultor|"
            r"recurso|repositorio|sharepoint|informe de actividades|http://|https://|\\\\)",
            na=False,
        )

        if hours_column in df.columns:
            hours_num = pd.to_numeric(df[hours_column], errors="coerce")
        else:
            hours_num = pd.Series(pd.NA, index=df.index, dtype="float64")
        hours_has_value = hours_num.notna() & (hours_num != 0)

        payload_mask = (desc_has_text & ~desc_is_summary & ~desc_has_metadata_token) | hours_has_value
        fill_mask = before_missing & payload_mask

        if not fill_mask.any():
            return 0

        df.loc[payload_mask, date_column] = df.loc[payload_mask, date_column].ffill()
        after_missing = df[date_column].isna() | df[date_column].astype(str).str.strip().eq("")
        filled = int((before_missing & payload_mask & ~after_missing).sum())
        return filled


    @staticmethod
    def _apply_validation_corrections(
        df: pd.DataFrame,
        mapping: ColumnMapping,
        row_numbers: Sequence[int],
        validation_errors: Sequence[ValidationIssue],
    ) -> None:
        """Apply safe, suggested corrections to the in-memory dataframe."""
        if not row_numbers:
            return

        row_lookup = {row_num: idx for idx, row_num in enumerate(row_numbers)}
        for issue in validation_errors:
            correction = str(issue.get("valor_corregido") or "").strip()
            if not correction:
                continue

            row_idx = row_lookup.get(issue.get("fila"))
            if row_idx is None or row_idx >= len(df):
                continue

            tipo = issue.get("tipo_error")
            if tipo == "descripcion_calidad" and mapping.description in df.columns:
                df.at[df.index[row_idx], mapping.description] = correction
            # Importantly, do NOT overwrite hours here; only apply safe text fixes.

    @staticmethod
    def _sort_errors_df(errors_df: pd.DataFrame) -> pd.DataFrame:
        if errors_df is None or errors_df.empty or "tipo_error" not in errors_df.columns:
            return errors_df
        sorted_df = errors_df.copy()
        sorted_df["__severity"] = sorted_df["tipo_error"].astype(str).apply(
            lambda t: _ERROR_PRIORITY_INDEX.get(t, len(_ERROR_PRIORITY))
        )
        sorted_df["__order"] = range(len(sorted_df))
        sorted_df = sorted_df.sort_values(["__severity", "__order"])
        return sorted_df.drop(columns=["__severity", "__order"])

    @staticmethod
    def _normalize_ticket_columns(df: pd.DataFrame) -> None:
        ticket_columns = [
            col for col in df.columns if "ticket" in str(col).lower()
        ]
        if not ticket_columns:
            return

        def _normalize(value: object) -> object:
            if pd.isna(value):
                return value
            if isinstance(value, (int, float)) and not pd.isna(value):
                if isinstance(value, float) and value.is_integer():
                    return str(int(value))
                return str(value)
            text = str(value).strip()
            if not text:
                return ""
            normalized = re.sub(r"\s+", "", text)
            return normalized

        for col in ticket_columns:
            df[col] = df[col].apply(_normalize)

    @staticmethod
    def _drop_empty_columns(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        drop_cols = []
        for col in df.columns:
            series = df[col]
            if series.isna().all():
                drop_cols.append(col)
                continue
            try:
                if series.astype(str).str.strip().eq("").all():
                    drop_cols.append(col)
            except Exception:
                continue
        if drop_cols:
            logger.info("Columnas fantasma removidas: %d", len(drop_cols))
            return df.drop(columns=drop_cols)
        return df

    @staticmethod
    def _normalize_ticket_validation_errors(
        errors: List[ValidationIssue],
        df: pd.DataFrame,
        ticket_column: str,
        row_numbers: Sequence[int],
    ) -> List[ValidationIssue]:
        if not errors or ticket_column not in df.columns:
            return errors

        def _is_valid_ticket(value: object) -> bool:
            if pd.isna(value):
                return True
            if isinstance(value, (int, float)) and not pd.isna(value):
                return True
            text = str(value).strip()
            if not text:
                return True
            normalized = re.sub(r"\s+", "", text)
            token = re.sub(r"[^A-Za-z0-9]", "", normalized).upper()
            if token in {"NA", "NAN", "SN"}:
                return True
            return normalized.isalnum()

        row_lookup = {row_num: idx for idx, row_num in enumerate(row_numbers)}
        filtered: List[ValidationIssue] = []
        for issue in errors:
            tipo = str(issue.get("tipo_error") or "")
            if tipo not in {"ticket_no_numerico", "ticket_invalido"}:
                filtered.append(issue)
                continue
            row_num = issue.get("fila")
            idx = row_lookup.get(row_num)
            if idx is None or idx >= len(df):
                filtered.append(issue)
                continue
            value = df.at[df.index[idx], ticket_column]
            if _is_valid_ticket(value):
                continue
            issue["tipo_error"] = "ticket_invalido"
            issue["descripcion"] = (
                "El ticket debe ser alfanumérico o estar vacío. Evite caracteres especiales."
            )
            filtered.append(issue)

        return filtered



def _safe_string(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)
