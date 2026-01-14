from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Sequence, Set, TypedDict

import pandas as pd
import holidays
from fuzzywuzzy import fuzz

logger = logging.getLogger(__name__)


class ValidationIssue(TypedDict):
    """Errores detectados durante la validación de registros."""

    fila: int
    fecha: str
    tipo_error: str
    descripcion: str
    valor_original: str
    valor_corregido: str


@dataclass(frozen=True)
class ActivityTimePattern:
    """Patrón de tiempo esperado para un tipo de actividad."""

    keywords: List[str]
    min_hours: float
    max_hours: float
    typical_hours: float
    description: str


ACTIVITY_TIME_PATTERNS: Dict[str, ActivityTimePattern] = {
    "daily": ActivityTimePattern(
        keywords=["daily", "standup", "stand-up", "scrum diario"],
        min_hours=0.15,
        max_hours=0.5,
        typical_hours=0.25,
        description="Reunión Daily/Standup",
    ),
    "meeting": ActivityTimePattern(
        keywords=["reunión", "meeting", "reunion", "junta"],
        min_hours=0.25,
        max_hours=3.0,
        typical_hours=1.0,
        description="Reunión general",
    ),
    "planning": ActivityTimePattern(
        keywords=["planning", "planificación", "estimación", "grooming"],
        min_hours=0.5,
        max_hours=4.0,
        typical_hours=2.0,
        description="Sesión de planning",
    ),
    "development": ActivityTimePattern(
        keywords=["desarrollo", "development", "codificación", "coding", "implementación", "programación"],
        min_hours=1.0,
        max_hours=8.0,
        typical_hours=4.0,
        description="Desarrollo/Programación",
    ),
    "testing": ActivityTimePattern(
        keywords=["testing", "pruebas", "qa", "test"],
        min_hours=0.5,
        max_hours=8.0,
        typical_hours=3.0,
        description="Testing/Pruebas",
    ),
    "code_review": ActivityTimePattern(
        keywords=["code review", "revisión de código", "peer review"],
        min_hours=0.25,
        max_hours=2.0,
        typical_hours=0.5,
        description="Revisión de código",
    ),
    "deployment": ActivityTimePattern(
        keywords=["deployment", "despliegue", "release", "producción"],
        min_hours=0.5,
        max_hours=4.0,
        typical_hours=1.5,
        description="Despliegue/Release",
    ),
    "documentation": ActivityTimePattern(
        keywords=["documentación", "documentation", "doc"],
        min_hours=0.5,
        max_hours=4.0,
        typical_hours=2.0,
        description="Documentación",
    ),
    "bug_fixing": ActivityTimePattern(
        keywords=["bug", "debugging", "fix", "corrección", "error"],
        min_hours=0.5,
        max_hours=6.0,
        typical_hours=2.0,
        description="Corrección de bugs",
    ),
}

def _ensure_required_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(
            "El archivo no contiene las columnas requeridas mapeadas: "
            + ", ".join(missing)
        )


def _normalize_date_output(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, str):
        return value
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _get_row_number(row_numbers: Optional[Sequence[int]], position: int) -> int:
    if row_numbers and position < len(row_numbers):
        return int(row_numbers[position])
    return position + 2


@lru_cache(maxsize=10)
def _get_ec_holidays(year: int) -> frozenset[date]:
    """Obtiene feriados de Ecuador para un año específico (cached y thread-safe)."""
    try:
        holidays_set = frozenset(holidays.country_holidays("EC", years=[year]))
        logger.debug("Se cachearon %d feriados para %s.", len(holidays_set), year)
        return holidays_set
    except Exception as exc:  # pragma: no cover
        logger.exception("Error obteniendo feriados de Ecuador para %s: %s", year, exc)
        return frozenset()


def validate_mapping(
    df: pd.DataFrame,
    *,
    date_col: str,
    hours_col: str,
    description_col: str,
    minimum_valid_ratio: float = 0.8,
) -> None:
    _ensure_required_columns(df, [date_col, hours_col, description_col])

    parsed_dates = pd.to_datetime(
        df[date_col], errors="coerce", dayfirst=True, infer_datetime_format=True
    )
    numeric_hours = pd.to_numeric(df[hours_col], errors="coerce")
    descriptions = df[description_col].astype(str).str.strip()

    valid_mask = parsed_dates.notna() & numeric_hours.notna() & descriptions.ne("")
    coverage = float(valid_mask.mean())
    if coverage < minimum_valid_ratio:
        raise ValueError(
            f"Solo el {coverage:.0%} de las filas contiene datos válidos según el mapeo. "
            "Ajuste la selección de columnas."
        )


