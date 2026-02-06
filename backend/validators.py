from __future__ import annotations

import logging
import numbers
import re
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


def _coerce_hours_series(series: pd.Series) -> pd.Series:
    """Normaliza horas para aceptar formatos como '7,5' o '8h'."""
    if series is None:
        return series
    if series.dtype == object:
        cleaned = (
            series.astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace(r"[^0-9\.\-]", "", regex=True)
        )
        return pd.to_numeric(cleaned, errors="coerce")
    return pd.to_numeric(series, errors="coerce")


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
    import time
    t_start = time.perf_counter()
    _ensure_required_columns(df, [date_col, hours_col, description_col])

    parsed_dates = pd.to_datetime(
        df[date_col], errors="coerce", dayfirst=True
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
    logger.info(
        "TIMING: validate_mapping %.2fs rows=%d cols=%d",
        time.perf_counter() - t_start,
        len(df),
        len(df.columns),
    )


def validate_calendar_constraints(
    df: pd.DataFrame,
    *,
    date_column: str,
    row_numbers: Optional[Sequence[int]] = None,
    parsed_dates: Optional[pd.Series] = None,
) -> List[ValidationIssue]:
    """
    Valida restricciones de calendario usando la columna Fecha del reporte.
    IMPORTANTE: Esta función usa los datos reales de la columna Fecha,
    NO la metadata del encabezado, para detectar feriados y fines de semana.
    """
    _ensure_required_columns(df, [date_column])
    issues: List[ValidationIssue] = []

    if parsed_dates is None:
        parsed_dates = pd.to_datetime(
            df[date_column], errors="coerce", dayfirst=True
        )

    # Caché de feriados por año para optimizar
    holidays_cache: Dict[int, Set[date]] = {}

    raw_dates = df[date_column]
    parsed = parsed_dates
    is_invalid = parsed.isna()
    valid_idx = parsed.index[~is_invalid]

    # Fechas inválidas (mantener misma fila/valor)
    for idx in parsed.index[is_invalid]:
        row_number = _get_row_number(row_numbers, idx)
        raw_date = raw_dates.iloc[idx]
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

    if len(valid_idx) == 0:
        logger.info("validate_calendar_constraints: %d errores de calendario detectados usando columna Fecha", len(issues))
        return issues

    parsed_valid = parsed.loc[valid_idx]
    raw_valid = raw_dates.loc[valid_idx]
    fecha_iso = parsed_valid.dt.strftime("%Y-%m-%d")

    # Fines de semana
    is_weekend = parsed_valid.dt.weekday >= 5
    for idx in parsed_valid.index[is_weekend]:
        row_number = _get_row_number(row_numbers, idx)
        issues.append(
            ValidationIssue(
                fila=row_number,
                fecha=fecha_iso.loc[idx],
                tipo_error="fin_semana",
                descripcion="Registro en fin de semana. Validar si son Horas Extras.",
                valor_original=_normalize_date_output(raw_valid.loc[idx]),
                valor_corregido="",
            )
        )

    # Feriados por año (manteniendo la misma lógica de cache)
    for year in parsed_valid.dt.year.unique():
        if year not in holidays_cache:
            holidays_cache[year] = _get_ec_holidays(int(year))
        year_mask = parsed_valid.dt.year == year
        for idx in parsed_valid.index[year_mask]:
            if parsed_valid.loc[idx].date() in holidays_cache[year]:
                row_number = _get_row_number(row_numbers, idx)
                issues.append(
                    ValidationIssue(
                        fila=row_number,
                        fecha=fecha_iso.loc[idx],
                        tipo_error="feriado",
                        descripcion="Registro en feriado nacional ecuatoriano. Valide la autorización.",
                        valor_original=_normalize_date_output(raw_valid.loc[idx]),
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
    parsed_dates: Optional[pd.Series] = None,
    numeric_hours: Optional[pd.Series] = None,
) -> List[ValidationIssue]:
    _ensure_required_columns(df, [date_column, hours_column])
    issues: List[ValidationIssue] = []

    # Recalcular desde el DataFrame para asegurar sumatoria correcta por fecha
    parsed_dates = pd.to_datetime(
        df[date_column], errors="coerce", dayfirst=True
    )
    numeric_hours = _coerce_hours_series(df[hours_column])

    # Vectorizado: detectar horas faltantes o en 0 (misma lógica, mismas filas)
    missing_mask = numeric_hours.isna() | (numeric_hours == 0)
    for idx in numeric_hours.index[missing_mask]:
        hours_value = numeric_hours.loc[idx]
        raw_hours = df[hours_column].loc[idx]
        issues.append(
            ValidationIssue(
                fila=_get_row_number(row_numbers, idx),
                fecha=_normalize_date_output(parsed_dates.loc[idx]),
                tipo_error="horas_faltantes",
                descripcion=(
                    "Horas faltantes. Registre las horas trabajadas para este día."
                    if pd.isna(hours_value)
                    else "Horas registradas en 0. Registre las horas trabajadas para este día."
                ),
                valor_original=str(raw_hours),
                valor_corregido=f"{expected_hours:.2f}",
            )
        )

    valid_rows = parsed_dates.notna() & numeric_hours.notna() & (numeric_hours > 0)
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
    parsed_dates: Optional[pd.Series] = None,
    normalized_descriptions: Optional[pd.Series] = None,
) -> List[ValidationIssue]:
    _ensure_required_columns(df, [description_column, date_column])
    issues: List[ValidationIssue] = []

    if parsed_dates is None:
        parsed_dates = pd.to_datetime(df[date_column], errors="coerce", dayfirst=True)
    if normalized_descriptions is None:
        normalized_descriptions = df[description_column].fillna("").astype(str).str.lower().str.strip()

    working = pd.DataFrame(
        {
            "descripcion": normalized_descriptions,
            "fecha": parsed_dates,
            "row_idx": range(len(df)),
        }
    ).dropna(subset=["fecha"]).sort_values("fecha")

    previous_desc = None
    streak = 0

    for row in working.itertuples(index=False):
        current_desc = str(row.descripcion).strip().lower()
        row_number = _get_row_number(row_numbers, int(row.row_idx))
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
                    fecha=row.fecha.strftime("%Y-%m-%d"),
                    tipo_error="descripcion_repetida",
                    descripcion=(
                        f"Descripción repetida por más de {max_consecutive_identical} días consecutivos. "
                        "Aporta más detalle para diferenciar las actividades."
                    ),
                    valor_original=row.descripcion,
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
    parsed_dates: Optional[pd.Series] = None,
    normalized_descriptions: Optional[pd.Series] = None,
    enable_fuzzy: bool = True,
    fuzzy_max_text_len: int = 600,
    fuzzy_time_budget_sec: Optional[float] = 1.5,
) -> List[ValidationIssue]:
    """Detecta registros duplicados o muy similares usando fuzzy matching."""
    issues: List[ValidationIssue] = []
    import time

    _ensure_required_columns(df, [date_column, description_column, hours_column])

    work_df = df.copy()
    if normalized_descriptions is None:
        normalized_descriptions = (
            work_df[description_column]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )
    work_df["_normalized_desc"] = normalized_descriptions

    duplicate_groups = (
        work_df.groupby("_normalized_desc")
        .filter(lambda x: len(x) >= min_duplicates)
        .groupby("_normalized_desc")
    )
    index_map = work_df.groupby("_normalized_desc").indices

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

    if not enable_fuzzy:
        logger.info("validate_duplicate_entries: fuzzy matching desactivado (modo fast).")
        logger.info("validate_duplicate_entries: %d duplicados detectados", len(issues))
        return issues

    descriptions = work_df["_normalized_desc"].unique()

    # 🟢 FIX PERFORMANCE: Limitar comparaciones O(n²) a máximo 30 descripciones
    # Si hay más, solo comparar las primeras 30 para evitar timeout
    if len(descriptions) > 30:
        logger.info("Limitando fuzzy matching a primeras 30 descripciones para evitar timeout")
        descriptions = descriptions[:30]

    # Truncar textos largos solo para el fuzzy matching (no afecta valores reportados)
    fuzzy_lookup = {}
    for desc in descriptions:
        if not isinstance(desc, str):
            desc = str(desc or "")
        fuzzy_lookup[desc] = desc[:fuzzy_max_text_len]

    fuzzy_start = time.perf_counter()
    fuzzy_exceeded = False

    for i, desc1 in enumerate(descriptions):
        if not desc1 or len(desc1) < 10:
            continue
        # 🟢 FIX: Solo comparar con próximos 10 items en lugar de todos los restantes
        for desc2 in descriptions[i + 1 : i + 11]:
            if not desc2:
                continue
            if fuzzy_time_budget_sec is not None and (time.perf_counter() - fuzzy_start) > fuzzy_time_budget_sec:
                fuzzy_exceeded = True
                break
            similarity = fuzz.ratio(fuzzy_lookup.get(desc1, desc1), fuzzy_lookup.get(desc2, desc2))
            if similarity >= similarity_threshold:
                rows1 = list(index_map.get(desc1, []))
                rows2 = list(index_map.get(desc2, []))
                if len(rows1) + len(rows2) >= min_duplicates:
                    desc1_lower = desc1.lower()
                    desc2_lower = desc2.lower()
                    if (
                        any(keyword in desc1_lower for keyword in ["daily", "standup", "stand-up", "reunión diaria"])
                        and any(keyword in desc2_lower for keyword in ["daily", "standup", "stand-up", "reunión diaria"])
                    ):
                        continue
                    if parsed_dates is None:
                        fechas = work_df.loc[rows1 + rows2, date_column].apply(_normalize_date_output).tolist()
                    else:
                        fechas = parsed_dates.loc[rows1 + rows2].apply(_normalize_date_output).tolist()
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
        if fuzzy_exceeded:
            break

    if fuzzy_exceeded:
        logger.warning(
            "Fuzzy matching detenido por limite de tiempo (%.1fs). Se omitieron comparaciones adicionales.",
            fuzzy_time_budget_sec,
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
    numeric_hours: Optional[pd.Series] = None,
    normalized_descriptions: Optional[pd.Series] = None,
) -> List[ValidationIssue]:
    """Detecta horas sospechosas según el tipo de actividad."""
    issues: List[ValidationIssue] = []

    _ensure_required_columns(df, [hours_column, description_column, date_column])

    work_df = df.copy()
    if numeric_hours is None:
        numeric_hours = pd.to_numeric(work_df[hours_column], errors="coerce")
    if normalized_descriptions is None:
        normalized_descriptions = work_df[description_column].fillna("").astype(str).str.lower().str.strip()
    work_df["_hours_numeric"] = numeric_hours
    work_df["_normalized_desc"] = normalized_descriptions

    def _is_compound(description: object) -> bool:
        desc = str(description or "").strip()
        if any(token in desc for token in ["1.-", "2.-", "3.-", " • ", "\n", " -> "]):
            return True
        if desc.count(",") >= 2 or len(desc) > 120:
            return True
        return False

    def _is_simple_task(desc: object, keywords: Iterable[str]) -> bool:
        stripped = str(desc or "").strip()
        if len(stripped) > 80:
            return False
        return any(
            stripped == kw
            or stripped.startswith(f"{kw} ")
            or stripped.endswith(f" {kw}")
            for kw in keywords
        )

    idx_values = work_df.index.to_list()
    for pos, (hours, desc_lower, original_desc, raw_date) in enumerate(
        zip(
            work_df["_hours_numeric"].to_numpy(),
            work_df["_normalized_desc"].to_numpy(),
            work_df[description_column].to_numpy(),
            work_df[date_column].to_numpy(),
        )
    ):
        idx = idx_values[pos]
        fecha = _normalize_date_output(raw_date)

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
    parsed_dates: Optional[pd.Series] = None,
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
    if parsed_dates is None:
        parsed_dates = pd.to_datetime(
            df[date_column], errors='coerce', dayfirst=True
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

        # Si es num?rico, es v?lido
        if isinstance(value, numbers.Real) and not pd.isna(value):
            continue

        # Convertir a string y limpiar espacios
        value_str = str(value).strip()

        # Si est? vac?o despu?s de limpiar, tambi?n es v?lido
        if not value_str:
            continue

        # Normalizar: eliminar espacios internos
        normalized = "".join(value_str.split())
        normalized_token = re.sub(r"[^A-Za-z0-9]", "", normalized).upper()

        # Validar formato alfanum?rico
        if not normalized.isalnum():
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha=_normalize_date_output(df.at[idx, date_column]),
                    tipo_error="ticket_invalido",
                    descripcion="El ticket debe ser alfanum?rico o estar vac?o. Evite caracteres especiales.",
                    valor_original=value_str,
                    valor_corregido="",
                )
            )

    logger.info("validate_ticket_format: %d tickets inválidos detectados", len(issues))
    return issues


