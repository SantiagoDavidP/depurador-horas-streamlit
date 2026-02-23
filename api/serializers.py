from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

import pandas as pd

from backend.holiday_detector import HolidayDetector


_ERROR_PRIORITY = [
    "completitud",
    "fecha_fuera_periodo",
    "fecha_invalida",
    "fin_semana",
    "feriado",
    "horas_faltantes",
    "horas_incorrectas",
    "horas_excesivas",
    "horas_muy_bajas",
    "duplicado_exacto",
    "duplicado_similar",
    "descripcion_repetida",
    "campo_vacio",
]
_ERROR_PRIORITY_INDEX = {t: i for i, t in enumerate(_ERROR_PRIORITY)}

_holiday_detector = HolidayDetector()


def sanitize_payload(value: Any) -> Any:
    """Convierte tipos no serializables (numpy/pandas) a tipos JSON seguros."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): sanitize_payload(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize_payload(v) for v in value]

    # numpy scalars
    try:
        import numpy as np  # type: ignore

        if isinstance(value, np.generic):
            return value.item()
    except Exception:
        pass

    # pandas Timestamp / datetime
    try:
        import pandas as pd  # type: ignore

        if isinstance(value, pd.Timestamp):
            return value.isoformat()
    except Exception:
        pass

    try:
        from datetime import date, datetime

        if isinstance(value, (datetime, date)):
            return value.isoformat()
    except Exception:
        pass

    # Fallback: evitar errores de serializacion (openpyxl, etc.)
    try:
        return str(value)
    except Exception:
        return None


def sort_errors_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    sorted_df = df.copy()
    sorted_df["__severity"] = sorted_df["tipo_error"].astype(str).apply(
        lambda t: _ERROR_PRIORITY_INDEX.get(t, len(_ERROR_PRIORITY))
    )
    sorted_df["__order"] = range(len(sorted_df))
    sorted_df = sorted_df.sort_values(["__severity", "__order"])
    return sorted_df.drop(columns=["__severity", "__order"])


def dataframe_to_records(df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    safe_df = df.copy()
    for col in safe_df.columns:
        safe_df[col] = safe_df[col].apply(lambda v: "" if pd.isna(v) else v)
    return safe_df.to_dict(orient="records")


def summary_to_dict(summary: object) -> Dict[str, Any]:
    if summary is None:
        return {}
    if hasattr(summary, "__dict__"):
        return asdict(summary)  # type: ignore[arg-type]
    return dict(summary)  # type: ignore[arg-type]


def build_holiday_info(
    dataframe: pd.DataFrame,
    date_column: Optional[str],
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    if dataframe is None or dataframe.empty:
        return None

    info = None
    metadata = metadata or {}

    if date_column and date_column in dataframe.columns:
        try:
            info = _holiday_detector.detect_month_holidays(dataframe, date_column)
        except Exception:
            info = None

    if info is None:
        period_start = metadata.get("period_start")
        period_end = metadata.get("period_end")
        if period_start and period_end:
            try:
                info = _holiday_detector.detect_period_holidays(period_start, period_end)
            except Exception:
                info = None

    if info is None or info.month is None or info.year is None:
        return None

    month_label = info.month_name or str(info.month)
    if str(info.year) not in month_label:
        month_label = f"{month_label} {info.year}"

    return {
        "month": info.month,
        "year": info.year,
        "month_label": month_label,
        "holidays": info.holidays,
        "source": info.source,
    }
