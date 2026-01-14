from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from typing import Dict, Iterable, List, Optional
import re

import pandas as pd

logger = logging.getLogger(__name__)

SHEET_KEYWORDS = [
    "fecha",
    "fechas",
    "hours",
    "horas",
    "activity",
    "actividad",
    "descripcion",
    "description",
    "ticket",
    "proyecto",
    "project",
]

HEADER_KEYWORDS = [
    "fecha",
    "hours",
    "horas",
    "actividad",
    "description",
    "descripcion",
    "project",
    "proyecto",
    "task",
    "tarea",
    "rol",
    "role",
    "ticket",
    "tecnico",
    "area",
    "equipo",
]

JUNK_ROW_PATTERNS = [
    "total",
    "elaborado",
    "aprobado",
    "reporte",
    "firma",
    "repositorio",
    "sharepoint",
    "periodo",
    "periodo informe",
    "fecha del informe",
    "informe de actividades",
    "path",
    "\\\\",
    "http://",
    "https://",
]


@dataclass(frozen=True)
class ParsedSheet:
    """Hoja ya preparada para ser procesada (con encabezado y numeracion original)."""

    dataframe: pd.DataFrame
    header_row: int
    row_offset: int
    sheet_name: str
    metadata: Dict[str, object] = field(default_factory=dict)


def list_sheets(excel_bytes: bytes) -> List[str]:
    """Devuelve los nombres de todas las hojas en el Excel."""
    try:
        with pd.ExcelFile(BytesIO(excel_bytes), engine="openpyxl") as xls:
            return xls.sheet_names
    except Exception as exc:
        logger.exception("No se pudieron listar las hojas del archivo Excel: %s", exc)
        raise


def _clean_row_values(df: pd.DataFrame, index: int) -> List[str]:
    if index >= len(df):
        return []
    row = df.iloc[index]
    values = [
        str(value).strip()
        for value in row
        if pd.notna(value) and str(value).strip()
    ]
    return values


def _parse_date_from_text(text: str) -> Optional[str]:
    text = text.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    match = re.search(r"\d{1,2}/\d{1,2}/\d{4}", text)
    if match:
        return datetime.strptime(match.group(0), "%d/%m/%Y").date().isoformat()
    return None


def _extract_metadata_rows(df: pd.DataFrame) -> Dict[str, object]:
    metadata: Dict[str, object] = {}
    metadata["raw_rows"] = {}
    for idx in range(min(8, len(df))):
        metadata["raw_rows"][idx] = _clean_row_values(df, idx)

    # Row 0 title
    title_values = metadata["raw_rows"].get(0, [])
    if title_values:
        metadata["title"] = " ".join(title_values)

    # BANINTER/NOVA: posiciones flexibles para metadata de cabecera (primeras 8 filas)
    def _find_value_by_label(labels: List[str]) -> Optional[str]:
        for row_values in metadata["raw_rows"].values():
            if not row_values:
                continue
            first = str(row_values[0]).lower()
            if any(label in first for label in labels):
                return row_values[-1]
        return None

    # Fecha del informe
    for row_values in metadata["raw_rows"].values():
        if not row_values:
            continue
        row_text = " ".join(row_values)
        row_lower = row_text.lower()
        if "fecha del informe" in row_lower or "fecha informe" in row_lower:
            date_value = _parse_date_from_text(row_text.split(":")[-1])
            if date_value:
                metadata["report_date"] = date_value
                break

    # Periodo Informe (BANINTER fila 5, otros en fila 3)
    for row_values in metadata["raw_rows"].values():
        if not row_values or "periodo" not in " ".join(row_values).lower():
            continue
        combined = " ".join(row_values)
        range_match = re.search(
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*[-–]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            combined,
        )
        if range_match:
            start_raw, end_raw = range_match.groups()
            start_date = _parse_date_from_text(start_raw)
            end_date = _parse_date_from_text(end_raw)
            if start_date:
                metadata["period_start"] = start_date
                metadata["month_name"] = datetime.fromisoformat(start_date).strftime("%B")
                metadata["year"] = datetime.fromisoformat(start_date).year
            if end_date:
                metadata["period_end"] = end_date
            metadata["period_source"] = "header"
            break

    # Empresa/Cliente (BANINTER fila 2)
    company_value = _find_value_by_label(["cliente", "empresa"])
    if company_value:
        metadata["company"] = company_value

    # Consultor (BANINTER fila 6)
    employee_value = _find_value_by_label(["consultor", "empleado"])
    if employee_value:
        metadata["employee"] = employee_value

    return metadata


