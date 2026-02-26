from __future__ import annotations
from backend.models import ColumnMapping
import pandas as pd
from typing import Optional
from openpyxl import load_workbook  # <--- AGREGAR ESTO EN TUS IMPORTS
from openpyxl.utils import range_boundaries
from copy import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime
import time
from io import BytesIO
from typing import Dict, Iterable, List, Optional, Tuple
import re


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


def detect_used_range_real(
    excel_bytes: bytes,
    sheet_name: str,
    *,
    workbook: Optional[object] = None,
) -> Tuple[int, int]:
    """
    Detecta el rango real usado (max_row, max_col) basado SOLO en celdas con valores.
    Evita ws.max_row/max_column inflados por formato.
    """
    max_row = 0
    max_col = 0
    try:
        wb = workbook or load_workbook(BytesIO(excel_bytes), data_only=True)
        ws = wb[sheet_name]
        for (row, col), cell in getattr(ws, "_cells", {}).items():
            value = cell.value
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if row > max_row:
                max_row = row
            if col > max_col:
                max_col = col
        if workbook is None:
            wb.close()
    except Exception as exc:
        logger.warning("No se pudo detectar used range real: %s", exc)

    if max_row <= 0 or max_col <= 0:
        # Fallback seguro
        try:
            wb = load_workbook(BytesIO(excel_bytes), data_only=True, read_only=True)
            ws = wb[sheet_name]
            max_row = ws.max_row or 1
            max_col = ws.max_column or 1
            wb.close()
        except Exception:
            max_row = max_row or 1
            max_col = max_col or 1

    return int(max_row), int(max_col)


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
        except (KeyError, ValueError, AttributeError) as exc:
            logger.debug("No se pudo extraer metadata de la hoja %s: %s", sheet_name, exc)
            meta = {}
        except Exception as exc:
            logger.warning("Error inesperado extrayendo metadata de %s: %s", sheet_name, exc)
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
    excel_file: Optional[pd.ExcelFile] = None,
    workbook_styles: Optional[object] = None,
    workbook_values: Optional[object] = None,
) -> ParsedSheet:
    """
    Carga hoja, limpia, arregla fechas y RECONSTRUYE EL PERIODO DESDE LOS DATOS (Autoridad Total).
    """
    t_total = time.perf_counter()
    # ---------------------------------------------------------
    # 1. Carga y Detección Básica
    # ---------------------------------------------------------
    xls = excel_file
    created_excel = False
    if xls is None:
        xls = pd.ExcelFile(BytesIO(excel_bytes), engine="openpyxl")
        created_excel = True
    try:
        target_sheet = (
            sheet_name if sheet_name is not None
            else _select_best_sheet_from_excel_file(xls, header_keywords)
        )
        if workbook_values is not None:
            max_row_real, max_col_real = detect_used_range_real(
                excel_bytes, target_sheet, workbook=workbook_values
            )
        else:
            max_row_real, max_col_real = detect_used_range_real(excel_bytes, target_sheet)
        logger.info(
            "Used range real detectado en '%s': rows=%d cols=%d",
            target_sheet,
            max_row_real,
            max_col_real,
        )
        usecols = list(range(max_col_real)) if max_col_real > 0 else None
        temp_df = xls.parse(
            target_sheet,
            header=None,
            nrows=max_row_real if max_row_real > 0 else None,
            usecols=usecols,
        )
    finally:
        if created_excel:
            xls.close()

    header_idx = (
        header_row if header_row is not None
        else detect_header_row(temp_df, keywords=header_keywords)
    )
    metadata = _extract_metadata_rows(temp_df)
    metadata["sheet_name"] = target_sheet
    metadata["header_row"] = header_idx
    metadata["used_range"] = {"max_row": max_row_real, "max_col": max_col_real}
    data_df = temp_df.iloc[header_idx + 1 :].copy()
    raw_columns = temp_df.iloc[header_idx].tolist()

    # ---------------------------------------------------------
    # 🚨 FIX PREVENTIVO: Reparar Metadata Rota (Caso Víctor 2024)
    # Antes de procesar nada, arreglamos el año absurdo.
    # ---------------------------------------------------------
    if "period_start" in metadata and "period_end" in metadata:
        try:
            m_start = pd.to_datetime(metadata["period_start"])
            m_end = pd.to_datetime(metadata["period_end"])
            
            # Si Fin < Inicio, asumimos que el año de fin está mal y lo igualamos al de inicio
            if m_end < m_start:
                fixed_end = m_end.replace(year=m_start.year)
                # Si sigue siendo menor (ej: Dic 2025 - Ene 2025), sumamos 1 año
                if fixed_end < m_start:
                    fixed_end = fixed_end.replace(year=m_start.year + 1)
                
                new_end_str = fixed_end.strftime("%Y-%m-%d")
                metadata["period_end"] = new_end_str
                metadata["period_source"] = "metadata_early_fix"
                logger.info(f"✅ Metadata reparada preventivamente: {new_end_str}")
        except: pass

    # Normalización de columnas
    def _normalize_columns(columns: List[object]) -> List[str]:
        normalized: List[str] = []
        seen: Dict[str, int] = {}
        for col in columns:
            if pd.isna(col): col = ""
            col_str = str(col).strip()
            if col_str in seen: seen[col_str] += 1; col_str = f"{col_str}_{seen[col_str]}"
            else: seen[col_str] = 0
            normalized.append(col_str)
        return normalized

    def _assign_columns_safe(df: pd.DataFrame, columns: List[str]) -> List[str]:
        cols = list(columns)
        if len(cols) != df.shape[1]:
            if len(cols) > df.shape[1]:
                cols = cols[: df.shape[1]]
            else:
                extra = df.shape[1] - len(cols)
                cols = cols + [f"Col_{i+1}" for i in range(extra)]
        try:
            df.columns = cols
        except ValueError:
            # Fallback absoluto: evitar crash por desalineacion
            df.columns = [f"Col_{i+1}" for i in range(df.shape[1])]
            return list(df.columns)
        return cols

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
            logger.info("Columnas vacias removidas: %d", len(drop_cols))
            return df.drop(columns=drop_cols)
        return df

    normalized_columns = _normalize_columns(raw_columns)
    normalized_columns = _assign_columns_safe(data_df, normalized_columns)

    # Reintento de Header
    if header_keywords:
        hk = [str(k).lower().strip() for k in header_keywords if k]
        curr = sum(1 for k in hk if k in [c.lower().strip() for c in normalized_columns])
        if curr < max(2, len(hk) // 2):
            best_r, best_m = header_idx, curr
            for idx, row in temp_df.iterrows():
                m = sum(1 for k in hk if k in [str(v).lower() for v in row if pd.notna(v)])
                if m > best_m: best_r, best_m = idx, m
            if best_r != header_idx and best_m >= max(2, len(hk) // 2):
                header_idx = best_r
                metadata["header_row"] = header_idx
                data_df = temp_df.iloc[best_r + 1 :].copy()
                raw_columns = temp_df.iloc[header_idx].tolist()
                normalized_columns = _normalize_columns(raw_columns)
                normalized_columns = _assign_columns_safe(data_df, normalized_columns)

    data_df = _remove_junk_columns(data_df)
    data_df = _remove_junk_rows(data_df)
    object_like_cols = data_df.select_dtypes(include=["object", "string"]).columns
    if len(object_like_cols) > 0:
        with pd.option_context("future.no_silent_downcasting", True):
            data_df[object_like_cols] = (
                data_df[object_like_cols]
                .replace(r"^\s*$", pd.NA, regex=True)
                .infer_objects(copy=False)
            )
    data_df = data_df.dropna(how="all")
    data_df = _drop_empty_columns(data_df)

    # ---------------------------------------------------------
    # 2.1. Capturar footer original (contenido debajo de la tabla)
    # ---------------------------------------------------------
    footer_rows: List[List[object]] = []
    footer_block = None
    
    # NO CAPTURAMOS FOOTER AQUÍ PORQUE LUEGO VIENE _remove_junk_rows
    # que elimina las filas que detectamos como footer (tiene "Total", "Elaborado", etc)
    # Mejor dejar que se eliminen del DataFrame pero guardaremos la info del footer
    # al leer openpyxl directamente más abajo

    # ---------------------------------------------------------
    # 2. CAZAFANTASMAS: Limpiar filas vacías
    # ---------------------------------------------------------
    date_col = _detect_date_column(data_df)
    hours_col = None
    for c in data_df.columns:
        if any(x in str(c).lower() for x in ["hora", "hours", "tiempo"]):
            hours_col = c
            break
            
    if date_col and hours_col:
        rows_before = len(data_df)
        data_df = data_df.dropna(subset=[date_col, hours_col], how="all")

        desc_col = None
        for c in data_df.columns:
            if any(x in str(c).lower() for x in ["actividad", "descrip", "tarea", "task"]):
                desc_col = c
                break

        missing_date = data_df[date_col].isna() | data_df[date_col].astype(str).str.strip().eq("")
        hours_num = pd.to_numeric(data_df[hours_col], errors="coerce")
        missing_hours = hours_num.isna() | hours_num.eq(0)

        if desc_col:
            desc_clean = data_df[desc_col].fillna("").astype(str).str.strip()
            desc_lower = desc_clean.str.lower()
            desc_has_text = desc_clean.ne("") & ~desc_clean.isin({"-", "---"})
            desc_is_summary = desc_lower.str.startswith(("total", "resumen", "suma", "acumulado"))
            desc_has_metadata_token = desc_lower.str.contains(
                r"(?:elaborado|aprobado|firma|periodo|fecha del informe|cliente|consultor|"
                r"recurso|repositorio|sharepoint|informe de actividades|http://|https://|\\\\)",
                na=False,
            )
            mask_ghost = missing_date & missing_hours & (
                ~desc_has_text | desc_is_summary | desc_has_metadata_token
            )
        else:
            mask_ghost = missing_date & missing_hours
        data_df = data_df[~mask_ghost]
        if len(data_df) != rows_before:
            logger.info(f"Filas fantasma eliminadas: {rows_before - len(data_df)}")

    # ---------------------------------------------------------
    # 3. CORRECCIÓN AVANZADA DE FECHAS (El FIX de Johanna)
    # ---------------------------------------------------------
    if date_col:
        try:
            # Forzar dayfirst=True para arreglar formato Latino
            data_df[date_col] = pd.to_datetime(data_df[date_col], dayfirst=True, errors='coerce')
            
            series = data_df[date_col]
            unique_months = series.dt.to_period("M").nunique()
            
            # Inversión Heurística (Si hay muchos meses dispersos)
            if unique_months > 2:
                logger.warning(f"⚠️ Dispersión alta ({unique_months} meses). Chequeando inversión...")
                mask_swap = (series.dt.day <= 12) & series.notna()
                if mask_swap.any():
                    subset = series[mask_swap]
                    swap_df = pd.DataFrame({'year': subset.dt.year, 'month': subset.dt.day, 'day': subset.dt.month})
                    candidate = series.copy()
                    candidate.loc[swap_df.index] = pd.to_datetime(swap_df)
                    if candidate.dt.to_period("M").nunique() < unique_months:
                        data_df[date_col] = candidate
                        logger.info("🔄 SWAP APLICADO POR COHERENCIA DE DATOS.")

            data_df[date_col] = data_df[date_col].dt.strftime('%Y-%m-%d')
            
        except Exception as e:
            logger.warning(f"Error procesando fechas: {e}")

    # ---------------------------------------------------------
    # 4. 🔥 AUTORIDAD DE DATOS FINAL: Reconstruir Periodo desde 'Fecha' 🔥
    # ---------------------------------------------------------
    # Este paso es clave: Sobrescribe la metadata con lo que realmente dicen los datos.
    # Arregla el caso de "30 de Octubre" cuando hay datos del "31".
    if auto_correct_period and date_col and not data_df.empty:
        try:
            real_dates = pd.to_datetime(data_df[date_col], errors='coerce').dropna()
            
            if not real_dates.empty:
                # 1. Calculamos el mes real predominante
                mode_year = real_dates.dt.year.mode()[0]
                mode_month = real_dates.dt.month.mode()[0]
                
                # 2. Calculamos el último día teórico de ese mes (ej: 31)
                import calendar
                last_day = calendar.monthrange(mode_year, mode_month)[1]
                
                new_start = datetime(mode_year, mode_month, 1).strftime("%Y-%m-%d")
                new_end = datetime(mode_year, mode_month, last_day).strftime("%Y-%m-%d")
                
                # 3. Forzamos la actualización de la metadata
                metadata["period_start"] = new_start
                metadata["period_end"] = new_end
                metadata["month_name"] = datetime(mode_year, mode_month, 1).strftime("%B")
                metadata["year"] = mode_year
                metadata["period_source"] = "data_authority_final"
                
                logger.info(f"✅ Periodo Autoridad Datos: {new_start} al {new_end}")

        except Exception as e:
            logger.error(f"Error reconstruyendo periodo final: {e}")

    # ---------------------------------------------------------
    # 5. Retorno
    # ---------------------------------------------------------
    row_offset = header_idx + 2
    original_row_numbers = [row_offset + idx for idx in range(len(data_df))]
    data_df = data_df.reset_index(drop=True)
    data_df.attrs["original_row_numbers"] = original_row_numbers
    data_df.attrs["source_metadata"] = metadata

    # Captura avanzada con estilos (openpyxl)
    try:
        wb = workbook_styles or load_workbook(BytesIO(excel_bytes), data_only=False)
        wb_values = workbook_values or load_workbook(BytesIO(excel_bytes), data_only=True)
        ws = wb[target_sheet]
        ws_values = wb_values[target_sheet]

        try:
            # Determinar última fila de datos: usar el máximo de original_row_numbers
            # (es la fila más alta del dataframe limpio que ya ha sido procesado)
            data_end_row = max(original_row_numbers) if original_row_numbers else header_idx + 1

            # Refinar buscando la ÚLTIMA FILA CON FECHA VÁLIDA desde el final hacia atrás
            # Esto ayuda a capturar filas que pueden haber sido removidas del dataframe
            # pero que son datos reales (no footer)
            try:
                header_ws_row = header_idx + 1
                date_idx = None
                if date_col and date_col in normalized_columns:
                    date_idx = normalized_columns.index(date_col) + 1

                def _is_date_value(value: object) -> bool:
                    if value is None or value == "":
                        return False
                    if isinstance(value, (date, datetime)):
                        return True
                    text = str(value).strip()
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
                        try:
                            datetime.strptime(text, fmt)
                            return True
                        except ValueError:
                            continue
                    return False

                if date_idx:
                    # Buscar desde el final hacia atrás para encontrar la última fecha válida
                    for r in range(ws.max_row, header_ws_row, -1):
                        if _is_date_value(ws.cell(row=r, column=date_idx).value):
                            data_end_row = r
                            logger.debug(f"Última fila con fecha válida encontrada: {r}")
                            break
            except Exception as e:
                logger.debug(f"Error refinando data_end_row: {e}")

            footer_start = data_end_row + 1
            # Footer end: usar used range real para evitar rangos inflados por formato
            used_range = metadata.get("used_range") or {}
            max_row_real = int(used_range.get("max_row") or ws.max_row or 1)
            max_col_real = int(used_range.get("max_col") or ws.max_column or 1)
            footer_end = max_row_real

            logger.debug(f"Footer range: {footer_start} - {footer_end} (data_end: {data_end_row})")

            if footer_start <= footer_end:
                max_col = max_col_real
                cells = []
                row_heights: Dict[int, float] = {}
                merge_ranges = []
                merged_coords = set()

                for merge_range in ws.merged_cells.ranges:
                    min_col, min_row, max_col_m, max_row = range_boundaries(str(merge_range))
                    if min_row >= footer_start and min_row <= footer_end:
                        merge_ranges.append((min_row, min_col, max_row, max_col_m))
                        for r in range(min_row, max_row + 1):
                            for c in range(min_col, max_col_m + 1):
                                merged_coords.add((r, c))

                cells_iterated = 0
                for r in range(footer_start, footer_end + 1):
                    height = ws.row_dimensions[r].height
                    if height:
                        row_heights[r] = height
                    for c in range(1, max_col + 1):
                        cell = ws.cell(row=r, column=c)
                        value_cell = ws_values.cell(row=r, column=c)
                        # Para el footer, capturar TODAS las celdas, incluyendo las vacías
                        # porque pueden tener estilos o ser parte de la estructura
                        cells_iterated += 1
                        cells.append(
                            {
                                "row": r,
                                "col": c,
                                "value": value_cell.value,
                                "font": copy(cell.font),
                                "fill": copy(cell.fill),
                                "border": copy(cell.border),
                                "alignment": copy(cell.alignment),
                                "number_format": cell.number_format,
                            }
                        )

                if cells or row_heights or merge_ranges:
                    footer_block = {
                        "data_end_row": data_end_row,
                        "start_row": footer_start,
                        "max_row": footer_end,
                        "max_col": max_col,
                        "cells": cells,
                        "row_heights": row_heights,
                        "merges": merge_ranges,
                    }
                logger.info(
                    "Footer capture: filas=%d cols=%d celdas_iteradas=%d",
                    (footer_end - footer_start + 1),
                    max_col,
                    cells_iterated,
                )
        finally:
            if workbook_styles is None:
                wb.close()
            if workbook_values is None:
                wb_values.close()
    except Exception as exc:
        logger.warning(f"No se pudo capturar footer con estilos: {exc}")

    if footer_block:
        metadata["footer_block"] = footer_block
    logger.info("TIMING: excel_parser.total %.2fs", time.perf_counter() - t_total)


    return ParsedSheet(data_df, header_idx, row_offset, target_sheet, metadata)

# ==========================================
# FUNCIÓN NUEVA: AÑADIDA AL FINAL CORRECTAMENTE
# ==========================================

def load_multiple_sheets(
    excel_bytes: bytes,
    *,
    header_keywords: Optional[List[str]] = None,
    auto_correct_period: bool = True,
) -> List[ParsedSheet]:
    """
    Carga TODAS las hojas VISIBLES del Excel, EXCEPTO la hoja 'Resumen'.
    Ignora hojas ocultas (Hidden/VeryHidden).
    """
    results: List[ParsedSheet] = []
    
    # ---------------------------------------------------------
    # 1. Obtener SOLO nombres de hojas VISIBLES usando openpyxl
    # ---------------------------------------------------------
    visible_sheet_names = []
    workbook_values = None
    workbook_styles = None
    try:
        workbook_values = load_workbook(BytesIO(excel_bytes), data_only=True)
        workbook_styles = load_workbook(BytesIO(excel_bytes), data_only=False)

        for sheet in workbook_values.worksheets:
            # sheet_state puede ser 'visible', 'hidden' o 'veryHidden'
            if sheet.sheet_state == 'visible':
                visible_sheet_names.append(sheet.title)
            else:
                logger.info(f"🙈 Ignorando hoja oculta: '{sheet.title}'")
    except Exception as e:
        logger.error(f"Error filtrando hojas ocultas: {e}")
        # Fallback: si falla openpyxl, usamos pandas (aunque traerá las ocultas)
        try:
            visible_sheet_names = list_sheets(excel_bytes)
        except Exception:
            return []
        workbook_values = None
        workbook_styles = None

    logger.info(f"Hojas visibles a procesar: {visible_sheet_names}")

    # ---------------------------------------------------------
    # 2. Recorrer y filtrar
    # ---------------------------------------------------------
    excel_file = None
    try:
        excel_file = pd.ExcelFile(BytesIO(excel_bytes), engine="openpyxl")
    except Exception as e:
        logger.warning(f"No se pudo abrir ExcelFile para cachear parseo: {e}")
        excel_file = None

    try:
        for name in visible_sheet_names:
            try:
                lower_name = name.strip().lower()
                if lower_name in {"datos", "resumen", "catalogo", "catálogo", "listas", "pivot"}:
                    logger.info("Ignorando hoja auxiliar: '%s'", name)
                    continue
                # --- FILTRO MAESTRO ---
                # Si el nombre contiene "resumen", lo ignoramos.
                if "resumen" in name.lower():
                    logger.info(f"🚫 Ignorando hoja '{name}' (es el resumen viejo).")
                    continue

                # Opcional: Ignorar hojas de sistema/temporales
                if name.startswith("_") or "consolidado" in name.lower():
                    continue

                # 3. Procesar hoja de Empleado
                logger.info(f"Intentando cargar hoja de empleado: {name}")

                parsed = load_sheet_with_header(
                    excel_bytes,
                    sheet_name=name,  # Forzamos esta hoja específica
                    header_keywords=header_keywords,
                    auto_correct_period=auto_correct_period,
                    excel_file=excel_file,
                    workbook_styles=workbook_styles,
                    workbook_values=workbook_values,
                )

                # Solo guardamos si tiene datos (filas > 0)
                if not parsed.dataframe.empty and len(parsed.dataframe) > 0:
                    # Si la metadata no trajo el nombre del empleado, usamos el nombre de la hoja
                    if "employee" not in parsed.metadata:
                        parsed.metadata["employee"] = name

                    results.append(parsed)
                    logger.info(f"✅ Empleado '{name}' cargado correctamente.")

            except Exception:
                # Si falla (porque no tiene columnas de Fecha/Horas), asumimos que no es un timesheet
                logger.warning(f"⚠️ La hoja '{name}' no parece un timesheet válido. Se omite.")
    finally:
        if excel_file is not None:
            excel_file.close()
        if workbook_styles is not None:
            workbook_styles.close()
        if workbook_values is not None:
            workbook_values.close()

    return results

def infer_column_mapping(df: pd.DataFrame, profile_mapping: dict) -> Optional[ColumnMapping]:
    """
    Intenta inferir el mapeo de columnas dando PRIORIDAD EXPLICITA al perfil configurado.
    Si el perfil falla, usa heurísticas.
    """

    def norm(x: object) -> str:
        return re.sub(r"\s+", " ", str(x).strip().lower())

    cols = list(df.columns)
    cols_norm = {norm(c): c for c in cols}  # normalizado -> nombre real

    def resolve_by_profile(expected: Optional[str]) -> Optional[str]:
        """Busca la columna REAL del df que corresponde al nombre esperado del perfil."""
        if not expected:
            return None
        e = norm(expected)

        # 1. Match exacto normalizado
        if e in cols_norm:
            return cols_norm[e]

        # 2. Match por contención estricta (útil si el Excel trae "Actividad (Detalle)")
        for c in cols:
            if e in norm(c):
                return c
        return None

    def find_col(possible_names: List[str]) -> Optional[str]:
        """Busca por keywords dentro de las columnas reales."""
        poss = [norm(p) for p in possible_names]
        
        # MEJORA: Iterar primero por keywords, luego por columnas.
        # Esto asegura que si buscamos "actividad" antes que "descripcion", 
        # encuentre "actividad" aunque esté en una columna posterior.
        for p in poss:
            for c in cols:
                cl = norm(c)
                if p in cl:
                    return c
        return None

    # --- CAMBIO CLAVE AQUÍ ---
    # 1. Intentar resolver usando el mapeo del perfil (JSON) PRIMERO
    date_col    = resolve_by_profile(profile_mapping.get("date"))
    hours_col   = resolve_by_profile(profile_mapping.get("hours"))
    desc_col    = resolve_by_profile(profile_mapping.get("description"))
    project_col = resolve_by_profile(profile_mapping.get("project"))

    # 2. Si no se encontró en el perfil, usar heurísticas (Auto-detección)
    # Nota: He reordenado las keywords para poner "actividad" antes que "descripcion" por si acaso.
    if not date_col:
        date_col = find_col(["fecha", "date", "día", "dia"])
    
    if not hours_col:
        hours_col = find_col(["hora", "horas", "hours", "tiempo"])
    
    if not desc_col:
        # Aquí "actividad" va primero para darle preferencia en la búsqueda heurística
        desc_col = find_col(["actividad", "task", "tareas", "tarea", "descripcion", "descripción", "detalle"])
    
    if not project_col:
        project_col = find_col(["proyecto", "tipo actividad", "project"])

    # Validación final
    if not date_col or not hours_col or not desc_col:
        return None

    return ColumnMapping(
        date=date_col,
        hours=hours_col,
        description=desc_col,
        project=project_col,
    )
