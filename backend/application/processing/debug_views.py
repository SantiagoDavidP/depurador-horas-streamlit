from __future__ import annotations

from typing import Sequence

import pandas as pd

from backend.domain.models import ColumnMapping
from backend.application.validation.validators import ValidationIssue, _coerce_hours_series


class ProcessingDebugViewsMixin:
    def _group_hours_debug_df(
        self,
        df: pd.DataFrame,
        *,
        mapping: ColumnMapping,
        row_numbers: Sequence[int],
    ) -> pd.DataFrame:
        """Agrupa horas por fecha con detalle de filas y valores."""
        if df.empty or mapping.date not in df.columns or mapping.hours not in df.columns:
            return pd.DataFrame()

        parsed_dates = pd.to_datetime(df[mapping.date], errors="coerce", dayfirst=True)
        hours_raw = df[mapping.hours]
        hours_num = _coerce_hours_series(hours_raw)
        # Alinear longitudes defensivamente
        safe_len = min(len(df.index), len(row_numbers))
        if safe_len == 0:
            return pd.DataFrame()
        df = df.iloc[:safe_len].copy()
        row_numbers_series = pd.Series(list(row_numbers)[:safe_len], index=df.index)

        work = pd.DataFrame(
            {
                "Fecha": parsed_dates.dt.date,
                "Horas_Raw": hours_raw,
                "Horas_Num": hours_num,
                "Fila_Excel": row_numbers_series,
            }
        ).dropna(subset=["Fecha"], how="any")

        if work.empty:
            return pd.DataFrame()

        def _join_series(series: pd.Series) -> str:
            return " | ".join(str(x) for x in series.tolist())

        grouped = (
            work.groupby("Fecha")
            .agg(
                Filas=("Horas_Num", "size"),
                Horas_Sumadas=("Horas_Num", "sum"),
                Horas_Invalidas=("Horas_Num", lambda s: int(s.isna().sum())),
                Horas_Raw=("Horas_Raw", _join_series),
                Filas_Excel=("Fila_Excel", _join_series),
            )
            .reset_index()
        )
        return grouped

    @staticmethod
    def _merge_hours_debug(
        raw_debug: pd.DataFrame,
        clean_debug: pd.DataFrame,
        *,
        expected_hours: float,
    ) -> pd.DataFrame:
        if raw_debug.empty and clean_debug.empty:
            return pd.DataFrame()

        raw = raw_debug.rename(
            columns={
                "Filas": "Filas_Raw",
                "Horas_Sumadas": "Horas_Sumadas_Raw",
                "Horas_Invalidas": "Horas_Invalidas_Raw",
                "Horas_Raw": "Horas_Raw_Raw",
                "Filas_Excel": "Filas_Excel_Raw",
            }
        )
        clean = clean_debug.rename(
            columns={
                "Filas": "Filas_Clean",
                "Horas_Sumadas": "Horas_Sumadas_Clean",
                "Horas_Invalidas": "Horas_Invalidas_Clean",
                "Horas_Raw": "Horas_Raw_Clean",
                "Filas_Excel": "Filas_Excel_Clean",
            }
        )

        merged = raw.merge(clean, on="Fecha", how="outer").sort_values("Fecha")
        merged["Horas_Esperadas"] = expected_hours
        merged["Diferencia_Clean"] = merged["Horas_Sumadas_Clean"] - expected_hours
        return merged

    def _build_hours_debug_detail(
        self,
        *,
        df: pd.DataFrame,
        mapping: ColumnMapping,
        row_numbers: Sequence[int],
        validation_errors: Sequence[ValidationIssue],
        stage_label: str,
    ) -> pd.DataFrame:
        """Detalle por fila para fechas con horas_incorrectas."""
        if df.empty or not validation_errors:
            return pd.DataFrame()

        target_dates = sorted(
            {
                err.get("fecha")
                for err in validation_errors
                if err.get("tipo_error") == "horas_incorrectas" and err.get("fecha")
            }
        )
        if not target_dates:
            return pd.DataFrame()

        parsed_dates = pd.to_datetime(df[mapping.date], errors="coerce", dayfirst=True)
        hours_raw = df[mapping.hours]
        hours_num = _coerce_hours_series(hours_raw)
        descriptions = (
            df[mapping.description]
            if mapping.description in df.columns
            else pd.Series(index=df.index, dtype="object")
        )
        desc_series = descriptions.astype(str)
        desc_clean = desc_series.str.strip()
        empty_tokens = {"", "-", "---"}
        desc_empty = desc_series.isna() | desc_clean.isin(empty_tokens) | desc_clean.eq("")
        desc_numeric = desc_clean.str.fullmatch(r"\d+(\.\d+)?", na=False)
        hours_missing_or_zero = hours_num.isna() | (hours_num == 0)

        non_core_cols = [
            col
            for col in df.columns
            if col not in {mapping.date, mapping.hours, mapping.description}
        ]
        non_core_non_empty_count = pd.Series(0, index=df.index)
        if non_core_cols:
            for col in non_core_cols:
                series = df[col]
                non_empty = (
                    series.notna()
                    & series.astype(str).str.strip().ne("")
                    & ~series.astype(str).str.strip().isin(empty_tokens)
                )
                non_core_non_empty_count += non_empty.astype(int)

        footer_like = (
            hours_missing_or_zero
            & (desc_empty | desc_numeric)
            & (non_core_non_empty_count <= 1)
        )
        # Alinear longitudes defensivamente
        safe_len = min(len(df.index), len(row_numbers))
        if safe_len == 0:
            return pd.DataFrame()
        df = df.iloc[:safe_len].copy()
        row_numbers_series = pd.Series(list(row_numbers)[:safe_len], index=df.index)

        work = pd.DataFrame(
            {
                "Fecha": parsed_dates.dt.strftime("%Y-%m-%d"),
                "Horas_Raw": hours_raw,
                "Horas_Num": hours_num,
                "Descripcion": descriptions,
                "Fila_Excel": row_numbers_series,
                "Etapa": stage_label,
                "Desc_Vacia": desc_empty,
                "Desc_Numerica": desc_numeric,
                "Horas_Faltantes": hours_missing_or_zero,
                "Cols_NoCore": non_core_non_empty_count,
                "Footer_Like": footer_like,
            }
        )
        return work[work["Fecha"].isin(target_dates)].reset_index(drop=True)