def _detect_date_column(df: pd.DataFrame) -> Optional[str]:
    """Intenta detectar automáticamente la columna de fechas en el dataframe."""
    date_keywords = ["fecha", "date", "dia", "day"]

    # Buscar por nombre de columna
    for col in df.columns:
        if col and any(keyword in str(col).lower() for keyword in date_keywords):
            return str(col)

    # Fallback: buscar la primera columna con fechas parseables
    for col in df.columns:
        if df[col].dtype == 'object' or 'datetime' in str(df[col].dtype):
            parsed = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
            if parsed.notna().sum() > len(df) * 0.5:  # Al menos 50% son fechas válidas
                logger.info("Columna de fecha auto-detectada por contenido: %s", col)
                return str(col)

    return None


def correct_period_from_data(
    df: pd.DataFrame,
    metadata: Dict[str, object],
    date_column: Optional[str] = None,
) -> Dict[str, object]:
    """
    Corrige el periodo declarado en metadata usando la lógica de mayoría (moda) de las fechas reales.

    PRIORIDAD: Datos reales > Metadata del encabezado

    Args:
        df: DataFrame con los datos (ya con headers)
        metadata: Metadata extraída del encabezado
        date_column: Nombre de la columna de fecha (si se conoce), sino se autodetecta

    Returns:
        Metadata corregida con periodo real detectado desde los datos
    """
    corrected = metadata.copy()

    # Detectar columna de fecha si no se proporciona
    if date_column is None:
        date_column = _detect_date_column(df)

    if not date_column or date_column not in df.columns:
        logger.warning("No se pudo detectar columna de fecha para corrección de periodo")
        return corrected

    # Parsear fechas
    parsed_dates = pd.to_datetime(
        df[date_column], errors='coerce', dayfirst=True, infer_datetime_format=True
    )
    valid_dates = parsed_dates.dropna()

    if valid_dates.empty:
        logger.warning("No hay fechas válidas para corregir el periodo")
        return corrected

    # Calcular mes y año predominantes (moda)
    month_mode = int(valid_dates.dt.month.mode().iloc[0])
    year_subset = valid_dates[valid_dates.dt.month == month_mode]
    year_mode = int(year_subset.dt.year.mode().iloc[0])

    # Calcular rango real del periodo
    month_dates = valid_dates[(valid_dates.dt.month == month_mode) & (valid_dates.dt.year == year_mode)]
    period_start_detected = month_dates.min().strftime("%Y-%m-%d")
    period_end_detected = month_dates.max().strftime("%Y-%m-%d")

    # Detectar si hay inconsistencia con la metadata
    metadata_month = None
    if "period_start" in metadata and metadata["period_start"]:
        try:
            metadata_month = datetime.fromisoformat(str(metadata["period_start"])).month
        except (ValueError, TypeError):
            pass

    # Si hay inconsistencia o no hay metadata de periodo, usar los datos reales
    if metadata_month != month_mode or "period_start" not in metadata:
        if metadata_month and metadata_month != month_mode:
            logger.warning(
                "INCONSISTENCIA DETECTADA: Metadata declara mes %s, pero datos reales son del mes %s. "
                "Usando datos reales (lógica de mayoría).",
                metadata_month,
                month_mode,
            )

        corrected["period_start"] = period_start_detected
        corrected["period_end"] = period_end_detected
        corrected["month_name"] = datetime(year_mode, month_mode, 1).strftime("%B")
        corrected["year"] = year_mode
        corrected["period_source"] = "data_corrected"
        corrected["metadata_warning"] = (
            f"Periodo corregido automáticamente desde los datos reales. "
            f"Metadata original declaraba: {metadata.get('month_name', 'N/A')} {metadata.get('year', 'N/A')}, "
            f"pero los registros corresponden a {corrected['month_name']} {year_mode}"
        )

        logger.info(
            "Periodo corregido: %s al %s (%s %s)",
            period_start_detected,
            period_end_detected,
            corrected["month_name"],
            year_mode,
        )
    else:
        logger.info("Periodo de metadata es consistente con los datos")
        corrected["period_source"] = "header_verified"

    return corrected


def _normalized_keywords(extra: Optional[Iterable[str]] = None) -> List[str]:
    keywords = HEADER_KEYWORDS.copy()
    if extra:
        keywords.extend(str(item).lower() for item in extra if item)
    return sorted(set(keywords))


