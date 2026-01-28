from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import holidays  # type: ignore
except ImportError:  # pragma: no cover - fallback si no est� instalado
    holidays = None

SPANISH_MONTHS = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

FALLBACK_EC_HOLIDAYS = [
    (1, 1, "A�o Nuevo"),
    (5, 1, "Dia del Trabajo"),
    (5, 24, "Batalla de Pichincha"),
    (8, 10, "Primer Grito de Independencia"),
    (10, 9, "Independencia de Guayaquil"),
    (11, 2, "Dia de los Difuntos"),
    (11, 3, "Independencia de Cuenca"),
    (12, 25, "Navidad"),
]


@dataclass
class HolidayInfo:
    month: Optional[int]
    year: Optional[int]
    month_name: Optional[str]
    holidays: List[Dict[str, str]]
    source: str


class HolidayDetector:
    """Obtiene feriados ecuatorianos asociados al mes presente en el timesheet."""

    def detect_month_holidays(
        self, dataframe: pd.DataFrame, date_column: str
    ) -> HolidayInfo:
        if dataframe.empty:
            return HolidayInfo(None, None, None, [], "vacio")
        if date_column not in dataframe.columns:
            raise ValueError(f"La columna '{date_column}' no existe en el DataFrame.")

        series = pd.to_datetime(dataframe[date_column], errors="coerce")
        series = series.dropna()
        if series.empty:
            return HolidayInfo(None, None, None, [], "sin_fechas")

        month = int(series.dt.month.mode().iloc[0])
        month_subset = series[series.dt.month == month]
        year = int(month_subset.dt.year.mode().iloc[0])

        holidays_list, source = self.get_ecuador_holidays(year, month)
        month_name = SPANISH_MONTHS.get(month)
        return HolidayInfo(month, year, month_name, holidays_list, source)

    def get_ecuador_holidays(self, year: int, month: int) -> Tuple[List[Dict[str, str]], str]:
        if holidays is not None:
            try:
                ec_holidays = holidays.Ecuador(years=year)  # type: ignore[attr-defined]
                filtered = [
                    {"date": dt.isoformat(), "name": name}
                    for dt, name in ec_holidays.items()
                    if dt.month == month
                ]
                if filtered:
                    return filtered, "holidays_lib"
            except Exception as exc:  # pragma: no cover - robustez ante librer�a
                logger.warning("Fallo consultando holidays: %s", exc)

        fallback = [
            {
                "date": date(year, month, day).isoformat(),
                "name": name,
            }
            for m, day, name in FALLBACK_EC_HOLIDAYS
            if m == month
        ]
        return fallback, "fallback"

    def detect_period_holidays(
            self,
            period_start: Optional[str],
            period_end: Optional[str],
        ) -> HolidayInfo:
            if not period_start or not period_end:
                return HolidayInfo(None, None, None, [], "sin_periodo")
            try:
                start_date = date.fromisoformat(str(period_start)[:10])
                end_date = date.fromisoformat(str(period_end)[:10])
            except ValueError:
                return HolidayInfo(None, None, None, [], "periodo_invalido")

            # ==============================================================================
            # 🛡️ PROTECCIÓN CONTRA RANGOS IMPOSIBLES (FIX VÍCTOR JARAMILLO)
            # ==============================================================================
            # Si el usuario pone el fin ANTES del inicio (ej: Inicio 2025, Fin 2024),
            # usamos solo el año de inicio para evitar que el sistema falle.
            # En cualquier otro caso normal, calculamos el rango de años correctamente.
            if end_date.year < start_date.year:
                years = [start_date.year]
            else:
                years = list(range(start_date.year, end_date.year + 1))
            # ==============================================================================

            collected: List[Dict[str, str]] = []
            source = "fallback"
            
            for year in years:
                if holidays is not None:
                    try:
                        ec_holidays = holidays.Ecuador(years=year)  # type: ignore[attr-defined]
                        for dt, name in ec_holidays.items():
                            # Validamos que la fecha esté dentro del rango real
                            # O si el rango estaba invertido (error usuario), validamos solo contra el mes/año de inicio
                            in_range = start_date <= dt <= end_date
                            in_corrected_year = (end_date < start_date and dt.year == start_date.year and dt.month == start_date.month)
                            
                            if in_range or in_corrected_year:
                                collected.append({"date": dt.isoformat(), "name": name})
                                source = "holidays_lib"
                    except Exception as exc:  # pragma: no cover
                        logger.warning("Fallo consultando holidays para rango: %s", exc)

            if not collected:
                # Usamos years[0] con seguridad porque la lista nunca estará vacía ahora
                current_year = years[0]
                for m, day, name in FALLBACK_EC_HOLIDAYS:
                    try:
                        candidate = date(current_year, m, day)
                    except ValueError:
                        continue
                    
                    if start_date <= candidate <= end_date:
                        collected.append({"date": candidate.isoformat(), "name": name})

            month_name = start_date.strftime("%B %Y")
            return HolidayInfo(start_date.month, start_date.year, month_name, collected, source)