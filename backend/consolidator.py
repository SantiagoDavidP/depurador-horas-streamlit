"""
Módulo para generar informes consolidados de múltiples consultores.

Este módulo toma los resultados procesados del BatchProcessor y genera
un archivo Excel profesional con:
- Hoja de resumen con todos los consultores
- Hojas individuales por consultor
- Cálculos de facturación y métricas
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from openpyxl import Workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.worksheet import Worksheet

from backend.collaborator_rates import get_collaborator_rates_manager

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None  # type: ignore

logger = logging.getLogger(__name__)

# ============================================================
# PALETA DE COLORES PROFESIONAL NOVA-TI
# ============================================================
COLOR_LIME = "8BC34A"              # Verde lima (titulos, acentos)
COLOR_DARK_GREEN = "689F38"        # Verde oscuro (totales, bordes)
COLOR_BLACK = "1A1A1A"             # Negro (fondos oscuros)
COLOR_SOFT_GREEN = "E8F5E9"        # Verde suave (filas alternadas)
COLOR_WHITE = "FFFFFF"             # Blanco
COLOR_LIGHT_GRAY = "F5F5F5"        # Gris claro (celdas de info)
COLOR_ORANGE = "F4A640"            # Naranja suave (encabezados resaltados)
COLOR_BORDER_LIGHT = "E0E0E0"      # Bordes sutiles grises

# ============================================================
# ESTILOS TIPOGRÁFICOS
# ============================================================
# Título principal del reporte
TITLE_FONT = Font(name="Calibri", size=22, bold=True, color=COLOR_LIME)

# Subtítulo (nombre del cliente)
SUBTITLE_FONT = Font(name="Calibri", size=12, bold=True, color=COLOR_WHITE)

# Etiquetas de información general
INFO_LABEL_FONT = Font(name="Calibri", size=11, bold=True, color=COLOR_BLACK)
INFO_VALUE_FONT = Font(name="Calibri", size=11, bold=False, color=COLOR_BLACK)

# Encabezados de tabla
TABLE_HEADER_FONT = Font(name="Calibri", size=11, bold=True, color=COLOR_LIME)
TABLE_HEADER_FILL = PatternFill(start_color=COLOR_BLACK, end_color=COLOR_BLACK, fill_type="solid")
TABLE_HEADER_ORANGE_FONT = Font(name="Calibri", size=11, bold=True, color=COLOR_BLACK)
TABLE_HEADER_ORANGE_FILL = PatternFill(start_color=COLOR_ORANGE, end_color=COLOR_ORANGE, fill_type="solid")

# Filas de datos
DATA_FONT = Font(name="Calibri", size=10, bold=False, color=COLOR_BLACK)
ALTERNATE_ROW_FILL = PatternFill(start_color=COLOR_SOFT_GREEN, end_color=COLOR_SOFT_GREEN, fill_type="solid")

# Fila de totales
TOTAL_ROW_FILL = PatternFill(start_color=COLOR_DARK_GREEN, end_color=COLOR_DARK_GREEN, fill_type="solid")
TOTAL_ROW_FONT = Font(name="Calibri", size=11, bold=True, color=COLOR_WHITE)

# ============================================================
# ESTILOS DE BORDES
# ============================================================
# Bordes sutiles para tabla
THIN_BORDER = Border(
    left=Side(style="thin", color=COLOR_BORDER_LIGHT),
    right=Side(style="thin", color=COLOR_BORDER_LIGHT),
    top=Side(style="thin", color=COLOR_BORDER_LIGHT),
    bottom=Side(style="thin", color=COLOR_BORDER_LIGHT),
)

# Borde superior grueso para fila de totales
THICK_TOP_BORDER = Border(
    left=Side(style="thin", color=COLOR_BORDER_LIGHT),
    right=Side(style="thin", color=COLOR_BORDER_LIGHT),
    top=Side(style="thick", color=COLOR_LIME),
    bottom=Side(style="thin", color=COLOR_BORDER_LIGHT),
)

# Bordes para sección de información
INFO_BORDER = Border(
    left=Side(style="thin", color=COLOR_BORDER_LIGHT),
    right=Side(style="thin", color=COLOR_BORDER_LIGHT),
    top=Side(style="thin", color=COLOR_BORDER_LIGHT),
    bottom=Side(style="thin", color=COLOR_BORDER_LIGHT),
)

# ============================================================
# ESTILOS DE ALINEACIÓN
# ============================================================
CENTER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=False)
LEFT_ALIGNMENT = Alignment(horizontal="left", vertical="center", wrap_text=False)
RIGHT_ALIGNMENT = Alignment(horizontal="right", vertical="center", wrap_text=False)

# Fondo para sección de información
INFO_FILL = PatternFill(start_color=COLOR_LIGHT_GRAY, end_color=COLOR_LIGHT_GRAY, fill_type="solid")


@dataclass
class ConsultorMetrics:
    """Métricas calculadas para un consultor."""

    nombre: str
    cargo: str
    dias_laborados: int
    total_horas_normales: float
    total_horas_extras: float
    valor_tarifa: float
    valor_dia: float
    total_facturar: float
    valor_hora_extra: float
    total_horas_extras_facturar: float
    dataframe: pd.DataFrame
    metadata: Dict[str, object]


@dataclass
class ConsolidatedReport:
    """Resultado del proceso de consolidación."""

    workbook_bytes: bytes
    output_filename: str
    consultores_incluidos: int
    total_facturar: float
    total_horas: float
    periodo: str
    dias_laborables: int


class TimeSheetConsolidator:
    """
    Consolidador de reportes de actividades de múltiples consultores.

    Toma los resultados procesados del BatchProcessor y genera un archivo
    Excel profesional con resumen ejecutivo y hojas individuales.
    """

    # Tarifas por cargo (pueden parametrizarse)
    TARIFAS = {
        "Senior": {"mensual": 2770, "hora_extra": 25},
        "Semisenior": {"mensual": 2320, "hora_extra": 22},
        "Junior": {"mensual": 1670, "hora_extra": 20},
    }


    def __init__(self, cliente: str = "NOVA - TI", logo_path: Optional[Path] = None):
        """
        Inicializa el consolidador.

        Args:
            cliente: Nombre del cliente para el encabezado
            logo_path: Ruta al logo (PNG). Si None, busca en frontend/logo.png
        """
        self.cliente = cliente
        self.consultores_metrics: List[ConsultorMetrics] = []
        self.logo_path = self._resolve_logo_path(logo_path)
        self.client_logo_path = self._resolve_client_logo_path()

    def _resolve_logo_path(self, logo_path: Optional[Path]) -> Optional[Path]:
        """
        Resuelve la ruta del logo.

        Args:
            logo_path: Ruta proporcionada o None

        Returns:
            Path al logo si existe, None en caso contrario
        """
        if logo_path and logo_path.exists():
            return logo_path

        # Buscar en ubicaciones estándar
        module_dir = Path(__file__).resolve().parent
        project_root = module_dir.parent

        # Regresar al comportamiento base: logo principal Business IT (logobit)
        preferred_names = ["logobit.png", "Logo.png", "logo.png"]
        for name in preferred_names:
            for candidate in (module_dir / name, project_root / "frontend" / name, project_root / name):
                if candidate.exists():
                    logger.info("Logo principal encontrado en: %s", candidate)
                    return candidate

        # Ubicaciones posibles
        possible_paths = [
            module_dir / "logobit.png",
            project_root / "frontend" / "logo.png",
            project_root / "assets" / "logo.png",
            project_root / "logo.png",
        ]

        for path in possible_paths:
            if path.exists():
                logger.info("Logo encontrado en: %s", path)
                return path

        logger.warning("No se encontró logo.png en ubicaciones estándar")
        return None

    def _resolve_client_logo_path(self) -> Optional[Path]:
        """Resuelve logo secundario por cliente (NOVA/BANINTER)."""
        module_dir = Path(__file__).resolve().parent
        project_root = module_dir.parent
        cliente_lower = (self.cliente or "").lower()

        if any(k in cliente_lower for k in ["baninter", "banco internacional"]):
            names = ["BANINTER.png", "baninter.png"]
        else:
            names = ["NOVA.png", "nova.png"]

        for name in names:
            for candidate in (project_root / name, module_dir / name, project_root / "frontend" / name):
                if candidate.exists():
                    logger.info("Logo secundario encontrado en: %s", candidate)
                    return candidate
        return None

    def _add_logo(
        self,
        ws: Worksheet,
        anchor: str = "A1",
        max_width: int = 140,
        max_height: Optional[int] = None,
        logo_path: Optional[Path] = None,
        width_cm: Optional[float] = None,
        height_cm: Optional[float] = None,
    ) -> None:
        """Agrega logo al worksheet si existe uno configurado."""
        path = logo_path or self.logo_path
        if not path or not path.exists():
            return
        try:
            img = Image(str(path))
            if not img.width or not img.height:
                return

            if width_cm and height_cm and width_cm > 0 and height_cm > 0:
                # openpyxl usa pixeles en Image.width/height
                img.width = int(round(width_cm * 37.795))
                img.height = int(round(height_cm * 37.795))
            else:
                width_scale = max_width / float(img.width)
                height_scale = (
                    (max_height / float(img.height))
                    if max_height and max_height > 0
                    else width_scale
                )
                scale = min(width_scale, height_scale)
                img.width = int(img.width * scale)
                img.height = int(img.height * scale)
            img.anchor = anchor
            ws.add_image(img)
        except Exception as exc:
            logger.warning("No se pudo agregar logo (%s): %s", path, exc)

    def extract_consultant_data(
        self,
        dataframe: pd.DataFrame,
        metadata: Dict[str, object],
        date_column: str = "Fecha",
        hours_column: str = "Horas",
        hour_type_column: Optional[str] = "Tipo Hora",
    ) -> ConsultorMetrics:
        """
        Extrae y calcula métricas de un consultor desde su DataFrame procesado.

        Args:
            dataframe: DataFrame con actividades del consultor (ya validado/corregido)
            metadata: Metadata extraída del archivo
            date_column: Nombre de la columna de fecha
            hours_column: Nombre de la columna de horas
            hour_type_column: Nombre de la columna de tipo de hora (HN, HE, etc.)

        Returns:
            ConsultorMetrics con todos los cálculos
        """
        dataframe = dataframe.copy()
        self._normalize_ticket_columns(dataframe)
        self._fill_empty_special_columns(dataframe)

        metadata = dict(metadata or {})
        # Extraer nombre del consultor
        nombre = str(metadata.get("employee", "Consultor Desconocido"))

        # Inferir cargo (puede mejorarse con lógica adicional o desde metadata)
        cargo = self._inferir_cargo(nombre, metadata)
        
        # Obtener manager de tarifas
        rates_manager = get_collaborator_rates_manager()

        # Parsear fechas y horas
        parsed_dates = pd.to_datetime(
            dataframe[date_column], errors="coerce", dayfirst=True
        )
        numeric_hours = pd.to_numeric(dataframe[hours_column], errors="coerce")

        # Filtrar solo filas válidas
        valid_mask = parsed_dates.notna() & numeric_hours.notna() & (numeric_hours > 0)
        valid_data = dataframe[valid_mask].copy()
        valid_dates = parsed_dates[valid_mask]
        valid_hours = numeric_hours[valid_mask]

        # Calcular días laborados (fechas únicas)
        dias_laborados = len(valid_dates.dt.date.unique())

        # Calcular horas normales y extras
        total_horas_normales = 0.0
        total_horas_extras = 0.0

        if hour_type_column and hour_type_column in dataframe.columns:
            hour_types = valid_data[hour_type_column].fillna("HN").astype(str)
            for hour_type, hours in zip(hour_types, valid_hours):
                if "HN" in hour_type.upper():
                    total_horas_normales += hours
                else:
                    total_horas_extras += hours
        else:
            # Si no hay columna de tipo de hora, asumir todas como normales
            total_horas_normales = float(valid_hours.sum())

        # Obtener tarifas personalizadas del colaborador
        # Si el colaborador está en collaborator_rates.json, usa sus datos completos
        # Si no está, usa defaults por seniority (ya inferido por _inferir_cargo)
        rate_info = rates_manager.get_rate_for_collaborator(nombre, seniority_fallback=cargo)
        if rate_info.get("cargo"):
            metadata["area"] = "CD"
        else:
            metadata["area"] = "TI"
        
        # Usar valores específicos del colaborador si están disponibles
        valor_tarifa = rate_info["salario_mensual"]
        valor_hora_extra = rate_info["valor_hora_extra"]
        # Días laborables: prioridad → rates.json → metadata → cálculo automático
        dias_laborables = rate_info.get("dias_laborables_mes")

        if not dias_laborables:
            dias_laborables = self._calcular_dias_laborables(
                metadata.get("year"),
                metadata.get("month_name"),
            )
            logger.info(
                "Dias laborables calculados automaticamente para %s: %d",
                nombre,
                dias_laborables,
            )

        # Valor por día SIEMPRE se recalcula de forma segura
        valor_dia = valor_tarifa / dias_laborables

        # Log si se encontró configuración personalizada
        if rate_info["found_by_name"]:
            logger.info(
                f"Usando tarifas personalizadas para {rate_info['nombre_completo']}: "
                f"${valor_dia:.2f}/día, ${valor_hora_extra:.2f}/hora extra"
            )
        else:
            logger.info(
                f"Usando tarifas por seniority ({cargo}) para {nombre}: "
                f"${valor_dia:.2f}/día"
            )
        total_facturar = valor_dia * dias_laborados
        total_horas_extras_facturar = total_horas_extras * valor_hora_extra

        return ConsultorMetrics(
            nombre=nombre,
            cargo=cargo,
            dias_laborados=dias_laborados,
            total_horas_normales=total_horas_normales,
            total_horas_extras=total_horas_extras,
            valor_tarifa=valor_tarifa,
            valor_dia=valor_dia,
            total_facturar=total_facturar,
            valor_hora_extra=valor_hora_extra,
            total_horas_extras_facturar=total_horas_extras_facturar,
            dataframe=dataframe,
            metadata=metadata,
        )

    @staticmethod
    def _normalize_ticket_columns(df: pd.DataFrame) -> None:
        ticket_columns = [col for col in df.columns if "ticket" in str(col).lower()]
        if not ticket_columns:
            return

        def _normalize(value: object) -> object:
            if pd.isna(value):
                return ""
            if isinstance(value, (int, float)):
                if isinstance(value, float) and value.is_integer():
                    return str(int(value))
                return str(value)
            text = str(value).strip()
            if not text:
                return ""
            normalized = re.sub(r"\s+", "", text)
            return normalized

        for col in ticket_columns:
            df[col] = df[col].apply(_normalize)

    @staticmethod
    def _fill_empty_special_columns(df: pd.DataFrame) -> None:
        target = r"\NOVA\Tecnología - Documentos\IT\Desarrollo\Documentación\2025"
        normalized_target = target.strip().casefold()
        for col in df.columns:
            if str(col).strip().casefold() != normalized_target:
                continue
            series = df[col]
            mask = series.isna() | series.astype(str).str.strip().eq("")
            if mask.any():
                df.loc[mask, col] = "SN"

    def _inferir_cargo(self, nombre: str, metadata: Dict[str, object]) -> str:
        """
        Infiere el cargo del consultor de forma automática.
        
        Prioridad:
        1. Buscar en collaborator_rates.json (si existe el colaborador)
        2. Metadata del archivo (campo "cargo" o "role")
        3. Metadata de rol detectado desde actividades
        4. Default "Junior" (conservador)

        Args:
            nombre: Nombre del consultor
            metadata: Metadata del archivo

        Returns:
            Cargo: Senior, Semisenior o Junior
        """
        # 1. PRIMERO: Intentar obtener desde collaborator_rates.json
        rates_manager = get_collaborator_rates_manager()
        collab = rates_manager.find_collaborator(nombre)
        
        if collab:
            # Encontrado en JSON - usar su seniority
            if collab.cargo:
                logger.info(f"Cargo de {nombre} obtenido de collaborator_rates: {collab.cargo}")
                return collab.cargo
            logger.info(f"Seniority de {nombre} obtenido de collaborator_rates: {collab.seniority}")
            return collab.seniority
        
        # 2. Buscar en metadata del archivo
        if "cargo" in metadata:
            cargo = str(metadata["cargo"]).strip()
            logger.info(f"Seniority de {nombre} obtenido de metadata 'cargo': {cargo}")
            return cargo
            
        if "role" in metadata:
            role = str(metadata["role"]).strip()
            logger.info(f"Seniority de {nombre} obtenido de metadata 'role': {role}")
            return role
        
        if "seniority" in metadata:
            seniority = str(metadata["seniority"]).strip()
            logger.info(f"Seniority de {nombre} obtenido de metadata 'seniority': {seniority}")
            return seniority
        
        # 3. Intentar inferir desde rol detectado en validaciones (si existe)
        if "detected_role" in metadata:
            detected_role = str(metadata["detected_role"]).strip().lower()
            # Mapeo básico de roles a seniority
            role_to_seniority = {
                "senior developer": "Senior",
                "lead developer": "Senior",
                "architect": "Senior",
                "developer": "Semisenior",
                "qa engineer": "Semisenior",
                "devops": "Semisenior",
                "junior developer": "Junior",
                "qa junior": "Junior",
                "intern": "Junior",
            }
            for role_key, seniority_value in role_to_seniority.items():
                if role_key in detected_role:
                    logger.info(f"Seniority de {nombre} inferido de rol detectado: {seniority_value}")
                    return seniority_value
        
        # 4. DEFAULT: Usar Junior como opción conservadora
        logger.warning(
            f"No se pudo determinar seniority para '{nombre}'. "
            f"Usando default 'Junior'. Considera agregarlo a collaborator_rates.json"
        )
        return "Junior"

    def _calcular_dias_laborables(
        self, year: Optional[int], month_name: Optional[str]
    ) -> int:
        """
        Calcula días laborables del mes (L-V, excluyendo feriados).

        Args:
            year: Año
            month_name: Nombre del mes en inglés

        Returns:
            Número de días laborables
        """
        if not year or not month_name:
            return 22  # Valor por defecto

        try:
            # Convertir nombre del mes a número
            month = datetime.strptime(month_name, "%B").month
        except ValueError:
            return 22

        # Importar función de validators
        from backend.validators import get_working_days_in_period

        working_days = get_working_days_in_period(year, month)
        return len(working_days)

    def generate_consolidated_report(
        self,
        consultores_data: List[Tuple[pd.DataFrame, Dict[str, object]]],
        output_filename: Optional[str] = None,
    ) -> ConsolidatedReport:
        """
        Genera el reporte consolidado a partir de los datos de múltiples consultores.

        Args:
            consultores_data: Lista de tuplas (dataframe, metadata) de cada consultor
            output_filename: Nombre del archivo de salida (None para auto-generar)

        Returns:
            ConsolidatedReport con el workbook y metadatos
        """
        logger.info("Iniciando generación de reporte consolidado...")

        # Extraer métricas de cada consultor
        self.consultores_metrics = []
        for df, metadata in consultores_data:
            try:
                metrics = self.extract_consultant_data(df, metadata)
                self.consultores_metrics.append(metrics)
                logger.info(
                    "Procesado: %s - %d días laborados, %.1f horas",
                    metrics.nombre,
                    metrics.dias_laborados,
                    metrics.total_horas_normales + metrics.total_horas_extras,
                )
            except Exception as exc:
                logger.error(
                    "Error procesando consultor %s: %s",
                    metadata.get("employee", "desconocido"),
                    exc,
                )
                continue

        if not self.consultores_metrics:
            raise ValueError("No se pudieron procesar consultores")

        self._resolve_cliente_from_metrics()

        # Crear workbook
        wb = Workbook()
        wb.remove(wb.active)  # Eliminar hoja por defecto

        # Determinar periodo y días laborables del primer consultor
        first_metadata = self.consultores_metrics[0].metadata
        periodo = f"{first_metadata.get('month_name', 'N/A')} {first_metadata.get('year', 'N/A')}"
        dias_laborables = self._calcular_dias_laborables(
            first_metadata.get("year"), first_metadata.get("month_name")
        )

        # 1. Crear hoja de resumen
        ws_resumen = wb.create_sheet("Resumen", 0)
        self._create_summary_sheet(ws_resumen, periodo, dias_laborables)

        # 2. Crear hojas individuales por consultor
        for idx, metrics in enumerate(self.consultores_metrics, start=1):
            sheet_name = self._sanitize_sheet_name(f"{idx}. {metrics.nombre}")
            ws_individual = wb.create_sheet(sheet_name)
            self._create_individual_sheet(ws_individual, metrics)

        # Guardar en bytes
        from io import BytesIO

        buffer = BytesIO()
        wb.save(buffer)
        workbook_bytes = buffer.getvalue()

        # Generar nombre de archivo si no se proporciona
        if not output_filename:
            mes = first_metadata.get("month_name", "Unknown")
            year = first_metadata.get("year", "2025")
            output_filename = f"Informe_TI_Nova_BIT_{mes}_{year}_Consolidado.xlsx"

        # Calcular totales
        total_facturar = sum(
            m.total_facturar + m.total_horas_extras_facturar
            for m in self.consultores_metrics
        )
        total_horas = sum(
            m.total_horas_normales + m.total_horas_extras
            for m in self.consultores_metrics
        )

        logger.info("Reporte consolidado generado exitosamente")
        logger.info("Total consultores: %d", len(self.consultores_metrics))
        logger.info("Total a facturar: $%.2f", total_facturar)

        return ConsolidatedReport(
            workbook_bytes=workbook_bytes,
            output_filename=output_filename,
            consultores_incluidos=len(self.consultores_metrics),
            total_facturar=total_facturar,
            total_horas=total_horas,
            periodo=periodo,
            dias_laborables=dias_laborables,
        )

    def generate_single_consultant_report(
        self,
        dataframe: pd.DataFrame,
        metadata: Dict[str, object],
        output_filename: Optional[str] = None,
    ) -> bytes:
        """
        Genera un Excel individual con el mismo formato visual del consolidado.
        """
        wb = Workbook()
        ws = wb.active
        ws.title = self._sanitize_sheet_name(str(metadata.get("employee", "Consultor")))

        metrics = self.extract_consultant_data(dataframe, metadata)
        self._create_individual_sheet(ws, metrics)

        from io import BytesIO
        buffer = BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    def _create_summary_sheet(
        self, ws: Worksheet, periodo: str, dias_laborables: int
    ) -> None:
        """Crea la hoja de resumen con diseno corporativo NOVA-TI."""
        # Limpieza de merges previos para evitar conflictos con el nuevo layout
        for merged_range in list(ws.merged_cells.ranges):
            ws.unmerge_cells(str(merged_range))

        # Ordenar colaboradores por cargo: Senior -> Semisenior -> Junior
        seniority_order = {"Senior": 1, "Semisenior": 2, "Junior": 3}
        sorted_metrics = sorted(
            self.consultores_metrics,
            key=lambda m: (seniority_order.get(m.cargo, 4), m.nombre)
        )

        def px_to_points(px: float) -> float:
            """Convierte pixeles a puntos (Excel usa puntos en alturas)."""
            return round(px * 0.75, 2)

        total_columns = 14
        end_col = get_column_letter(total_columns)

        header_fill = PatternFill(start_color=COLOR_BLACK, end_color=COLOR_BLACK, fill_type='solid')
        accent_fill = PatternFill(start_color=COLOR_LIME, end_color=COLOR_LIME, fill_type='solid')

        # Logo en esquina superior izquierda
        # Logo principal Business IT (restaurado al tamaño visual anterior)
        self._add_logo(ws, anchor="A1", max_width=150, max_height=52)
        if self.client_logo_path:
            # Logo cliente en resumen: fila negra superior, esquina derecha
            client_stem = self.client_logo_path.stem.lower()
            if "baninter" in client_stem:
                self._add_logo(ws, anchor="L1", logo_path=self.client_logo_path, max_width=110, max_height=32)
            elif "nova" in client_stem:
                # NOVA en la misma fila de header negro que BIT
                self._add_logo(ws, anchor="L1", max_width=105, max_height=30, logo_path=self.client_logo_path)
            else:
                self._add_logo(ws, anchor="L1", max_width=105, max_height=30, logo_path=self.client_logo_path)

        # ============================================================
        # HEADER (filas 1-3)
        # ============================================================
        ws.merge_cells(f"A1:{end_col}1")
        title_cell = ws['A1']
        title_cell.value = 'INFORME CONSOLIDADO DE ACTIVIDADES'
        title_cell.font = TITLE_FONT
        title_cell.alignment = CENTER_ALIGNMENT
        title_cell.fill = header_fill

        ws.merge_cells(f"A2:{end_col}2")
        subtitle_cell = ws['A2']
        subtitle_cell.value = self.cliente
        subtitle_cell.font = SUBTITLE_FONT
        subtitle_cell.alignment = CENTER_ALIGNMENT
        subtitle_cell.fill = header_fill

        ws.merge_cells(f"A3:{end_col}3")
        line_cell = ws['A3']
        line_cell.fill = accent_fill

        for row in [1, 2]:
            ws.row_dimensions[row].height = px_to_points(35)
            for col in range(1, total_columns + 1):
                ws.cell(row=row, column=col).fill = header_fill
        ws.row_dimensions[3].height = px_to_points(5)

        # ============================================================
        # INFO DEL CONTRATO (filas 5-9)
        # ============================================================
        info_start = 5
        contract_info = [
            ('Cliente:', self.cliente),
            ('Fecha inicio:', f"01/{periodo.split()[0][:3]}/{periodo.split()[1]}"),
            ('Fecha fin:', f"30/{periodo.split()[0][:3]}/{periodo.split()[1]}"),
            ('Mes:', periodo),
            ('Dias Laborables:', dias_laborables),
        ]

        label_col = 'B'
        value_start_col = 'C'
        value_end_col = 'G'
        value_border = Border(bottom=Side(style='medium', color=COLOR_LIME))

        for idx, (label, value) in enumerate(contract_info):
            row = info_start + idx

            label_cell = ws[f"{label_col}{row}"]
            label_cell.value = label
            label_cell.font = INFO_LABEL_FONT
            label_cell.alignment = RIGHT_ALIGNMENT

            value_cell = ws[f"{value_start_col}{row}"]
            value_cell.value = value
            value_cell.font = INFO_VALUE_FONT
            value_cell.alignment = LEFT_ALIGNMENT
            value_cell.fill = INFO_FILL
            value_cell.border = value_border
            ws.merge_cells(f"{value_start_col}{row}:{value_end_col}{row}")

            ws.row_dimensions[row].height = px_to_points(24)

        # ============================================================
        # TABLA DE DATOS
        # ============================================================
        header_row = info_start + len(contract_info) + 2
        headers = [
            'No.',
            'NOMBRE',
            'CARGO',
            'DIAS LABORADOS',
            'VALOR TARIFA',
            'VALOR DÍA',
            'TOTAL',
            'DIAS LABORADOS',
            'HN',
            'HORAS EXTRAS',
            'VALOR A FACTURAR',
            'Valor Horas Extras',
            'Total Horas Extras',
            'TOTAL GENERAL',
        ]

        header_border = Border(
            left=Side(style='thin', color=COLOR_DARK_GREEN),
            right=Side(style='thin', color=COLOR_DARK_GREEN),
            top=Side(style='thin', color=COLOR_DARK_GREEN),
            bottom=Side(style='thin', color=COLOR_DARK_GREEN),
        )

        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=header_row, column=col_idx, value=header)
            if col_idx in {8, 9, 10, 11, 12, 13, 14}:
                cell.font = TABLE_HEADER_ORANGE_FONT
                cell.fill = TABLE_HEADER_ORANGE_FILL
            else:
                cell.font = TABLE_HEADER_FONT
                cell.fill = TABLE_HEADER_FILL
            cell.alignment = CENTER_ALIGNMENT
            cell.border = header_border

        ws.row_dimensions[header_row].height = px_to_points(35)

        data_row_height = px_to_points(28)

        for idx, metrics in enumerate(sorted_metrics, start=1):
            row = header_row + idx
            values = [
                idx,
                metrics.nombre,
                metrics.cargo,
                None,  # DIAS LABORADOS (formula desde header)
                round(metrics.valor_tarifa, 2),
                None,  # VALOR DÍA (formula)
                None,  # TOTAL (formula)
                metrics.dias_laborados,
                None,  # HN (formula)
                round(metrics.total_horas_extras, 2),
                None,  # VALOR A FACTURAR (formula)
                round(metrics.valor_hora_extra, 2),
                None,  # Total Horas Extras (formula)
                None,  # TOTAL GENERAL (formula)
            ]

            for col_idx, value in enumerate(values, start=1):
                cell = ws.cell(row=row, column=col_idx, value=value)
                cell.font = DATA_FONT
                cell.border = THIN_BORDER

                if col_idx == 1:
                    cell.alignment = CENTER_ALIGNMENT
                elif col_idx in [2, 3]:
                    cell.alignment = LEFT_ALIGNMENT
                else:
                    cell.alignment = RIGHT_ALIGNMENT

                if col_idx in [5, 6, 7, 11, 12, 13, 14]:
                    cell.number_format = '$#,##0.00'
                elif col_idx in [4, 8]:
                    cell.number_format = '0'
                elif col_idx in [9, 10]:
                    cell.number_format = '0.0'

                # Formularios por fila
                if col_idx == 4:  # DIAS LABORADOS = valor del header
                    cell.value = f"=$C$9"
                if col_idx == 6:  # VALOR DÍA = VALOR TARIFA / DIAS LABORADOS (col 4)
                    cell.value = f"=E{row}/D{row}"
                elif col_idx == 7:  # TOTAL = DIAS LABORADOS (col 4) * VALOR DÍA
                    cell.value = f"=D{row}*F{row}"
                elif col_idx == 9:  # HN = DIAS LABORADOS (col 8) * 8
                    cell.value = f"=H{row}*8"
                elif col_idx == 11:  # VALOR A FACTURAR = DIAS LABORADOS (col 8) * VALOR DÍA
                    cell.value = f"=H{row}*F{row}"
                elif col_idx == 13:  # Total Horas Extras = Valor Horas Extras * Horas Extras
                    cell.value = f"=L{row}*J{row}"
                elif col_idx == 14:  # TOTAL GENERAL solo se calcula en la fila TOTAL
                    cell.value = None

                if idx % 2 == 0:
                    cell.fill = ALTERNATE_ROW_FILL

            ws.row_dimensions[row].height = data_row_height

        # ============================================================
        # FILA TOTALES
        # ============================================================
        total_row = header_row + len(sorted_metrics) + 1
        ws.merge_cells(f"A{total_row}:C{total_row}")

        for col_idx in range(1, 4):
            total_cell = ws.cell(row=total_row, column=col_idx)
            if col_idx == 1:
                total_cell.value = 'TOTAL'
            total_cell.font = TOTAL_ROW_FONT
            total_cell.fill = TOTAL_ROW_FILL
            total_cell.alignment = CENTER_ALIGNMENT
            total_cell.border = THICK_TOP_BORDER

        totals = {
            4: f"=C9",
            5: round(sum(m.valor_tarifa for m in self.consultores_metrics), 2),
            6: '',
            7: f"=SUM(G{header_row + 1}:G{total_row - 1})",
            8: sum(m.dias_laborados for m in self.consultores_metrics),
            9: f"=SUM(I{header_row + 1}:I{total_row - 1})",
            10: f"=SUM(J{header_row + 1}:J{total_row - 1})",
            11: f"=SUM(K{header_row + 1}:K{total_row - 1})",
            12: '',
            13: f"=SUM(M{header_row + 1}:M{total_row - 1})",
            14: f"=K{total_row}+M{total_row}",
        }

        for col_idx, total_value in totals.items():
            cell = ws.cell(row=total_row, column=col_idx, value=total_value)
            cell.font = TOTAL_ROW_FONT
            cell.fill = TOTAL_ROW_FILL
            cell.border = THICK_TOP_BORDER
            cell.alignment = RIGHT_ALIGNMENT

            if col_idx in [5, 7, 11, 12, 13, 14] and total_value not in ('', None):
                cell.number_format = '$#,##0.00'
            elif col_idx in [4, 8] and total_value not in ('', None):
                cell.number_format = '0'
            elif col_idx in [9, 10] and total_value not in ('', None):
                cell.number_format = '0.0'

        ws.row_dimensions[total_row].height = px_to_points(32)

        # ============================================================
        # AJUSTES FINALES
        # ============================================================
        column_widths = {
            'A': 6,
            'B': 30,
            'C': 16,
            'D': 12,
            'E': 14,
            'F': 14,
            'G': 14,
            'H': 12,
            'I': 10,
            'J': 12,
            'K': 16,
            'L': 12,
            'M': 14,
            'N': 16,
        }

        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width

        ws.freeze_panes = f"A{header_row + 1}"

        footer_row = total_row + 2
        ws.merge_cells(f"A{footer_row}:{end_col}{footer_row}")
        ws[f"A{footer_row}"] = f"Informe generado automaticamente | {self.cliente} (c) {datetime.now().year}"
        ws[f"A{footer_row}"].font = Font(name='Calibri', size=9, italic=True, color='7F8C8D')
        ws[f"A{footer_row}"].alignment = CENTER_ALIGNMENT

        logger.info('Hoja de resumen creada con diseno corporativo')

    def _create_individual_sheet(
        self, ws: Worksheet, metrics: ConsultorMetrics
    ) -> None:
        """Crea una hoja individual con los datos del consultor."""
        cliente_actual = (self.cliente or "").lower()
        if any(k in cliente_actual for k in ["baninter", "banco internacional"]):
            self._create_individual_sheet_business_it(ws, metrics)
            return

        # Formato actual NOVA (se mantiene sin cambios)
        self._create_individual_sheet_nova(ws, metrics)

    def _create_individual_sheet_business_it(
        self, ws: Worksheet, metrics: ConsultorMetrics
    ) -> None:
        """Hoja individual BANINTER con layout simple tipo plantilla y colores corporativos."""
        dataframe = metrics.dataframe.copy()
        metadata = metrics.metadata or {}

        def _format_date_only(value: object) -> str:
            if not value:
                return ""
            if isinstance(value, (date, datetime)):
                return f"{value.day}/{value.month}/{value.year}"
            text = str(value).strip()
            # Evitar mostrar hora cuando llega "2026-01-01 00:00:00"
            if " " in text:
                text = text.split(" ")[0]
            try:
                parsed = datetime.fromisoformat(text)
                return f"{parsed.day}/{parsed.month}/{parsed.year}"
            except Exception:
                return text

        def _raw_from_metadata(labels: List[str]) -> str:
            raw_rows = (metadata.get("raw_rows") or {})
            for _, row_values in raw_rows.items():
                if not row_values:
                    continue
                first = str(row_values[0]).lower()
                if any(label in first for label in labels):
                    raw_text = str(row_values[-1]).strip()
                    return raw_text.split(" ")[0] if raw_text else ""
            return ""

        report_date_raw = _raw_from_metadata(["fecha del informe", "fecha informe"])
        period_raw = _raw_from_metadata(["periodo informe", "periodo"])

        report_date = report_date_raw or _format_date_only(metadata.get("report_date"))
        period_start = _format_date_only(metadata.get("period_start"))
        period_end = _format_date_only(metadata.get("period_end"))
        if not period_raw and period_start and period_end:
            period_raw = f"{period_start} - {period_end}"

        client_name = (
            str(metadata.get("client_name") or "").strip()
            or str(metadata.get("company") or "").strip()
            or "Banco Internacional"
        )
        consultant_name = str(metadata.get("employee") or metrics.nombre or "").strip()

        total_cols = max(5, len(dataframe.columns))
        end_col_letter = get_column_letter(total_cols)

        # Encabezado BANINTER + logo
        # Logo + titulo en la misma fila de header
        self._add_logo(ws, anchor="A1", max_width=235, max_height=78)
        if self.client_logo_path:
            client_anchor_col = get_column_letter(max(6, total_cols - 1))
            self._add_logo(
                ws,
                anchor=f"{client_anchor_col}2",
                logo_path=self.client_logo_path,
                max_width=100 if "baninter" in self.client_logo_path.stem.lower() else 95,
                max_height=30 if "baninter" in self.client_logo_path.stem.lower() else 28,
            )
        title_start_col = 2 if total_cols >= 2 else 1
        title_start_letter = get_column_letter(title_start_col)
        ws.merge_cells(f"{title_start_letter}1:{end_col_letter}1")
        title_cell = ws.cell(row=1, column=title_start_col, value="INFORME ACTIVIDADES OUTSOURCING BUSINESS IT")
        title_cell.font = TITLE_FONT
        title_cell.alignment = CENTER_ALIGNMENT
        title_cell.fill = TABLE_HEADER_FILL

        # Banda de color completa en la fila de título
        for c_idx in range(1, total_cols + 1):
            ws.cell(row=1, column=c_idx).fill = TABLE_HEADER_FILL

        labels_and_values = [
            ("Cliente:", client_name),
            ("Fecha del Informe:", report_date),
            ("Tema del Informe:", "Informe de Actividades"),
            ("Periodo Informe:", period_raw),
            ("Consultor:", consultant_name),
        ]
        info_row = 3
        for label, value in labels_and_values:
            ws.cell(row=info_row, column=1, value=label).font = INFO_LABEL_FONT
            ws.cell(row=info_row, column=2, value=value).font = INFO_VALUE_FONT
            ws.cell(row=info_row, column=2).alignment = LEFT_ALIGNMENT
            info_row += 1

        # Fila de encabezados (fila 1)
        date_col_indices = set()
        hour_col_indices = set()
        table_header_row = 9

        for c_idx, col_name in enumerate(dataframe.columns, start=1):
            cell = ws.cell(row=table_header_row, column=c_idx, value=str(col_name))
            cell.font = TABLE_HEADER_FONT
            cell.fill = TABLE_HEADER_FILL
            cell.border = THIN_BORDER
            cell.alignment = CENTER_ALIGNMENT

            col_text = str(col_name).lower()
            if "fecha" in col_text:
                date_col_indices.add(c_idx)
            if "hora" in col_text:
                hour_col_indices.add(c_idx)

        # Filas de datos
        for r_idx, row in enumerate(
            dataframe_to_rows(dataframe, index=False, header=False), start=table_header_row + 1
        ):
            for c_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=value)
                cell.font = DATA_FONT
                cell.border = THIN_BORDER
                cell.alignment = LEFT_ALIGNMENT

                if r_idx % 2 == 0:
                    cell.fill = ALTERNATE_ROW_FILL

                if c_idx in date_col_indices and value not in (None, ""):
                    try:
                        parsed = None
                        if isinstance(value, (date, datetime)):
                            parsed = value
                        else:
                            text = str(value).strip()
                            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
                                try:
                                    parsed = datetime.strptime(text, fmt)
                                    break
                                except ValueError:
                                    continue
                        if parsed:
                            cell.value = parsed
                            cell.number_format = "D/M/YYYY"
                            cell.alignment = CENTER_ALIGNMENT
                    except Exception:
                        pass

                if c_idx in hour_col_indices and value not in (None, ""):
                    cell.number_format = "0.0"
                    cell.alignment = RIGHT_ALIGNMENT

        # Ajustes visuales
        ws.freeze_panes = "A10"
        ws.row_dimensions[1].height = 56

        for col_idx in range(1, ws.max_column + 1):
            col_letter = get_column_letter(col_idx)
            max_length = 0
            for row_idx in range(1, ws.max_row + 1):
                value = ws.cell(row=row_idx, column=col_idx).value
                text = "" if value is None else str(value)
                if len(text) > max_length:
                    max_length = len(text)
            # Limites suaves para que se vea como plantilla BANINTER
            ws.column_dimensions[col_letter].width = min(max(max_length + 2, 12), 85)

    def _create_individual_sheet_nova(
        self, ws: Worksheet, metrics: ConsultorMetrics
    ) -> None:
        """Hoja individual NOVA (layout con metadata + tabla)."""
        # Encabezado con metadata (formato original)
        metadata = metrics.metadata or {}
        report_date = metadata.get("report_date")
        period_start = metadata.get("period_start")
        period_end = metadata.get("period_end")
        company = metadata.get("company", "")

        def _format_date(value: object) -> str:
            if not value:
                return ""
            if isinstance(value, (date, datetime)):
                return value.strftime("%d/%m/%Y")
            text = str(value).strip()
            try:
                parsed = datetime.fromisoformat(text)
                return parsed.strftime("%d/%m/%Y")
            except Exception:
                return text

        def _raw_from_metadata(labels: List[str]) -> str:
            raw_rows = (metadata.get("raw_rows") or {})
            for _, row_values in raw_rows.items():
                if not row_values:
                    continue
                first = str(row_values[0]).lower()
                if any(label in first for label in labels):
                    raw_text = str(row_values[-1]).strip()
                    # Si viene con hora, conservar solo la fecha
                    return raw_text.split(" ")[0]
            return ""

        report_date_raw = _raw_from_metadata(["fecha del informe", "fecha informe"])
        periodo_raw = _raw_from_metadata(["periodo informe", "periodo"])

        # NOVA: mismo criterio que BANINTER (logo + titulo en una sola fila)
        total_cols_nova = max(5, len(metrics.dataframe.columns))
        end_col_letter_nova = get_column_letter(total_cols_nova)
        self._add_logo(ws, anchor="A1", max_width=200, max_height=66)
        if self.client_logo_path:
            client_anchor_col = get_column_letter(max(6, total_cols_nova - 1))
            self._add_logo(
                ws,
                anchor=f"{client_anchor_col}2",
                logo_path=self.client_logo_path,
                max_width=100 if "baninter" in self.client_logo_path.stem.lower() else 95,
                max_height=30 if "baninter" in self.client_logo_path.stem.lower() else 28,
            )
        title_start_col = 2 if total_cols_nova >= 2 else 1
        title_start_letter = get_column_letter(title_start_col)
        ws.merge_cells(f"{title_start_letter}1:{end_col_letter_nova}1")
        title_cell = ws.cell(row=1, column=title_start_col, value="Informe de Actividades")
        title_cell.font = TITLE_FONT
        title_cell.alignment = CENTER_ALIGNMENT
        title_cell.fill = TABLE_HEADER_FILL
        for c_idx in range(1, total_cols_nova + 1):
            ws.cell(row=1, column=c_idx).fill = TABLE_HEADER_FILL
        ws.row_dimensions[1].height = 56

        ws["A2"] = "Fecha del Informe:"
        if report_date_raw:
            ws["B2"] = report_date_raw
        elif report_date:
            ws["B2"] = _format_date(report_date)
        elif period_end:
            ws["B2"] = _format_date(period_end)
        else:
            ws["B2"] = ""
        ws["A3"] = "Tema del Informe:"
        ws["B3"] = "Informe de Actividades"
        ws["A4"] = "Periodo Informe:"
        if periodo_raw:
            ws["B4"] = periodo_raw
        elif period_start and period_end:
            ws["B4"] = f"{_format_date(period_start)} - {_format_date(period_end)}"
        else:
            ws["B4"] = ""
        ws["A5"] = "Empresa:"
        ws["B5"] = company or ""
        ws["A6"] = "Consultor:"
        ws["B6"] = metrics.nombre

        # Titulo de tabla
        ws["A8"] = "Trabajo Realizado"
        ws["A8"].font = Font(name="Calibri", size=12, bold=True)

        # Escribir el DataFrame a partir de la fila 9
        date_col_indices = set()
        hour_col_indices = set()
        for r_idx, row in enumerate(
            dataframe_to_rows(metrics.dataframe, index=False, header=True), start=9
        ):
            for c_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=value)
                cell.border = THIN_BORDER

                # Header de tabla
                if r_idx == 9:
                    cell.font = TABLE_HEADER_FONT
                    cell.fill = TABLE_HEADER_FILL
                    cell.alignment = CENTER_ALIGNMENT
                    if value and "fecha" in str(value).lower():
                        date_col_indices.add(c_idx)
                    if value and "hora" in str(value).lower():
                        hour_col_indices.add(c_idx)
                else:
                    if c_idx in date_col_indices and value:
                        try:
                            parsed = None
                            if isinstance(value, (date, datetime)):
                                parsed = value
                            else:
                                text = str(value).strip()
                                for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
                                    try:
                                        parsed = datetime.strptime(text, fmt)
                                        break
                                    except ValueError:
                                        continue
                            if parsed:
                                cell.value = parsed
                                cell.number_format = "DD/MM/YYYY"
                        except Exception:
                            pass

                    if c_idx in hour_col_indices and value not in (None, ""):
                        cell.number_format = "0.0"

                    header_value = ws.cell(row=9, column=c_idx).value
                    header_text = str(header_value) if header_value is not None else ""
                    if header_text and "ticket" in header_text.lower():
                        raw = "" if value is None else str(value).strip()
                        normalized = re.sub(r"\s+", "", raw)
                        if not normalized:
                            cell.value = "SN"
                            cell.number_format = "@"
                        elif normalized.isdigit():
                            cell.value = int(normalized)
                            cell.number_format = "0"
                        else:
                            cell.value = normalized
                            cell.number_format = "@"
                        cell.alignment = RIGHT_ALIGNMENT
                    elif header_text == r"\NOVA\Tecnología - Documentos\IT\Desarrollo\Documentación\2025":
                        raw = "" if value is None else str(value).strip()
                        if not raw:
                            cell.value = "SN"
                            cell.number_format = "@"

        # Alinear a la derecha las columnas de Ticket (solo filas de datos)
        header_row = 9
        ticket_columns = []
        for col_idx in range(1, ws.max_column + 1):
            header_value = ws.cell(row=header_row, column=col_idx).value
            if header_value and "ticket" in str(header_value).lower():
                ticket_columns.append(col_idx)

        if ticket_columns:
            for col_idx in ticket_columns:
                for row_idx in range(header_row + 1, ws.max_row + 1):
                    ws.cell(row=row_idx, column=col_idx).alignment = RIGHT_ALIGNMENT

        # Ajustar anchos de columna automaticamente
        # Auto-ajuste robusto: evita fallo con celdas combinadas y mejora performance
        scan_max_row = min(ws.max_row, 300)
        for col_idx in range(1, ws.max_column + 1):
            max_length = 0
            column = get_column_letter(col_idx)
            for row_idx in range(1, scan_max_row + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                if isinstance(cell, MergedCell):
                    continue
                try:
                    cell_value = str(cell.value) if cell.value is not None else ""
                    if len(cell_value) > max_length:
                        max_length = len(cell_value)
                except (TypeError, AttributeError) as exc:
                    logger.debug("No se pudo procesar celda en columna %s: %s", column, exc)
                    continue
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width

        # ---------------------------------------------------------
        # Footer original (contenido adicional debajo de la tabla)
        # ---------------------------------------------------------
        footer_block = (metrics.metadata or {}).get("footer_block")
        if footer_block:
            # Calcular dónde termina la tabla NUEVA
            # Header está en fila 9, datos desde fila 10
            table_header_row = 9
            last_data_row = table_header_row + len(metrics.dataframe)
            
            # Obtener información del footer de la hoja ORIGINAL
            original_data_end = int(footer_block.get("data_end_row", 0))
            original_footer_start = int(footer_block.get("start_row", original_data_end + 1))
            original_footer_end = int(footer_block.get("max_row", original_footer_start))
            
            # En la nueva hoja: el footer debe empezar 2 filas después del último dato
            new_footer_start = last_data_row + 2
            
            # El offset es la diferencia entre donde comienza el footer nuevo y donde comenzaba en el original
            offset = new_footer_start - original_footer_start
            
            logger.debug(
                f"Footer: última_fila_original={original_data_end}, "
                f"footer_original={original_footer_start}-{original_footer_end}, "
                f"última_fila_nueva={last_data_row}, "
                f"footer_nuevo_inicia={new_footer_start}, "
                f"offset={offset}"
            )
            
            # Aplicar alturas de filas del footer
            for original_row, height in (footer_block.get("row_heights") or {}).items():
                new_row = original_row + offset
                ws.row_dimensions[new_row].height = height
            
            # Aplicar celdas del footer
            for cell_info in footer_block.get("cells", []):
                new_row = cell_info["row"] + offset
                col = cell_info["col"]
                cell = ws.cell(row=new_row, column=col, value=cell_info.get("value"))
                cell.font = cell_info.get("font")
                cell.fill = cell_info.get("fill")
                cell.border = cell_info.get("border")
                cell.alignment = cell_info.get("alignment")
                cell.number_format = cell_info.get("number_format") or cell.number_format
            
            # Aplicar merged cells del footer
            for min_row, min_col, max_row, max_col in footer_block.get("merges", []):
                try:
                    ws.merge_cells(
                        start_row=min_row + offset,
                        start_column=min_col,
                        end_row=max_row + offset,
                        end_column=max_col,
                    )
                except Exception as merge_exc:
                    logger.warning(f"No se pudo mergear footer cells: {merge_exc}")
    def _sanitize_sheet_name(self, name: str) -> str:
        """
        Sanitiza el nombre de una hoja de Excel.

        Args:
            name: Nombre original

        Returns:
            Nombre válido para Excel (max 31 caracteres, sin caracteres especiales)
        """
        # Caracteres no permitidos en nombres de hojas de Excel
        invalid_chars = ["\\", "/", "*", "?", "[", "]", ":"]
        sanitized = name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, "")

        # Truncar a 31 caracteres
        if len(sanitized) > 31:
            sanitized = sanitized[:31]

        return sanitized

    def _resolve_cliente_from_metrics(self) -> None:
        if not self.consultores_metrics:
            return
        cd_count = 0
        ti_count = 0
        for m in self.consultores_metrics:
            area = str((m.metadata or {}).get("area", "")).upper()
            if area == "CD":
                cd_count += 1
            else:
                ti_count += 1

        # Regla por mayoría: si hay más CD que TI -> CD, si no -> TI
        if cd_count > ti_count:
            self.cliente = "NOVA - Centro Digital"
        else:
            self.cliente = "BIT Nova"
