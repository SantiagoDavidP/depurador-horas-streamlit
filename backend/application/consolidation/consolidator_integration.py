"""
Módulo de integración entre BatchProcessor y TimeSheetConsolidator.
CORREGIDO: 
1. Estructura de datos: Vuelve a usar TUPLAS (df, metadata) para compatibilidad.
2. Mantiene la normalización de columnas (FECHA -> Fecha).
3. LIMPIEZA: Elimina columnas basura (_1, _2, Unnamed) generadas por formatos sucios.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple, Dict, Any

from backend.application.batch.batch_processor import BatchFileResult
from backend.application.ports.collaborator_rates_port import CollaboratorRatesPort
from backend.application.consolidation.models import ConsolidatedReport
from backend.application.ports.timesheet_reporting_port import TimesheetReportingPort
from backend.application.tabular.table_data import TableData
from backend.shared.tabular.pandas_mapper import from_pandas_table, to_pandas_table

logger = logging.getLogger(__name__)


def generate_consolidated_from_batch_results(
    batch_results: List[BatchFileResult],
    cliente: str = "NOVA - TI",
    output_filename: Optional[str] = None,
    reporting_port: Optional[TimesheetReportingPort] = None,
    collaborator_rates: Optional[CollaboratorRatesPort] = None,
) -> ConsolidatedReport:
    """
    Genera un reporte consolidado a partir de los resultados del BatchProcessor.
    """
    logger.info("Iniciando generación de consolidado desde %d resultados de batch", len(batch_results))

    # Filtrar solo resultados exitosos
    successful_results = [r for r in batch_results if r.success and r.result]

    if not successful_results:
        raise ValueError(
            "No hay resultados exitosos para consolidar. "
            "Asegúrese de que al menos un archivo haya sido procesado correctamente."
        )

    logger.info("Resultados exitosos: %d/%d", len(successful_results), len(batch_results))

    # ⚠️ CAMBIO CRÍTICO: Lista de TUPLAS (DataFrame, dict), no diccionarios.
    consultores_data: List[Tuple[TableData, dict]] = []

    for batch_result in successful_results:
        try:
            res = batch_result.result
            df = to_pandas_table(res.corrected_dataframe)

            # =========================================================
            # 🛡️ RED DE SEGURIDAD: NORMALIZACIÓN DE COLUMNAS
            # =========================================================
            rename_map = {}
            
            # 1. Usar detección del sistema
            date_col_name = getattr(res, "date_column", None)
            hours_col_name = getattr(res, "hours_column", None)
            desc_col_name = getattr(res, "description_column", None)

            if date_col_name and date_col_name in df.columns:
                rename_map[date_col_name] = "Fecha"
            if hours_col_name and hours_col_name in df.columns:
                rename_map[hours_col_name] = "Horas"
            if desc_col_name and desc_col_name in df.columns:
                rename_map[desc_col_name] = "Actividad"
            
            df = df.rename(columns=rename_map)

            # 2. Plan B: Búsqueda flexible
            if "Fecha" not in df.columns:
                for col in df.columns:
                    c_lower = str(col).lower().strip()
                    if c_lower in ["fecha", "date", "fec"]:
                        df.rename(columns={col: "Fecha"}, inplace=True)
                        break
            
            if "Horas" not in df.columns:
                for col in df.columns:
                    c_lower = str(col).lower().strip()
                    if c_lower in ["horas", "hours", "hrs", "tiempo", "time"]:
                        df.rename(columns={col: "Horas"}, inplace=True)
                        break

            if "Actividad" not in df.columns:
                for col in df.columns:
                    c_lower = str(col).lower().strip()
                    if any(x in c_lower for x in ["actividad", "descrip", "task", "tarea"]):
                        df.rename(columns={col: "Actividad"}, inplace=True)
                        break

            # =========================================================
            # 🧹 LIMPIEZA DE COLUMNAS BASURA (_1, _2, etc.)
            # =========================================================
            # Eliminamos columnas que pandas genera cuando hay celdas vacias con formato
            cols_to_keep = []
            for col in df.columns:
                c_str = str(col).strip()
                # Si empieza con "_" seguido de un numero (ej: _1, _14) es basura
                if c_str.startswith("_") and c_str[1:].isdigit():
                    continue
                # Si es "Unnamed", es basura
                if "unnamed" in c_str.lower():
                    continue
                cols_to_keep.append(col)
            
            df = df[cols_to_keep]

            # =========================================================
            # 3️⃣ Preparar Metadata
            # =========================================================
            meta = batch_result.metadata or {}
            res_meta = batch_result.result.metadata or {}
            
            employee_name = (
                meta.get("employee") 
                or res_meta.get("employee") 
                or batch_result.sheet_name 
                or "Desconocido"
            )

            combined_metadata = {
                **meta,
                **res_meta,
                "employee": employee_name, # Asegurar que el nombre esté aquí
                "file_name": batch_result.file_name,
                "client_id": batch_result.client_id,
            }

            # =========================================================
            # 4️⃣ Agregar como TUPLA (df, metadata)
            # =========================================================
            consultores_data.append((from_pandas_table(df), combined_metadata))

            logger.debug(
                "Agregado consultor: %s (%s)",
                employee_name,
                batch_result.file_name,
            )

        except Exception as exc:
            logger.error(
                "Error extrayendo datos de %s: %s",
                batch_result.file_name,
                exc,
            )
            continue

    if not consultores_data:
        raise ValueError("No se pudieron extraer datos válidos. Verifique columnas Fecha/Horas.")

    # Crear consolidador
    if reporting_port is None:
        raise RuntimeError("Timesheet reporting port is not configured.")

    consolidated_report = reporting_port.generate_consolidated_report(
        cliente=cliente,
        consultores_data=consultores_data, 
        output_filename=output_filename,
        collaborator_rates=collaborator_rates,
    )

    logger.info("Consolidado generado exitosamente: %s", consolidated_report.output_filename)
    logger.info("Total consultores: %d", consolidated_report.consultores_incluidos)
    logger.info("Total a facturar: $%.2f", consolidated_report.total_facturar)

    return consolidated_report


def generate_individual_business_it_excel(
    batch_result: BatchFileResult,
    cliente: str = "BANINTER",
    reporting_port: Optional[TimesheetReportingPort] = None,
    collaborator_rates: Optional[CollaboratorRatesPort] = None,
) -> Tuple[bytes, str]:
    """
    Genera un Excel individual con formato Business IT a partir de un resultado procesado.
    """
    if not (batch_result.success and batch_result.result):
        raise ValueError("El resultado no es vÃ¡lido para generar reporte individual.")

    res = batch_result.result
    df = to_pandas_table(res.corrected_dataframe)

    # Normalización defensiva de columnas para plantillas BANINTER variables
    rename_map = {}
    date_col_name = getattr(res, "date_column", None)
    hours_col_name = getattr(res, "hours_column", None)
    desc_col_name = getattr(res, "description_column", None)
    if date_col_name and date_col_name in df.columns:
        rename_map[date_col_name] = "Fecha"
    if hours_col_name and hours_col_name in df.columns:
        rename_map[hours_col_name] = "Horas"
    if desc_col_name and desc_col_name in df.columns:
        rename_map[desc_col_name] = "Actividad"
    if rename_map:
        df = df.rename(columns=rename_map)

    if "Fecha" not in df.columns:
        for col in df.columns:
            c = str(col).lower().strip()
            if c in {"fecha", "date", "fecha\ndd/mm/yyyy"} or "fecha" in c:
                df.rename(columns={col: "Fecha"}, inplace=True)
                break
    if "Horas" not in df.columns:
        for col in df.columns:
            c = str(col).lower().strip()
            if c in {"horas", "hours", "hrs", "tiempo"} or "hora" in c:
                df.rename(columns={col: "Horas"}, inplace=True)
                break
    if "Actividad" not in df.columns:
        for col in df.columns:
            c = str(col).lower().strip()
            if any(x in c for x in ["actividad", "tarea", "detalle", "descrip", "task"]):
                df.rename(columns={col: "Actividad"}, inplace=True)
                break
    # Quitar columnas ocultas/sistema (_1, _2, ... y Unnamed)
    cols_to_keep = []
    for col in df.columns:
        c_str = str(col).strip()
        if c_str.startswith("_") and c_str[1:].isdigit():
            continue
        if "unnamed" in c_str.lower():
            continue
        cols_to_keep.append(col)
    df = df[cols_to_keep]
    metadata = {
        **(batch_result.metadata or {}),
        **(res.metadata or {}),
    }
    if not metadata.get("employee"):
        metadata["employee"] = (
            batch_result.sheet_name
            or batch_result.file_name.rsplit(".", 1)[0]
        )

    if reporting_port is None:
        raise RuntimeError("Timesheet reporting port is not configured.")

    workbook_bytes = reporting_port.generate_single_consultant_report(
        cliente=cliente,
        dataframe=from_pandas_table(df),
        metadata=metadata,
        collaborator_rates=collaborator_rates,
    )
    source_stem = (batch_result.file_name or "").rsplit(".", 1)[0].strip()
    employee_safe = str(metadata["employee"]).replace(" ", "_")
    if source_stem:
        source_safe = source_stem.replace(" ", "_")
        output_name = f"{employee_safe}_BusinessIT_{source_safe}.xlsx"
    else:
        output_name = f"{employee_safe}_BusinessIT.xlsx"
    return workbook_bytes, output_name


def validate_batch_results_for_consolidation(
    batch_results: List[BatchFileResult],
) -> Tuple[bool, List[str]]:
    """
    Valida que los resultados del batch sean aptos para consolidación.
    """
    warnings = []

    successful_count = sum(1 for r in batch_results if r.success)
    if successful_count == 0:
        warnings.append("No hay archivos procesados exitosamente. No se puede generar consolidado.")
        return False, warnings

    periodos = set()
    for result in batch_results:
        if result.success and result.metadata:
            periodo_key = (
                result.metadata.get("year"),
                result.metadata.get("month_name"),
            )
            if periodo_key != (None, None):
                periodos.add(periodo_key)

    if len(periodos) > 1:
        warnings.append(
            f"Los archivos contienen {len(periodos)} periodos diferentes. "
            "Se recomienda consolidar archivos del mismo mes."
        )

    def _is_baninter(result: BatchFileResult) -> bool:
        if result.client_id == "cliente_talent":
            return True
        company = (result.metadata or {}).get("company")
        if company and any(k in str(company).lower() for k in ["baninter", "banco internacional"]):
            return True
        return False

    is_baninter = any(_is_baninter(r) for r in batch_results if r.success)

    nombres = []
    for result in batch_results:
        if result.success and result.metadata:
            nombre = result.metadata.get("employee")
            if nombre:
                nombres.append(nombre)

    if not is_baninter:
        duplicados = [nombre for nombre in nombres if nombres.count(nombre) > 1]
        if duplicados:
            warnings.append(
                f"Se detectaron consultores duplicados: {', '.join(set(duplicados))}. "
                "Verifique que no haya archivos repetidos."
            )

    failed_count = len(batch_results) - successful_count
    if failed_count > 0:
        warnings.append(
            f"{failed_count} archivo(s) fallaron en el procesamiento y no se incluirán en el consolidado."
        )

    is_valid = successful_count > 0
    return is_valid, warnings