def validate_calendar_constraints(
    df: pd.DataFrame,
    *,
    date_column: str,
    row_numbers: Optional[Sequence[int]] = None,
) -> List[ValidationIssue]:
    """
    Valida restricciones de calendario usando la columna Fecha del reporte.
    IMPORTANTE: Esta función usa los datos reales de la columna Fecha,
    NO la metadata del encabezado, para detectar feriados y fines de semana.
    """
    _ensure_required_columns(df, [date_column])
    issues: List[ValidationIssue] = []

    parsed_dates = pd.to_datetime(
        df[date_column], errors="coerce", dayfirst=True, infer_datetime_format=True
    )

    # Caché de feriados por año para optimizar
    holidays_cache: Dict[int, Set[date]] = {}

    for idx, (raw_date, parsed_date) in enumerate(zip(df[date_column], parsed_dates)):
        row_number = _get_row_number(row_numbers, idx)
        if pd.isna(parsed_date):
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha=_normalize_date_output(raw_date),
                    tipo_error="fecha_invalida",
                    descripcion="Fecha inválida o con formato no reconocido. Revise el valor.",
                    valor_original=_normalize_date_output(raw_date),
                    valor_corregido="",
                )
            )
            continue

        fecha_iso = parsed_date.strftime("%Y-%m-%d")
        if parsed_date.weekday() >= 5:
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha=fecha_iso,
                    tipo_error="fin_semana",
                    descripcion="Registro en fin de semana. Ajuste o justifique la fecha.",
                    valor_original=_normalize_date_output(raw_date),
                    valor_corregido="",
                )
            )

        # Detectar feriados usando la fecha REAL de la columna (no metadata)
        year = parsed_date.year
        if year not in holidays_cache:
            holidays_cache[year] = _get_ec_holidays(year)

        if parsed_date.date() in holidays_cache[year]:
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha=fecha_iso,
                    tipo_error="feriado",
                    descripcion="Registro en feriado nacional ecuatoriano. Valide la autorización.",
                    valor_original=_normalize_date_output(raw_date),
                    valor_corregido="",
                )
            )

    logger.info("validate_calendar_constraints: %d errores de calendario detectados usando columna Fecha", len(issues))
    return issues


def validate_daily_hours(
    df: pd.DataFrame,
    *,
    date_column: str,
    hours_column: str,
    expected_hours: float = 8.0,
    row_numbers: Optional[Sequence[int]] = None,
) -> List[ValidationIssue]:
    _ensure_required_columns(df, [date_column, hours_column])
    issues: List[ValidationIssue] = []

    parsed_dates = pd.to_datetime(
        df[date_column], errors="coerce", dayfirst=True, infer_datetime_format=True
    )
    numeric_hours = pd.to_numeric(df[hours_column], errors="coerce")

    for idx, (hours_value, raw_hours) in enumerate(zip(numeric_hours, df[hours_column])):
        if pd.isna(hours_value):
            issues.append(
                ValidationIssue(
                    fila=_get_row_number(row_numbers, idx),
                    fecha=_normalize_date_output(parsed_dates.iloc[idx]),
                    tipo_error="horas_incorrectas",
                    descripcion="Horas vacías o no numéricas. Corrija con un valor decimal.",
                    valor_original=str(raw_hours),
                    valor_corregido=f"{expected_hours:.2f}",
                )
            )

    valid_rows = parsed_dates.notna() & numeric_hours.notna()
    working = pd.DataFrame(
        {
            "fecha": parsed_dates[valid_rows].dt.date,
            "horas": numeric_hours[valid_rows],
            "row_index": df.index[valid_rows],
        }
    )
    if working.empty:
        return issues

    aggregated = working.groupby("fecha")["horas"].sum()
    for fecha, total in aggregated.items():
        if pd.isna(total) or abs(float(total) - expected_hours) <= 0.01:
            continue
        first_row_idx = int(working.loc[working["fecha"] == fecha, "row_index"].iloc[0])
        issues.append(
            ValidationIssue(
                fila=_get_row_number(row_numbers, first_row_idx),
                fecha=fecha.strftime("%Y-%m-%d"),
                tipo_error="horas_incorrectas",
                descripcion=(
                    f"Se registraron {total:.2f} horas para la fecha indicada. "
                    f"Debe registrar exactamente {expected_hours:.2f} horas."
                ),
                valor_original=f"{total:.2f}",
                valor_corregido=f"{expected_hours:.2f}",
            )
        )

    return issues