def validate_missing_fields(
    df: pd.DataFrame,
    *,
    date_column: str,
    hours_column: str,
    ignore_columns: Optional[Sequence[str]] = None,
    row_numbers: Optional[Sequence[int]] = None,
) -> List[ValidationIssue]:
    """
    Reporta celdas COMPLETAMENTE VACÍAS en TODAS las columnas.
    Una celda se considera vacía si:
    - Es None
    - Es NaN/NaT
    - Es un string vacío o solo espacios
    
    NO se consideran vacíos: "SN", "N/A", "0", "False", etc.
    
    OPTIMIZADO: Usa Pandas vectorizado en lugar de iterar celdas individuales.
    """
    import math
    
    issues: List[ValidationIssue] = []

    # Columnas a evaluar (excluye fecha/horas y columnas técnicas ocultas)
    def _is_hidden_or_technical_column(col_name: object) -> bool:
        name = str(col_name or "").strip()
        if not name:
            return True
        lower = name.lower()
        # Columnas basura típicas al leer plantillas con celdas ocultas/formato
        if lower.startswith("unnamed"):
            return True
        if name.startswith("_") and name[1:].isdigit():
            return True
        return False

    ignore_set = {col for col in (ignore_columns or [])}
    columns_to_check = [
        col
        for col in df.columns
        if col not in {date_column, hours_column}
        and col not in ignore_set
        and not _is_hidden_or_technical_column(col)
    ]
    if not columns_to_check:
        return issues

    # 🟢 OPTIMIZATION: Usar Pandas vectorizado en lugar de .at[] en loops
    # Detectar celdas vacías por columna
    for col in columns_to_check:
        series = df[col]
        
        # Vectorized empty detection
        is_empty_mask = (
            (series.isna()) |  # None/NaN/NaT
            ((series.astype(str).str.strip() == "") & (series.notna()))  # Empty strings
        )
        
        # Obtener índices donde hay celdas vacías
        empty_indices = is_empty_mask[is_empty_mask].index.tolist()
        
        if not empty_indices:
            continue
        
        # Para estas celdas vacías, agregar issues
        if date_column in df.columns:
            fechas = df.loc[empty_indices, date_column].apply(_normalize_date_output)
        else:
            fechas = [""] * len(empty_indices)
        
        for idx, row_idx in enumerate(empty_indices):
            row_number = _get_row_number(row_numbers, row_idx)
            fecha = fechas.iloc[idx] if isinstance(fechas, pd.Series) else ""
            
            issues.append(
                ValidationIssue(
                    fila=row_number,
                    fecha=fecha,
                    tipo_error="campo_vacio",
                    descripcion=f"Campo vacío en columna '{col}'.",
                    valor_original="",
                    valor_corregido="",
                )
            )

    logger.info("validate_missing_fields: %d campos vacíos detectados", len(issues))
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
    precomputed: Optional[Dict[str, pd.Series]] = None,
    missing_fields_ignore_columns: Optional[Sequence[str]] = None,
    duplicate_fuzzy_enabled: bool = True,
    duplicate_fuzzy_max_text_len: int = 600,
    duplicate_fuzzy_time_budget_sec: Optional[float] = 1.5,
) -> List[ValidationIssue]:
    """
    Ejecuta todas las validaciones disponibles y agrega sus resultados.

    Args:
        check_completeness: Si True, valida que todos los días laborables del mes estén registrados
        period_year: Año del periodo para validación de completitud (None = auto-detectar)
        period_month: Mes del periodo para validación de completitud (None = auto-detectar)
    """
    import time

    issues: List[ValidationIssue] = []
    precomputed = precomputed or {}
    parsed_dates = precomputed.get("parsed_dates")
    numeric_hours = precomputed.get("numeric_hours")
    normalized_descriptions = precomputed.get("normalized_description")

    def _log_timing(name: str, start: float) -> None:
        logger.info(
            "TIMING: %s %.2fs rows=%d cols=%d",
            name,
            time.perf_counter() - start,
            len(df),
            len(df.columns),
        )

    if numeric_hours is None or numeric_hours.isna().any():
        numeric_hours = _coerce_hours_series(df[hours_column])

    if parsed_dates is None or getattr(parsed_dates, "isna", None) is None:
        parsed_dates = pd.to_datetime(
            df[date_column], errors="coerce", dayfirst=True
        )

    try:
        t0 = time.perf_counter()
        issues.extend(
            validate_calendar_constraints(
                df,
                date_column=date_column,
                row_numbers=row_numbers,
                parsed_dates=parsed_dates,
            )
        )
        _log_timing("validate_calendar_constraints", t0)
    except Exception as exc:
        logger.exception("Error validando calendario: %s", exc)
        raise

    try:
        t0 = time.perf_counter()
        issues.extend(
            validate_daily_hours(
                df,
                date_column=date_column,
                hours_column=hours_column,
                expected_hours=expected_hours,
                row_numbers=row_numbers,
                parsed_dates=parsed_dates,
                numeric_hours=numeric_hours,
            )
        )
        _log_timing("validate_daily_hours", t0)
    except Exception as exc:
        logger.exception("Error validando horas diarias: %s", exc)
        raise

    if description_column:
        try:
            t0 = time.perf_counter()
            issues.extend(
                validate_description_quality(
                    df,
                    description_column=description_column,
                    min_words=min_description_words,
                    row_numbers=row_numbers,
                )
            )
            _log_timing("validate_description_quality", t0)

            if len(df) > max_consecutive_identical:
                t0 = time.perf_counter()
                issues.extend(
                    detect_copy_paste_patterns(
                        df,
                        description_column=description_column,
                        date_column=date_column,
                        max_consecutive_identical=max_consecutive_identical,
                        row_numbers=row_numbers,
                        parsed_dates=parsed_dates,
                        normalized_descriptions=normalized_descriptions,
                    )
                )
                _log_timing("detect_copy_paste_patterns", t0)
            else:
                logger.info("TIMING: detect_copy_paste_patterns omitido (pocas filas)")

            if len(df) >= duplicate_min_occurrences:
                t0 = time.perf_counter()
                issues.extend(
                    validate_duplicate_entries(
                        df,
                        date_column=date_column,
                        description_column=description_column,
                        hours_column=hours_column,
                        similarity_threshold=duplicate_similarity_threshold,
                        min_duplicates=duplicate_min_occurrences,
                        row_numbers=row_numbers,
                        parsed_dates=parsed_dates,
                        normalized_descriptions=normalized_descriptions,
                        enable_fuzzy=duplicate_fuzzy_enabled,
                        fuzzy_max_text_len=duplicate_fuzzy_max_text_len,
                        fuzzy_time_budget_sec=duplicate_fuzzy_time_budget_sec,
                    )
                )
                _log_timing("validate_duplicate_entries", t0)
            else:
                logger.info("TIMING: validate_duplicate_entries omitido (pocas filas)")

            t0 = time.perf_counter()
            issues.extend(
                validate_reasonable_hours_per_task(
                    df,
                    hours_column=hours_column,
                    description_column=description_column,
                    date_column=date_column,
                    tolerance_factor=hours_tolerance_factor,
                    row_numbers=row_numbers,
                    numeric_hours=numeric_hours,
                    normalized_descriptions=normalized_descriptions,
                )
            )
            _log_timing("validate_reasonable_hours_per_task", t0)
        except Exception as exc:
            logger.exception("Error validando descripciones: %s", exc)
            raise

    if project_column:
        try:
            t0 = time.perf_counter()
            issues.extend(
                validate_project_consistency(
                    df,
                    project_column=project_column,
                    date_column=date_column,
                    valid_projects=valid_projects,
                    row_numbers=row_numbers,
                )
            )
            _log_timing("validate_project_consistency", t0)
        except Exception as exc:
            logger.exception("Error validando proyectos: %s", exc)
            raise

    # Nueva validación: Ticket (opcional, permite valores vacíos)
    if ticket_column and ticket_column in df.columns:
        try:
            t0 = time.perf_counter()
            issues.extend(
                validate_ticket_format(
                    df,
                    ticket_column=ticket_column,
                    date_column=date_column,
                    row_numbers=row_numbers,
                )
            )
            _log_timing("validate_ticket_format", t0)
        except Exception as exc:
            logger.exception("Error validando formato de ticket: %s", exc)
            raise

    # Nueva validación: campos vacíos (informativo)
    try:
        t0 = time.perf_counter()
        issues.extend(
            validate_missing_fields(
                df,
                date_column=date_column,
                hours_column=hours_column,
                ignore_columns=missing_fields_ignore_columns,
                row_numbers=row_numbers,
            )
        )
        _log_timing("validate_missing_fields", t0)
    except Exception as exc:
        logger.exception("Error validando campos vacíos: %s", exc)
        raise

    # Nueva validación: Completitud de días laborables
    if check_completeness:
        try:
            t0 = time.perf_counter()
            issues.extend(
                validate_working_days_completeness(
                    df,
                    date_column=date_column,
                    year=period_year,
                    month=period_month,
                    row_numbers=row_numbers,
                    parsed_dates=parsed_dates,
                )
            )
            _log_timing("validate_working_days_completeness", t0)
        except Exception as exc:
            logger.exception("Error validando completitud de días laborables: %s", exc)
            raise

    return issues