def _score_sheet(df: pd.DataFrame, keywords: List[str]) -> float:
    flattened = " ".join(
        df.astype(str).fillna("").values.flatten().tolist()
    ).lower()
    score = 0.0
    if any(keyword in flattened for keyword in keywords):
        score += 50
    non_empty_rows = df.dropna(how="all").shape[0]
    if non_empty_rows > 10 and df.shape[1] > 3:
        score += 30
    score += min(non_empty_rows, 1000) / 10
    return score


def _select_best_sheet_from_excel_file(
    xls: pd.ExcelFile,
    keywords: Optional[List[str]] = None,
) -> str:
    best_sheet = None
    max_score = float("-inf")
    normalized_keywords = _normalized_keywords(keywords or SHEET_KEYWORDS)
    multiple_sheets = len(xls.sheet_names) > 1

    for sheet_name in xls.sheet_names:
        df_temp = xls.parse(sheet_name, header=None)
        sheet_score = _score_sheet(df_temp, normalized_keywords)

        # Bonus/penalizaciones segun metadata extraida (ayuda para BANINTER)
        try:
            meta = _extract_metadata_rows(df_temp)
        except Exception:
            meta = {}
        company = str(meta.get("company", "")).lower()
        if company:
            sheet_score += 15
        if "banco internacional" in company:
            sheet_score += 25
        if meta.get("period_start"):
            sheet_score += 30
            year = meta.get("year")
            if isinstance(year, int):
                # Premia periodos recientes, castiga plantillas antiguas
                if year >= 2020:
                    sheet_score += 15
                elif year < 2018:
                    sheet_score -= 15
        # Penalizar Hoja1 cuando hay varias hojas (suele ser plantilla de ejemplo)
        if multiple_sheets and sheet_name.strip().lower() == "hoja1":
            sheet_score -= 60

        if sheet_score > max_score:
            max_score = sheet_score
            best_sheet = sheet_name

    if best_sheet is None:
        raise ValueError("No se encontraron hojas validas en el archivo.")
    return best_sheet


def select_best_sheet(excel_bytes: bytes, keywords: Optional[List[str]] = None) -> str:
    """Selecciona automaticamente la hoja mas probable a partir de heuristicas."""
    with pd.ExcelFile(BytesIO(excel_bytes), engine="openpyxl") as xls:
        return _select_best_sheet_from_excel_file(xls, keywords)


def detect_header_row(
    df: pd.DataFrame,
    *,
    min_non_null: int = 2,
    keywords: Optional[List[str]] = None,
) -> int:
    """Detecta la fila de encabezado usando coincidencias de keywords y cantidad de datos."""
    normalized = _normalized_keywords(keywords)

    # Priorizar la fila que contenga más coincidencias con las keywords proporcionadas
    # (útil para plantillas como BANINTER: Fecha / Horas / Tareas).
    extra_keywords = [str(k).lower().strip() for k in (keywords or []) if k]
    if extra_keywords:
        best_row = None
        best_matches = 0
        for idx, row in df.iterrows():
            row_values = [str(val).strip().lower() for val in row if pd.notna(val)]
            if len(row_values) < min_non_null:
                continue
            row_text = " ".join(row_values)
            matches = sum(1 for keyword in extra_keywords if keyword in row_text)
            if matches > best_matches:
                best_matches = matches
                best_row = idx
        if best_row is not None and best_matches >= 2:
            logger.info("Header priorizado por coincidencias (%s) en fila %s.", best_matches, best_row)
            return best_row

    best_idx = None
    best_score = float("-inf")

    for idx, row in df.iterrows():
        row_values = [str(val).strip().lower() for val in row if pd.notna(val)]
        if len(row_values) < min_non_null:
            continue
        row_text = " ".join(row_values)
        matches = sum(1 for keyword in normalized if keyword in row_text) if normalized else 0
        score = matches * 10 + len(row_values)  # prioriza coincidencias de keywords
        if score > best_score:
            best_score = score
            best_idx = idx

    if best_idx is not None and best_score > float("-inf"):
        logger.info("Header auto-detectado en fila %s (score %s).", best_idx, best_score)
        return best_idx

    for idx, row in df.iterrows():
        if row.count() >= min_non_null:
            logger.warning("Header detectado por fallback en fila %s.", idx)
            return idx
    raise ValueError("No se pudo auto-detectar el encabezado.")


def _remove_junk_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    valid_columns = [
        col
        for col in df.columns
        if not (isinstance(col, str) and col.startswith("Unnamed"))
    ]
    if len(valid_columns) != len(df.columns):
        logger.info("Columnas 'Unnamed' removidas automaticamente.")
    return df.loc[:, valid_columns]