def validate_description_quality(
    df: pd.DataFrame,
    *,
    description_column: str,
    min_words: int = 3,
    row_numbers: Optional[Sequence[int]] = None,
) -> List[ValidationIssue]:
    _ensure_required_columns(df, [description_column])
    issues: List[ValidationIssue] = []
    descriptions = df[description_column].fillna("").astype(str)

    for idx, value in enumerate(descriptions):
        text = value.strip()
        row_number = _get_row_number(row_numbers, idx)
        if not text:
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha="",
                    tipo_error="descripcion_calidad",
                    descripcion="Descripción vacía. Ingrese detalles de la actividad.",
                    valor_original=value,
                    valor_corregido="",
                )
            )
            continue

        if len(text.split()) < min_words:
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha="",
                    tipo_error="descripcion_calidad",
                    descripcion=f"La descripción debe contener al menos {min_words} palabras.",
                    valor_original=value,
                    valor_corregido="",
                )
            )
        elif text == text.upper() and any(char.isalpha() for char in text):
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha="",
                    tipo_error="descripcion_calidad",
                    descripcion="Evite usar solo mayúsculas en la descripción.",
                    valor_original=value,
                    valor_corregido=text.capitalize(),
                )
            )
        elif text.replace(".", "", 1).isdigit():
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha="",
                    tipo_error="descripcion_calidad",
                    descripcion="La descripción no puede ser únicamente numérica.",
                    valor_original=value,
                    valor_corregido="",
                )
            )

    return issues


def validate_project_consistency(
    df: pd.DataFrame,
    *,
    project_column: str,
    date_column: str,
    valid_projects: Optional[List[str]] = None,
    row_numbers: Optional[Sequence[int]] = None,
) -> List[ValidationIssue]:
    _ensure_required_columns(df, [project_column, date_column])
    issues: List[ValidationIssue] = []
    projects = df[project_column].fillna("").astype(str)

    catalog = {project.upper().strip() for project in valid_projects or []}
    for idx, value in enumerate(projects):
        normalized = value.strip()
        row_number = _get_row_number(row_numbers, idx)
        if not normalized:
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha=_normalize_date_output(df.at[idx, date_column]),
                    tipo_error="proyecto_inconsistente",
                    descripcion="Proyecto vacío. Especifique el proyecto asociado.",
                    valor_original=value,
                    valor_corregido="",
                )
            )
            continue

        if catalog and normalized.upper() not in catalog:
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha=_normalize_date_output(df.at[idx, date_column]),
                    tipo_error="proyecto_inconsistente",
                    descripcion="Proyecto no pertenece al catálogo permitido.",
                    valor_original=value,
                    valor_corregido="",
                )
            )

        if len(normalized) < 3:
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha=_normalize_date_output(df.at[idx, date_column]),
                    tipo_error="proyecto_inconsistente",
                    descripcion="Nombre de proyecto demasiado corto. Verifique el formato.",
                    valor_original=value,
                    valor_corregido="",
                )
            )

    return issues


def detect_copy_paste_patterns(
    df: pd.DataFrame,
    *,
    description_column: str,
    date_column: str,
    max_consecutive_identical: int = 3,
    row_numbers: Optional[Sequence[int]] = None,
) -> List[ValidationIssue]:
    _ensure_required_columns(df, [description_column, date_column])
    issues: List[ValidationIssue] = []

    working = pd.DataFrame(
        {
            "descripcion": df[description_column].fillna("").astype(str),
            "fecha": pd.to_datetime(df[date_column], errors="coerce", dayfirst=True, infer_datetime_format=True),
            "row_idx": range(len(df)),
        }
    ).dropna(subset=["fecha"]).sort_values("fecha")

    previous_desc = None
    streak = 0

    for _, row in working.iterrows():
        current_desc = row["descripcion"].strip().lower()
        row_number = _get_row_number(row_numbers, int(row["row_idx"]))
        if current_desc and current_desc == previous_desc:
            streak += 1
        else:
            streak = 1
            previous_desc = current_desc

        if (
            current_desc
            and streak > max_consecutive_identical
            and not any(keyword in current_desc for keyword in ["daily", "standup", "stand-up", "reunión diaria", "reunion diaria"])
        ):
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha=row["fecha"].strftime("%Y-%m-%d"),
                    tipo_error="descripcion_repetida",
                    descripcion=(
                        f"Descripción repetida por más de {max_consecutive_identical} días consecutivos. "
                        "Aporta más detalle para diferenciar las actividades."
                    ),
                    valor_original=row["descripcion"],
                    valor_corregido="",
                )
            )

    return issues


