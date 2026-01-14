"""
Módulo de integración entre BatchProcessor y TimeSheetConsolidator.

Proporciona funciones de alto nivel para generar reportes consolidados
a partir de los resultados del procesamiento por lotes.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import pandas as pd

from backend.batch_processor import BatchFileResult
from backend.consolidator import ConsolidatedReport, TimeSheetConsolidator

logger = logging.getLogger(__name__)


def generate_consolidated_from_batch_results(
    batch_results: List[BatchFileResult],
    cliente: str = "NOVA - TI",
    output_filename: Optional[str] = None,
) -> ConsolidatedReport:
    """
    Genera un reporte consolidado a partir de los resultados del BatchProcessor.

    Esta función toma los archivos ya procesados y validados por el BatchProcessor
    y genera un único archivo Excel consolidado con:
    - Hoja de resumen con todos los consultores
    - Hojas individuales por consultor
    - Cálculos de facturación

    Args:
        batch_results: Resultados del BatchProcessor.process_batch()
        cliente: Nombre del cliente para el encabezado
        output_filename: Nombre del archivo de salida (None para auto-generar)

    Returns:
        ConsolidatedReport con el workbook generado y metadatos

    Raises:
        ValueError: Si no hay resultados exitosos para consolidar

    Example:
        >>> from backend.batch_processor import BatchProcessor
        >>> from backend.consolidator_integration import generate_consolidated_from_batch_results
        >>>
        >>> # Procesar archivos
        >>> batch_processor = BatchProcessor(processor)
        >>> batch_results = batch_processor.process_batch(files)
        >>>
        >>> # Generar consolidado
        >>> consolidated = generate_consolidated_from_batch_results(batch_results)
        >>> with open(consolidated.output_filename, 'wb') as f:
        ...     f.write(consolidated.workbook_bytes)
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

    # Extraer datos de cada consultor
    consultores_data: List[Tuple[pd.DataFrame, dict]] = []

    for batch_result in successful_results:
        try:
            # Obtener el DataFrame corregido
            corrected_df = batch_result.result.corrected_dataframe

            # Combinar metadata del ParsedSheet con metadata del ProcessorResult
            combined_metadata = {
                **batch_result.metadata,  # Metadata del parser (period, employee, etc.)
                **batch_result.result.metadata,  # Metadata del processor
                "file_name": batch_result.file_name,
                "client_id": batch_result.client_id,
            }

            consultores_data.append((corrected_df, combined_metadata))

            logger.debug(
                "Agregado consultor: %s (%s)",
                combined_metadata.get("employee", "Desconocido"),
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
        raise ValueError("No se pudieron extraer datos válidos de los resultados")

    # Crear consolidador y generar reporte
    consolidator = TimeSheetConsolidator(cliente=cliente)
    consolidated_report = consolidator.generate_consolidated_report(
        consultores_data=consultores_data,
        output_filename=output_filename,
    )

    logger.info("Consolidado generado exitosamente: %s", consolidated_report.output_filename)
    logger.info("Total consultores: %d", consolidated_report.consultores_incluidos)
    logger.info("Total a facturar: $%.2f", consolidated_report.total_facturar)

    return consolidated_report


def validate_batch_results_for_consolidation(
    batch_results: List[BatchFileResult],
) -> Tuple[bool, List[str]]:
    """
    Valida que los resultados del batch sean aptos para consolidación.

    Args:
        batch_results: Resultados del BatchProcessor

    Returns:
        Tupla (es_valido, lista_de_warnings)

    Example:
        >>> is_valid, warnings = validate_batch_results_for_consolidation(batch_results)
        >>> if warnings:
        ...     for warning in warnings:
        ...         print(f"⚠️ {warning}")
        >>> if is_valid:
        ...     consolidated = generate_consolidated_from_batch_results(batch_results)
    """
    warnings = []

    # Verificar que haya al menos un resultado exitoso
    successful_count = sum(1 for r in batch_results if r.success)
    if successful_count == 0:
        warnings.append("No hay archivos procesados exitosamente. No se puede generar consolidado.")
        return False, warnings

    # Verificar consistencia de periodos
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

    # Verificar nombres de consultores únicos
    nombres = []
    for result in batch_results:
        if result.success and result.metadata:
            nombre = result.metadata.get("employee")
            if nombre:
                nombres.append(nombre)

    duplicados = [nombre for nombre in nombres if nombres.count(nombre) > 1]
    if duplicados:
        warnings.append(
            f"Se detectaron consultores duplicados: {', '.join(set(duplicados))}. "
            "Verifique que no haya archivos repetidos."
        )

    # Verificar archivos con errores
    failed_count = len(batch_results) - successful_count
    if failed_count > 0:
        warnings.append(
            f"{failed_count} archivo(s) fallaron en el procesamiento y no se incluirán en el consolidado."
        )

    is_valid = successful_count > 0
    return is_valid, warnings