def _remove_junk_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    mask = pd.Series(True, index=df.index)
    first_column = df.columns[0]
    first_col_text = df[first_column].astype(str).str.lower()
    for pattern in JUNK_ROW_PATTERNS:
        mask &= ~first_col_text.str.contains(pattern, na=False)
    cleaned = df[mask].copy()
    removed = len(df) - len(cleaned)
    if removed:
        logger.info("Filas de metadata removidas automaticamente: %s", removed)
    return cleaned


def load_sheet_with_header(
    excel_bytes: bytes,
    sheet_name: Optional[str] = None,
    header_row: Optional[int] = None,
    *,
    header_keywords: Optional[List[str]] = None,
    auto_correct_period: bool = True,
) -> ParsedSheet:
    """
    Carga una hoja especifica o detecta automaticamente la mejor opcion y el encabezado.

    Args:
        excel_bytes: Bytes del archivo Excel
        sheet_name: Nombre de la hoja (None para auto-detección)
        header_row: Fila del encabezado (None para auto-detección)
        header_keywords: Keywords adicionales para detectar encabezado
        auto_correct_period: Si True, corrige automáticamente el periodo usando datos reales (lógica de mayoría)

    Returns:
        ParsedSheet con metadata corregida si auto_correct_period=True
    """
    with pd.ExcelFile(BytesIO(excel_bytes), engine="openpyxl") as xls:
        target_sheet = (
            sheet_name
            if sheet_name is not None
            else _select_best_sheet_from_excel_file(xls, header_keywords)
        )
        temp_df = xls.parse(target_sheet, header=None)

    header_idx = (
        header_row
        if header_row is not None
        else detect_header_row(temp_df, keywords=header_keywords)
    )
    metadata = _extract_metadata_rows(temp_df)
    metadata["sheet_name"] = target_sheet
    metadata["header_row"] = header_idx
    data_df = temp_df.iloc[header_idx + 1 :].copy()
    raw_columns = temp_df.iloc[header_idx].tolist()

    def _normalize_columns(columns: List[object]) -> List[str]:
        normalized: List[str] = []
        seen: Dict[str, int] = {}
        for col in columns:
            if pd.isna(col):
                col = ""
            col_str = str(col).strip()
            if col_str in seen:
                seen[col_str] += 1
                col_str = f"{col_str}_{seen[col_str]}"
            else:
                seen[col_str] = 0
            normalized.append(col_str)
        return normalized

    normalized_columns = _normalize_columns(raw_columns)
    data_df.columns = normalized_columns

    # Si el perfil trae header_keywords pero las columnas resultantes no coinciden,
    # reintentar con la fila que tenga más coincidencias de esas keywords (BANINTER).
    if header_keywords:
        hk = [str(k).lower().strip() for k in header_keywords if k]
        current_matches = sum(1 for k in hk if k in [c.lower().strip() for c in normalized_columns])
        required_matches = max(2, len(hk) // 2)
        if current_matches < required_matches:
            best_row = header_idx
            best_match = current_matches
            for idx, row in temp_df.iterrows():
                row_values = [str(val).strip().lower() for val in row if pd.notna(val)]
                matches = sum(1 for k in hk if k in row_values)
                if matches > best_match:
                    best_match = matches
                    best_row = idx
            if best_row != header_idx and best_match >= required_matches:
                header_idx = best_row
                metadata["header_row"] = header_idx
                data_df = temp_df.iloc[header_idx + 1 :].copy()
                raw_columns = temp_df.iloc[header_idx].tolist()
                normalized_columns = _normalize_columns(raw_columns)
                data_df.columns = normalized_columns
    data_df = _remove_junk_columns(data_df)
    data_df = _remove_junk_rows(data_df)
    data_df = data_df.dropna(how="all")

    # CORRECCIÓN INTELIGENTE: Usar datos reales para corregir periodo si está habilitado
    if auto_correct_period:
        metadata = correct_period_from_data(data_df, metadata)

    row_offset = header_idx + 2
    original_row_numbers = [row_offset + idx for idx in range(len(data_df))]
    data_df = data_df.reset_index(drop=True)
    data_df.attrs["original_row_numbers"] = original_row_numbers
    data_df.attrs["source_metadata"] = metadata

    return ParsedSheet(
        dataframe=data_df,
        header_row=header_idx,
        row_offset=row_offset,
        sheet_name=target_sheet,
        metadata=metadata,
    )