def validate_duplicate_entries(
    df: pd.DataFrame,
    *,
    date_column: str,
    description_column: str,
    hours_column: str,
    similarity_threshold: int = 90,
    min_duplicates: int = 3,
    row_numbers: Optional[Sequence[int]] = None,
) -> List[ValidationIssue]:
    """Detecta registros duplicados o muy similares usando fuzzy matching."""
    issues: List[ValidationIssue] = []

    _ensure_required_columns(df, [date_column, description_column, hours_column])

    work_df = df.copy()
    work_df["_normalized_desc"] = (
        work_df[description_column]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    duplicate_groups = (
        work_df.groupby("_normalized_desc")
        .filter(lambda x: len(x) >= min_duplicates)
        .groupby("_normalized_desc")
    )

    for desc, group in duplicate_groups:
        if desc and len(desc) > 5:
            desc_lower = desc.lower()
            if (
                any(keyword in desc_lower for keyword in ["daily", "standup", "stand-up", "reunión diaria", "reunion diaria"])
                or len(desc_lower) <= 30
            ):
                continue
            filas = group.index.tolist()
            fechas = group[date_column].apply(_normalize_date_output).tolist()

            issues.append(
                ValidationIssue(
                    fila=_get_row_number(row_numbers, filas[0]),
                    fecha=", ".join(fechas[:5]),
                    tipo_error="duplicado_exacto",
                    descripcion=f"Descripción idéntica repetida {len(filas)} veces. Posible copy-paste.",
                    valor_original=str(group[description_column].iloc[0]),
                    valor_corregido="",
                )
            )

    descriptions = work_df["_normalized_desc"].unique()

    for i, desc1 in enumerate(descriptions):
        if not desc1 or len(desc1) < 10:
            continue
        for desc2 in descriptions[i + 1 :]:
            if not desc2:
                continue
            similarity = fuzz.ratio(desc1, desc2)
            if similarity >= similarity_threshold:
                rows1 = work_df[work_df["_normalized_desc"] == desc1].index.tolist()
                rows2 = work_df[work_df["_normalized_desc"] == desc2].index.tolist()
                if len(rows1) + len(rows2) >= min_duplicates:
                    desc1_lower = desc1.lower()
                    desc2_lower = desc2.lower()
                    if (
                        any(keyword in desc1_lower for keyword in ["daily", "standup", "stand-up", "reunión diaria"])
                        and any(keyword in desc2_lower for keyword in ["daily", "standup", "stand-up", "reunión diaria"])
                    ):
                        continue
                    fechas = work_df.loc[rows1 + rows2, date_column].apply(_normalize_date_output).tolist()
                    idx_ref = rows1[0] if rows1 else rows2[0]
                    issues.append(
                        ValidationIssue(
                            fila=_get_row_number(row_numbers, idx_ref),
                            fecha=", ".join(fechas[:5]),
                            tipo_error="duplicado_similar",
                            descripcion=(
                                f"Descripciones muy similares ({similarity}% match) encontradas "
                                f"{len(rows1) + len(rows2)} veces. Revise posibles duplicados."
                            ),
                            valor_original=str(work_df.loc[idx_ref, description_column]),
                            valor_corregido="",
                        )
                    )

    logger.info("validate_duplicate_entries: %d duplicados detectados", len(issues))
    return issues


def validate_reasonable_hours_per_task(
    df: pd.DataFrame,
    *,
    hours_column: str,
    description_column: str,
    date_column: str,
    tolerance_factor: float = 1.5,
    row_numbers: Optional[Sequence[int]] = None,
) -> List[ValidationIssue]:
    """Detecta horas sospechosas según el tipo de actividad."""
    issues: List[ValidationIssue] = []

    _ensure_required_columns(df, [hours_column, description_column, date_column])

    work_df = df.copy()
    work_df["_hours_numeric"] = pd.to_numeric(work_df[hours_column], errors="coerce")
    work_df["_normalized_desc"] = work_df[description_column].fillna("").astype(str).str.lower()

    def _is_compound(description: str) -> bool:
        desc = description.strip()
        if any(token in desc for token in ["1.-", "2.-", "3.-", " • ", "\n", " -> "]):
            return True
        if desc.count(",") >= 2 or len(desc) > 120:
            return True
        return False

    def _is_simple_task(desc: str, keywords: Iterable[str]) -> bool:
        stripped = desc.strip()
        if len(stripped) > 80:
            return False
        return any(
            stripped == kw
            or stripped.startswith(f"{kw} ")
            or stripped.endswith(f" {kw}")
            for kw in keywords
        )

    for idx, row in work_df.iterrows():
        hours = row["_hours_numeric"]
        desc_lower = row["_normalized_desc"]
        original_desc = row[description_column]
        fecha = _normalize_date_output(row[date_column])

        if pd.isna(hours) or hours <= 0:
            continue

        if _is_compound(original_desc):
            if hours > 8:
                issues.append(
                    ValidationIssue(
                        fila=_get_row_number(row_numbers, idx),
                        fecha=fecha,
                        tipo_error="horas_excesivas",
                        descripcion="Se registran más de 8 horas en una sola fila. Valide la jornada diaria.",
                        valor_original=f"{hours}h - {original_desc}",
                        valor_corregido="",
                    )
                )
            continue

        detected_pattern = None
        for pattern in ACTIVITY_TIME_PATTERNS.values():
            if any(keyword in desc_lower for keyword in pattern.keywords):
                detected_pattern = pattern
                break

        if not detected_pattern:
            continue

        if not _is_simple_task(original_desc.lower(), detected_pattern.keywords):
            continue

        min_allowed = detected_pattern.min_hours
        max_allowed = detected_pattern.max_hours * tolerance_factor

        if hours < min_allowed:
            issues.append(
                ValidationIssue(
                    fila=_get_row_number(row_numbers, idx),
                    fecha=fecha,
                    tipo_error="horas_muy_bajas",
                    descripcion=(
                        f"{detected_pattern.description}: {hours}h es muy poco. "
                        f"Esperado: {detected_pattern.min_hours}-{detected_pattern.max_hours}h "
                        f"(típicamente {detected_pattern.typical_hours}h)."
                    ),
                    valor_original=f"{hours}h - {original_desc}",
                    valor_corregido=f"Sugerido: {detected_pattern.typical_hours}h",
                )
            )
        elif hours > max_allowed:
            issues.append(
                ValidationIssue(
                    fila=_get_row_number(row_numbers, idx),
                    fecha=fecha,
                    tipo_error="horas_excesivas",
                    descripcion=(
                        f"{detected_pattern.description}: {hours}h es excesivo. "
                        f"Esperado: {detected_pattern.min_hours}-{detected_pattern.max_hours}h "
                        f"(típicamente {detected_pattern.typical_hours}h)."
                    ),
                    valor_original=f"{hours}h - {original_desc}",
                    valor_corregido="Revisar justificación o dividir en múltiples tareas",
                )
            )

    logger.info("validate_reasonable_hours_per_task: %d inconsistencias detectadas", len(issues))
    return issues


def get_working_days_in_period(
    year: int,
    month: int,
) -> List[date]:
    """
    Genera lista de días laborables (Lunes a Viernes) del mes, excluyendo feriados ecuatorianos.

    Args:
        year: Año
        month: Mes (1-12)

    Returns:
        Lista de fechas laborables ordenadas
    """
    from calendar import monthrange

    # Obtener feriados del mes
    ec_holidays = _get_ec_holidays(year)

    # Generar todos los días del mes
    _, last_day = monthrange(year, month)
    working_days = []

    for day in range(1, last_day + 1):
        current_date = date(year, month, day)

        # Filtrar: solo lunes a viernes (0-4)
        if current_date.weekday() < 5:
            # Excluir feriados
            if current_date not in ec_holidays:
                working_days.append(current_date)

    return working_days


def validate_working_days_completeness(
    df: pd.DataFrame,
    *,
    date_column: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
    row_numbers: Optional[Sequence[int]] = None,
) -> List[ValidationIssue]:
    """
    Valida la completitud del reporte verificando que todos los días laborables estén registrados.

    Genera una alerta listando específicamente qué días laborables (L-V) faltan por registrar,
    excluyendo automáticamente fines de semana y feriados.

    Args:
        df: DataFrame con los datos
        date_column: Nombre de la columna de fecha
        year: Año del periodo (si None, se detecta desde los datos)
        month: Mes del periodo (si None, se detecta desde los datos)
        row_numbers: Números de fila originales

    Returns:
        Lista con un issue de tipo 'completitud' si faltan días, vacía si está completo
    """
    _ensure_required_columns(df, [date_column])
    issues: List[ValidationIssue] = []

    # Parsear fechas
    parsed_dates = pd.to_datetime(
        df[date_column], errors='coerce', dayfirst=True, infer_datetime_format=True
    )
    valid_dates = parsed_dates.dropna()

    if valid_dates.empty:
        logger.warning("No hay fechas válidas para validar completitud")
        return issues

    # Detectar mes y año si no se proporcionan (usar moda de los datos)
    if month is None or year is None:
        detected_month = int(valid_dates.dt.month.mode().iloc[0])
        month_subset = valid_dates[valid_dates.dt.month == detected_month]
        detected_year = int(month_subset.dt.year.mode().iloc[0])

        if month is None:
            month = detected_month
        if year is None:
            year = detected_year

    # Obtener días laborables esperados
    expected_working_days = get_working_days_in_period(year, month)

    # Convertir fechas registradas a set de dates
    registered_dates = set(valid_dates.dt.date)

    # Calcular días faltantes
    missing_days = [day for day in expected_working_days if day not in registered_dates]

    if missing_days:
        # Formatear lista de días faltantes
        missing_days_str = ", ".join([day.strftime("%Y-%m-%d (%A)") for day in sorted(missing_days)])

        issues.append(
            ValidationIssue(
                fila=0,  # No aplica a una fila específica
                fecha="",
                tipo_error="completitud",
                descripcion=(
                    f"Reporte incompleto: Faltan {len(missing_days)} días laborables. "
                    f"Días faltantes: {missing_days_str}"
                ),
                valor_original=f"{len(registered_dates)} de {len(expected_working_days)} días registrados",
                valor_corregido=f"Se esperan {len(expected_working_days)} días laborables",
            )
        )

        logger.warning(
            "Completitud del reporte: %d/%d días laborables registrados. Faltan: %d",
            len(registered_dates),
            len(expected_working_days),
            len(missing_days),
        )
    else:
        logger.info(
            "Reporte completo: Todos los %d días laborables del mes están registrados",
            len(expected_working_days),
        )

    return issues


def validate_ticket_format(
    df: pd.DataFrame,
    *,
    ticket_column: str,
    date_column: str,
    row_numbers: Optional[Sequence[int]] = None,
) -> List[ValidationIssue]:
    """
    Valida que la columna Ticket contenga solo valores numéricos o esté vacía.

    Reglas:
    - Valores vacíos (null/NaN) son VÁLIDOS (no generan error)
    - Valores numéricos son VÁLIDOS
    - Valores de texto NO numérico son INVÁLIDOS

    Args:
        df: DataFrame a validar
        ticket_column: Nombre de la columna de ticket
        date_column: Nombre de la columna de fecha (para contexto en errores)
        row_numbers: Números de fila originales del Excel

    Returns:
        Lista de errores detectados
    """
    _ensure_required_columns(df, [ticket_column, date_column])
    issues: List[ValidationIssue] = []

    tickets = df[ticket_column]

    for idx, value in enumerate(tickets):
        row_number = _get_row_number(row_numbers, idx)

        # Valores vacíos son válidos, saltar
        if pd.isna(value):
            continue

        # Convertir a string y limpiar espacios
        value_str = str(value).strip()

        # Si está vacío después de limpiar, también es válido
        if not value_str:
            continue

        # Intentar convertir a numérico
        try:
            float(value_str)
            # Si se convierte exitosamente, es válido
            continue
        except ValueError:
            # No es numérico, generar error
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha=_normalize_date_output(df.at[idx, date_column]),
                    tipo_error="ticket_invalido",
                    descripcion="El ticket debe ser numérico o estar vacío. Valor actual contiene texto no numérico.",
                    valor_original=value_str,
                    valor_corregido="",
                )
            )

    logger.info("validate_ticket_format: %d tickets inválidos detectados", len(issues))
    return issues


