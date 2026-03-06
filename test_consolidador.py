"""
Script de prueba standalone para el Consolidador de Reportes.

Este script permite probar la funcionalidad del consolidador sin usar la interfaz
de Streamlit, útil para debugging y validación rápida.

Uso:
    python test_consolidador.py --input ./archivos_procesados --output consolidado.xlsx
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Tuple

import pandas as pd

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.consolidator import TimeSheetConsolidator
from backend.batch_processor import BatchFileRequest, BatchProcessor
from backend.processor import ColumnMapping, TimeSheetProcessor
from backend.excel_parser import load_sheet_with_header
from backend.infrastructure.composition.processing_factory import build_timesheet_processor
from backend.infrastructure.config.collaborator_rates_repository import get_collaborator_rates_manager
from backend.infrastructure.parsing.excel_sheet_parser_adapter import ExcelSheetParserAdapter

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_data() -> List[Tuple[pd.DataFrame, dict]]:
    """
    Crea datos de ejemplo para testing (útil si no tienes archivos reales).

    Returns:
        Lista de tuplas (dataframe, metadata) de 3 consultores ficticios
    """
    import datetime

    consultores_data = []

    # Consultor 1: Mateo Granja (Senior)
    df1 = pd.DataFrame({
        'Fecha': ['2025-10-01', '2025-10-02', '2025-10-03'] * 7,  # 21 días
        'Horas': [8.0] * 21,
        'Actividad': ['Desarrollo'] * 10 + ['Reunión'] * 6 + ['Code Review'] * 5,
        'Descripción': ['Implementación feature X'] * 21,
        'Tipo Hora': ['HN'] * 19 + ['HE'] * 2,  # 2 horas extras
    })
    metadata1 = {
        'employee': 'Mateo Granja',
        'cargo': 'Senior',
        'month_name': 'October',
        'year': 2025,
        'period_start': '2025-10-01',
        'period_end': '2025-10-31',
    }
    consultores_data.append((df1, metadata1))

    # Consultor 2: Miguel Baquero (Semisenior)
    df2 = pd.DataFrame({
        'Fecha': ['2025-10-01', '2025-10-02', '2025-10-03'] * 7,
        'Horas': [8.0] * 21,
        'Actividad': ['Testing'] * 15 + ['Documentación'] * 6,
        'Descripción': ['Pruebas del módulo Y'] * 21,
        'Tipo Hora': ['HN'] * 21,
    })
    metadata2 = {
        'employee': 'Miguel Baquero',
        'cargo': 'Semisenior',
        'month_name': 'October',
        'year': 2025,
        'period_start': '2025-10-01',
        'period_end': '2025-10-31',
    }
    consultores_data.append((df2, metadata2))

    # Consultor 3: Pablo Guanoluisa (Junior, solo 17 días)
    df3 = pd.DataFrame({
        'Fecha': ['2025-10-01', '2025-10-02', '2025-10-03'] * 6,  # 18 registros = 17 días únicos
        'Horas': [8.0] * 17 + [4.0],  # Último día medio día
        'Actividad': ['Desarrollo'] * 18,
        'Descripción': ['Soporte técnico'] * 18,
        'Tipo Hora': ['HN'] * 18,
    })
    metadata3 = {
        'employee': 'Pablo Guanoluisa',
        'cargo': 'Junior',
        'month_name': 'October',
        'year': 2025,
        'period_start': '2025-10-01',
        'period_end': '2025-10-31',
    }
    consultores_data.append((df3, metadata3))

    return consultores_data


def process_files_from_directory(input_dir: Path) -> List[Tuple[pd.DataFrame, dict]]:
    """
    Procesa todos los archivos Excel de un directorio.

    Args:
        input_dir: Directorio con archivos Excel individuales

    Returns:
        Lista de tuplas (dataframe, metadata) procesadas
    """
    logger.info("Buscando archivos Excel en: %s", input_dir)

    # Buscar archivos Excel
    excel_files = list(input_dir.glob("*.xlsx")) + list(input_dir.glob("*.xls"))

    if not excel_files:
        logger.warning("No se encontraron archivos Excel en el directorio")
        return []

    logger.info("Encontrados %d archivos Excel", len(excel_files))

    consultores_data = []
    processor = build_timesheet_processor()
    batch_processor = BatchProcessor(processor, sheet_parser=ExcelSheetParserAdapter())

    for file_path in excel_files:
        logger.info("Procesando: %s", file_path.name)

        try:
            # Leer archivo
            with open(file_path, 'rb') as f:
                file_bytes = f.read()

            # Parsear
            parsed_sheet = load_sheet_with_header(file_bytes)

            # Mapeo (ajustar según tus archivos)
            mapping = ColumnMapping(
                date="Fecha",
                hours="Horas",
                description="Actividad",
                project="Tipo Actividad" if "Tipo Actividad" in parsed_sheet.dataframe.columns else None,
            )

            # Procesar
            result = processor.process_parsed_sheet(
                parsed_sheet=parsed_sheet,
                mapping=mapping,
                source_name=file_path.name,
            )

            # Extraer datos procesados
            consultores_data.append((result.corrected_dataframe, parsed_sheet.metadata))

            logger.info("✓ Procesado: %s", parsed_sheet.metadata.get('employee', 'Desconocido'))

        except Exception as exc:
            logger.error("✗ Error procesando %s: %s", file_path.name, exc)
            continue

    return consultores_data


def main():
    """Función principal del script de prueba."""
    parser = argparse.ArgumentParser(
        description="Generador de Consolidado de Reportes TI"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Directorio con archivos Excel procesados (opcional)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="Informe_Consolidado_Test.xlsx",
        help="Nombre del archivo de salida",
    )
    parser.add_argument(
        "--cliente",
        type=str,
        default="NOVA - TI",
        help="Nombre del cliente",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Usar datos de ejemplo en lugar de archivos reales",
    )

    args = parser.parse_args()

    logger.info("=== Iniciando generación de consolidado ===")
    logger.info("Cliente: %s", args.cliente)
    logger.info("Archivo de salida: %s", args.output)

    # Obtener datos
    if args.sample:
        logger.info("Usando datos de ejemplo...")
        consultores_data = create_sample_data()
    elif args.input:
        input_dir = Path(args.input)
        if not input_dir.exists():
            logger.error("El directorio no existe: %s", input_dir)
            sys.exit(1)
        consultores_data = process_files_from_directory(input_dir)
    else:
        logger.error("Debes especificar --input o usar --sample")
        parser.print_help()
        sys.exit(1)

    if not consultores_data:
        logger.error("No se obtuvieron datos para consolidar")
        sys.exit(1)

    logger.info("Total de consultores a consolidar: %d", len(consultores_data))

    # Crear consolidador
    consolidator = TimeSheetConsolidator(
        cliente=args.cliente,
        collaborator_rates=get_collaborator_rates_manager(),
    )

    # Generar consolidado
    try:
        consolidated = consolidator.generate_consolidated_report(
            consultores_data=consultores_data,
            output_filename=args.output,
        )

        # Guardar archivo
        output_path = Path(args.output)
        output_path.write_bytes(consolidated.workbook_bytes)

        logger.info("=== ✓ Consolidado generado exitosamente ===")
        logger.info("Archivo: %s", output_path.absolute())
        logger.info("Consultores incluidos: %d", consolidated.consultores_incluidos)
        logger.info("Total a facturar: $%.2f", consolidated.total_facturar)
        logger.info("Total horas: %.1f h", consolidated.total_horas)
        logger.info("Periodo: %s", consolidated.periodo)
        logger.info("Días laborables: %d", consolidated.dias_laborables)

        print("\n" + "="*60)
        print("✓ CONSOLIDADO GENERADO EXITOSAMENTE")
        print("="*60)
        print(f"Archivo: {output_path.absolute()}")
        print(f"Consultores: {consolidated.consultores_incluidos}")
        print(f"Total a facturar: ${consolidated.total_facturar:,.2f}")
        print("="*60)

    except Exception as exc:
        logger.exception("Error generando consolidado: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