def get_activity_time_suggestion(description: str) -> Optional[ActivityTimePattern]:
    """Retorna el patrón de tiempo sugerido para una descripción."""
    desc_lower = (description or "").lower()
    for pattern in ACTIVITY_TIME_PATTERNS.values():
        if any(keyword in desc_lower for keyword in pattern.keywords):
            return pattern
    return None


def run_all_validations(
    df: pd.DataFrame,
    *,
    date_column: str,
    hours_column: str,
    expected_hours: float = 8.0,
    row_numbers: Optional[Sequence[int]] = None,
    description_column: Optional[str] = None,
    project_column: Optional[str] = None,
    ticket_column: Optional[str] = None,
    valid_projects: Optional[List[str]] = None,
    min_description_words: int = 3,
    max_consecutive_identical: int = 3,
    duplicate_similarity_threshold: int = 90,
    duplicate_min_occurrences: int = 3,
    hours_tolerance_factor: float = 1.5,
    check_completeness: bool = True,
    period_year: Optional[int] = None,
    period_month: Optional[int] = None,
) -> List[ValidationIssue]:
    """
    Ejecuta todas las validaciones disponibles y agrega sus resultados.

    Args:
        check_completeness: Si True, valida que todos los días laborables del mes estén registrados
        period_year: Año del periodo para validación de completitud (None = auto-detectar)
        period_month: Mes del periodo para validación de completitud (None = auto-detectar)
    """
    issues: List[ValidationIssue] = []

    try:
        issues.extend(
            validate_calendar_constraints(
                df,
                date_column=date_column,
                row_numbers=row_numbers,
            )
        )
    except Exception as exc:
        logger.exception("Error validando calendario: %s", exc)
        raise

    try:
        issues.extend(
            validate_daily_hours(
                df,
                date_column=date_column,
                hours_column=hours_column,
                expected_hours=expected_hours,
                row_numbers=row_numbers,
            )
        )
    except Exception as exc:
        logger.exception("Error validando horas diarias: %s", exc)
        raise

    if description_column:
        try:
            issues.extend(
                validate_description_quality(
                    df,
                    description_column=description_column,
                    min_words=min_description_words,
                    row_numbers=row_numbers,
                )
            )
            issues.extend(
                detect_copy_paste_patterns(
                    df,
                    description_column=description_column,
                    date_column=date_column,
                    max_consecutive_identical=max_consecutive_identical,
                    row_numbers=row_numbers,
                )
            )
            issues.extend(
                validate_duplicate_entries(
                    df,
                    date_column=date_column,
                    description_column=description_column,
                    hours_column=hours_column,
                    similarity_threshold=duplicate_similarity_threshold,
                    min_duplicates=duplicate_min_occurrences,
                    row_numbers=row_numbers,
                )
            )
            issues.extend(
                validate_reasonable_hours_per_task(
                    df,
                    hours_column=hours_column,
                    description_column=description_column,
                    date_column=date_column,
                    tolerance_factor=hours_tolerance_factor,
                    row_numbers=row_numbers,
                )
            )
        except Exception as exc:
            logger.exception("Error validando descripciones: %s", exc)
            raise

    if project_column:
        try:
            issues.extend(
                validate_project_consistency(
                    df,
                    project_column=project_column,
                    date_column=date_column,
                    valid_projects=valid_projects,
                    row_numbers=row_numbers,
                )
            )
        except Exception as exc:
            logger.exception("Error validando proyectos: %s", exc)
            raise

    # Nueva validación: Ticket (opcional, permite valores vacíos)
    if ticket_column and ticket_column in df.columns:
        try:
            issues.extend(
                validate_ticket_format(
                    df,
                    ticket_column=ticket_column,
                    date_column=date_column,
                    row_numbers=row_numbers,
                )
            )
        except Exception as exc:
            logger.exception("Error validando formato de ticket: %s", exc)
            raise

    # Nueva validación: Completitud de días laborables
    if check_completeness:
        try:
            issues.extend(
                validate_working_days_completeness(
                    df,
                    date_column=date_column,
                    year=period_year,
                    month=period_month,
                    row_numbers=row_numbers,
                )
            )
        except Exception as exc:
            logger.exception("Error validando completitud de días laborables: %s", exc)
            raise

    return issues