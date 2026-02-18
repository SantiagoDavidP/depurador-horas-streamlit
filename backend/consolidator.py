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
from copy import copy
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from openpyxl import Workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.drawing.image import Image
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter, column_index_from_string
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
COLOR_CYAN = "1BA9D5"              # Azul/cian (totales destacados)
COLOR_RED = "E74C3C"               # Rojo (total general)
COLOR_SENIOR_ROW = "E6D9F2"        # Morado claro (Senior)
COLOR_SEMISENIOR_ROW = "D6ECFA"    # Azul claro (Semisenior)
COLOR_JUNIOR_ROW = "E8F5E9"        # Verde claro (Junior)

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
TOTAL_ROW_HIGHLIGHT_FILL = PatternFill(start_color=COLOR_CYAN, end_color=COLOR_CYAN, fill_type="solid")
TOTAL_ROW_GRAND_FILL = PatternFill(start_color=COLOR_RED, end_color=COLOR_RED, fill_type="solid")
SENIOR_ROW_FILL = PatternFill(start_color=COLOR_SENIOR_ROW, end_color=COLOR_SENIOR_ROW, fill_type="solid")
SEMISENIOR_ROW_FILL = PatternFill(start_color=COLOR_SEMISENIOR_ROW, end_color=COLOR_SEMISENIOR_ROW, fill_type="solid")
JUNIOR_ROW_FILL = PatternFill(start_color=COLOR_JUNIOR_ROW, end_color=COLOR_JUNIOR_ROW, fill_type="solid")

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

    @staticmethod
    def _column_width_to_pixels(width: Optional[float]) -> int:
        # Aproximación estándar: Excel width -> px
        if width is None:
            width = 8.43
        return int(round(width * 7 + 5))

    @staticmethod
    def _row_height_to_pixels(height: Optional[float], default_height: Optional[float]) -> int:
        points = height if height is not None else (default_height or 15.0)
        return int(round(points * (96 / 72)))

    def _column_width_to_emu(self, width: Optional[float]) -> int:
        emu_per_px = 9525
        return self._column_width_to_pixels(width) * emu_per_px

    def _row_height_to_emu(self, height: Optional[float], default_height: Optional[float]) -> int:
        points = height if height is not None else (default_height or 15.0)
        return int(round(points * 12700))

    def _detect_header_band(
        self,
        ws: Worksheet,
        title_texts: List[str],
    ) -> Tuple[int, int, int, int]:
        """Detecta banda de header usando el rango merged del tÃ­tulo."""
        title_texts = [t.lower() for t in title_texts]
        title_cell = None
        for row in ws.iter_rows(min_row=1, max_row=8):
            for cell in row:
                if cell.value and any(t in str(cell.value).lower() for t in title_texts):
                    title_cell = cell
                    break
            if title_cell:
                break

        if not title_cell:
            return (1, 1, 1, ws.max_column or 1)

        # Buscar rango merged que contiene el tÃ­tulo
        merged_range = None
        for mr in ws.merged_cells.ranges:
            if mr.min_row <= title_cell.row <= mr.max_row and mr.min_col <= title_cell.column <= mr.max_col:
                merged_range = mr
                break

        if not merged_range:
            return (title_cell.row, title_cell.row, 1, ws.max_column or 1)

        r1 = merged_range.min_row
        r2 = merged_range.max_row
        c1 = merged_range.min_col
        c2 = merged_range.max_col

        # Extender hacia abajo mientras haya fill en la banda
        max_scan = min(r1 + 6, ws.max_row)
        for r in range(r1, max_scan + 1):
            has_fill = False
            for c in range(c1, c2 + 1):
                cell = ws.cell(row=r, column=c)
                if cell.fill and cell.fill.fill_type:
                    has_fill = True
                    break
            if has_fill:
                r2 = r
            else:
                break
        return (r1, r2, c1, c2)

    def _position_header_logo(
        self,
        ws: Worksheet,
        img_path: Path,
        *,
        header_rows: Optional[Tuple[int, int]] = None,
        logo_block_cols: Optional[Tuple[int, int]] = None,
        title_texts: Optional[List[str]] = None,
        max_width: int = 140,
        max_height: int = 48,
    ) -> None:
        """Inserta logo centrado vertical y horizontalmente dentro del header."""
        if not img_path.exists():
            return

        # Detectar banda de header
        if header_rows is None or logo_block_cols is None:
            r1, r2, c1, c2 = self._detect_header_band(
                ws, title_texts or ["informe de actividades", "informe consolidado de actividades"]
            )
            if header_rows is None:
                header_rows = (r1, r2)
            if logo_block_cols is None:
                # por defecto usa las Ãºltimas 2 columnas del header
                logo_block_cols = (max(c2 - 1, c1), c2)

        r1, r2 = header_rows
        c1, c2 = logo_block_cols

        # Eliminar logos previos en esa zona
        kept_images = []
        for img in getattr(ws, "_images", []):
            anchor = img.anchor
            img_col = None
            img_row = None
            if isinstance(anchor, str):
                try:
                    col_letter, row = re.match(r"([A-Z]+)(\d+)", anchor).groups()
                    img_col = column_index_from_string(col_letter)
                    img_row = int(row)
                except Exception:
                    img_col = None
            elif hasattr(anchor, "_from"):
                img_col = anchor._from.col + 1
                img_row = anchor._from.row + 1

            if img_col is not None and img_row is not None:
                if c1 <= img_col <= c2 and r1 <= img_row <= r2:
                    continue
            kept_images.append(img)
        ws._images = kept_images

        img = Image(str(img_path))
        if not img.width or not img.height:
            return

        # Escalar al mÃ¡ximo permitido
        width_scale = max_width / float(img.width)
        height_scale = max_height / float(img.height)
        scale = min(width_scale, height_scale)
        img.width = int(img.width * scale)
        img.height = int(img.height * scale)

        # Calcular tamaÃ±o del header en px
        header_height_px = 0
        default_height = getattr(ws.sheet_format, "defaultRowHeight", 15.0)
        for r in range(r1, r2 + 1):
            header_height_px += self._row_height_to_pixels(ws.row_dimensions[r].height, default_height)

        header_width_px = 0
        for c in range(c1, c2 + 1):
            col_letter = get_column_letter(c)
            header_width_px += self._column_width_to_pixels(ws.column_dimensions[col_letter].width)

        x_off_px = max(int(round((header_width_px - img.width) / 2)), 0)
        y_off_px = max(int(round((header_height_px - img.height) / 2)), 0)

        # EMU (openpyxl)
        emu_per_px = 9525
        marker = AnchorMarker(col=c1 - 1, colOff=x_off_px * emu_per_px, row=r1 - 1, rowOff=y_off_px * emu_per_px)
        ext = XDRPositiveSize2D(img.width * emu_per_px, img.height * emu_per_px)
        img.anchor = OneCellAnchor(_from=marker, ext=ext)
        ws.add_image(img)

    def _find_title_merge(
        self,
        ws: Worksheet,
        title_text: str,
    ) -> Optional[Tuple[int, int, int, int]]:
        """Encuentra el rango merged que contiene el tÃ­tulo."""
        target = title_text.lower()
        title_cell = None
        for row in ws.iter_rows(min_row=1, max_row=8):
            for cell in row:
                if cell.value and target in str(cell.value).lower():
                    title_cell = cell
                    break
            if title_cell:
                break
        if not title_cell:
            return None
        for mr in ws.merged_cells.ranges:
            if mr.min_row <= title_cell.row <= mr.max_row and mr.min_col <= title_cell.column <= mr.max_col:
                return (mr.min_row, mr.max_row, mr.min_col, mr.max_col)
        return (title_cell.row, title_cell.row, title_cell.column, title_cell.column)

    def _find_title_merge_any(
        self,
        ws: Worksheet,
        title_texts: List[str],
    ) -> Optional[Tuple[int, int, int, int]]:
        """Encuentra el rango merged que contiene cualquiera de los tÃƒÂ­tulos."""
        targets = [t.lower() for t in title_texts]
        title_cell = None
        for row in ws.iter_rows(min_row=1, max_row=8):
            for cell in row:
                if cell.value:
                    cell_text = str(cell.value).lower()
                    if any(t in cell_text for t in targets):
                        title_cell = cell
                        break
            if title_cell:
                break
        if not title_cell:
            return None
        for mr in ws.merged_cells.ranges:
            if mr.min_row <= title_cell.row <= mr.max_row and mr.min_col <= title_cell.column <= mr.max_col:
                return (mr.min_row, mr.max_row, mr.min_col, mr.max_col)
        return (title_cell.row, title_cell.row, title_cell.column, title_cell.column)

    def _get_last_header_col(
        self,
        ws: Worksheet,
        header_rows: Tuple[int, int],
        title_merge: Optional[Tuple[int, int, int, int]],
    ) -> int:
        """Detecta la Ãºltima columna usada en el header."""
        r1, r2 = header_rows
        last_col = title_merge[3] if title_merge else ws.max_column or 1
        max_col_scan = ws.max_column or last_col
        for c in range(1, max_col_scan + 1):
            for r in range(r1, r2 + 1):
                cell = ws.cell(row=r, column=c)
                if cell.value is not None:
                    last_col = max(last_col, c)
                if cell.fill and cell.fill.fill_type:
                    last_col = max(last_col, c)
        return last_col

    def get_header_rows(
        self,
        ws: Worksheet,
        title_texts: Optional[List[str]] = None,
    ) -> Tuple[Tuple[int, int], int, Optional[Tuple[int, int, int, int]]]:
        """Devuelve filas del header, alto en EMU y rango del título."""
        if not title_texts:
            title_texts = ["Informe de Actividades", "Informe Consolidado de Actividades"]
        title_merge = self._find_title_merge_any(ws, title_texts)
        if title_merge:
            title_min_row, title_max_row, title_min_col, title_max_col = title_merge
            header_start = 1
            header_end = title_max_row
            max_scan = min(title_max_row + 6, ws.max_row)
            for r in range(title_max_row + 1, max_scan + 1):
                has_fill = False
                for c in range(title_min_col, title_max_col + 1):
                    cell = ws.cell(row=r, column=c)
                    if cell.fill and cell.fill.fill_type:
                        has_fill = True
                        break
                if has_fill:
                    header_end = r
                else:
                    break
        else:
            header_start = 1
            header_end = min(3, ws.max_row or 3)

        header_rows = (header_start, header_end)
        header_height_emu = 0
        default_height = getattr(ws.sheet_format, "defaultRowHeight", 15.0)
        for r in range(header_start, header_end + 1):
            header_height_emu += self._row_height_to_emu(ws.row_dimensions[r].height, default_height)
        return header_rows, header_height_emu, title_merge

    def get_header_width(
        self,
        ws: Worksheet,
        header_rows: Tuple[int, int],
        title_merge: Optional[Tuple[int, int, int, int]],
    ) -> Tuple[int, int]:
        """Devuelve ancho del header en EMU y última columna usada."""
        last_col = self._get_last_header_col(ws, header_rows, title_merge)
        header_width_emu = 0
        for c in range(1, last_col + 1):
            col_letter = get_column_letter(c)
            header_width_emu += self._column_width_to_emu(ws.column_dimensions[col_letter].width)
        return header_width_emu, last_col

    def _get_title_x_range_emu(
        self,
        ws: Worksheet,
        title_merge: Optional[Tuple[int, int, int, int]],
        header_width_emu: int,
    ) -> Tuple[int, int]:
        if not title_merge or header_width_emu <= 0:
            return (int(round(header_width_emu * 0.35)), int(round(header_width_emu * 0.65)))
        _, _, title_min_col, title_max_col = title_merge
        start_x = 0
        for c in range(1, title_min_col):
            col_letter = get_column_letter(c)
            start_x += self._column_width_to_emu(ws.column_dimensions[col_letter].width)
        end_x = start_x
        for c in range(title_min_col, title_max_col + 1):
            col_letter = get_column_letter(c)
            end_x += self._column_width_to_emu(ws.column_dimensions[col_letter].width)
        if start_x <= header_width_emu * 0.1 and end_x >= header_width_emu * 0.9:
            return (int(round(header_width_emu * 0.35)), int(round(header_width_emu * 0.65)))
        return (start_x, end_x)

    def xy_to_anchor(
        self,
        ws: Worksheet,
        x_emu: int,
        y_emu: int,
        start_row: int = 1,
    ) -> Tuple[int, int, int, int]:
        """Convierte x/y en EMU a (col,row,colOff,rowOff) 0-based."""
        x_emu = max(int(x_emu), 0)
        y_emu = max(int(y_emu), 0)

        col_idx = 1
        x_acc = 0
        while True:
            col_letter = get_column_letter(col_idx)
            col_w = self._column_width_to_emu(ws.column_dimensions[col_letter].width)
            if x_acc + col_w > x_emu or col_idx >= (ws.max_column or 1):
                break
            x_acc += col_w
            col_idx += 1
        col_off = max(x_emu - x_acc, 0)

        row_idx = start_row
        y_acc = 0
        default_height = getattr(ws.sheet_format, "defaultRowHeight", 15.0)
        max_row = ws.max_row or start_row
        while True:
            row_h = self._row_height_to_emu(ws.row_dimensions[row_idx].height, default_height)
            if y_acc + row_h > y_emu or row_idx >= max_row:
                break
            y_acc += row_h
            row_idx += 1
        row_off = max(y_emu - y_acc, 0)

        return col_idx - 1, row_idx - 1, int(col_off), int(row_off)

    def _image_anchor_xy_emu(
        self,
        ws: Worksheet,
        img: Image,
    ) -> Optional[Tuple[int, int, int]]:
        anchor = img.anchor
        emu_per_px = 9525
        default_height = getattr(ws.sheet_format, "defaultRowHeight", 15.0)

        def _col_start(col_idx: int) -> int:
            total = 0
            for c in range(1, col_idx):
                col_letter = get_column_letter(c)
                total += self._column_width_to_emu(ws.column_dimensions[col_letter].width)
            return total

        def _row_start(row_idx: int) -> int:
            total = 0
            for r in range(1, row_idx):
                total += self._row_height_to_emu(ws.row_dimensions[r].height, default_height)
            return total

        if isinstance(anchor, str):
            try:
                col_letter, row = re.match(r"([A-Z]+)(\d+)", anchor).groups()
                col_idx = column_index_from_string(col_letter)
                row_idx = int(row)
                x_emu = _col_start(col_idx)
                y_emu = _row_start(row_idx)
                return (x_emu, y_emu, row_idx)
            except Exception:
                return None
        if hasattr(anchor, "_from"):
            try:
                col_idx = anchor._from.col + 1
                row_idx = anchor._from.row + 1
                col_off = int(getattr(anchor._from, "colOff", 0))
                row_off = int(getattr(anchor._from, "rowOff", 0))
                x_emu = _col_start(col_idx) + col_off
                y_emu = _row_start(row_idx) + row_off
                return (x_emu, y_emu, row_idx)
            except Exception:
                return None
        if hasattr(anchor, "col") and hasattr(anchor, "row"):
            try:
                col_idx = int(anchor.col) + 1
                row_idx = int(anchor.row) + 1
                x_emu = _col_start(col_idx)
                y_emu = _row_start(row_idx)
                return (x_emu, y_emu, row_idx)
            except Exception:
                return None
        # Fallback con imagen en px si no hay anchor
        if img.width and img.height:
            return (0, 0, 1)
        return None

    def extract_logo_reference_from_resumen(
        self,
        wb: Workbook,
    ) -> Optional[Tuple[Dict[str, int], Dict[str, int]]]:
        """Extrae tamaños (cx/cy) desde la hoja Resumen para BIT y NOVA."""
        ws = wb["Resumen"] if "Resumen" in wb.sheetnames else wb.worksheets[0]
        header_rows, header_height_emu, _ = self.get_header_rows(ws)
        header_height_emu = max(header_height_emu, 1)

        header_images: List[Tuple[Image, int]] = []
        for img in getattr(ws, "_images", []):
            pos = self._image_anchor_xy_emu(ws, img)
            if not pos:
                continue
            x_emu, _, row_idx = pos
            if header_rows[0] <= row_idx <= header_rows[1]:
                header_images.append((img, x_emu))

        if len(header_images) < 2:
            return None

        header_images.sort(key=lambda item: item[1])
        left_img = header_images[0][0]
        right_img = header_images[-1][0]

        def _extract_ext(img: Image) -> Optional[Tuple[int, int]]:
            if hasattr(img.anchor, "ext") and img.anchor.ext:
                cx = int(getattr(img.anchor.ext, "cx", 0))
                cy = int(getattr(img.anchor.ext, "cy", 0))
                if cx > 0 and cy > 0:
                    return (cx, cy)
            if img.width and img.height:
                emu_per_px = 9525
                return (int(img.width) * emu_per_px, int(img.height) * emu_per_px)
            return None

        left_ext = _extract_ext(left_img)
        right_ext = _extract_ext(right_img)
        if not left_ext or not right_ext:
            return None

        return (
            {"cx": left_ext[0], "cy": left_ext[1]},
            {"cx": right_ext[0], "cy": right_ext[1]},
        )

    def normalize_sheet_header_logos(
        self,
        ws: Worksheet,
        ref_bit: Dict[str, int],
        ref_nova: Dict[str, int],
        bit_logo_path: Optional[Path],
        nova_logo_path: Optional[Path],
        *,
        title_texts: Optional[List[str]] = None,
    ) -> None:
        if not bit_logo_path or not nova_logo_path:
            return
        if not bit_logo_path.exists() or not nova_logo_path.exists():
            return

        header_rows, header_height_emu, title_merge = self.get_header_rows(ws, title_texts)
        header_width_emu, _ = self.get_header_width(ws, header_rows, title_merge)
        if header_width_emu <= 0 or header_height_emu <= 0:
            return

        title_x_start_emu, title_x_end_emu = self._get_title_x_range_emu(ws, title_merge, header_width_emu)

        # Eliminar logos existentes (izq/der) sin tocar otras imágenes
        header_images: List[Tuple[Image, int]] = []
        for img in getattr(ws, "_images", []):
            pos = self._image_anchor_xy_emu(ws, img)
            if not pos:
                continue
            x_emu, _, row_idx = pos
            if header_rows[0] <= row_idx <= header_rows[1]:
                header_images.append((img, x_emu))

        to_remove: Set[Image] = set()
        if header_images:
            header_images.sort(key=lambda item: item[1])
            to_remove.add(header_images[0][0])
            to_remove.add(header_images[-1][0])

        ws._images = [img for img in getattr(ws, "_images", []) if img not in to_remove]

        emu_per_px = 9525
        margin_left_emu = int(round(18 * emu_per_px))
        margin_right_emu = int(round(24 * emu_per_px))
        gap_title_emu = int(round(12 * emu_per_px))

        # BIT (izquierda)
        bit_cx = int(ref_bit.get("cx", 0))
        bit_cy = int(ref_bit.get("cy", 0))
        if bit_cx > 0 and bit_cy > 0:
            bit_y = max(int(round((header_height_emu - bit_cy) / 2)), 0)
            bit_x = margin_left_emu
            max_left = max(title_x_start_emu - gap_title_emu, 0)
            x_max = max_left - bit_cx
            if bit_x > x_max:
                bit_x = max(0, x_max)
            if bit_x + bit_cx > max_left:
                available = max_left
                scale = min(
                    available / float(bit_cx) if bit_cx else 0.0,
                    header_height_emu / float(bit_cy) if bit_cy else 0.0,
                ) * 0.98
                if scale > 0 and scale < 1:
                    bit_cx = max(int(bit_cx * scale), 1)
                    bit_cy = max(int(bit_cy * scale), 1)
                    bit_y = max(int(round((header_height_emu - bit_cy) / 2)), 0)
                    bit_x = max(0, max_left - bit_cx)
                    logger.info("Escalado de emergencia aplicado al logo BIT (%.2f).", scale)
            self.place_logo_fixed(ws, bit_logo_path, bit_cx, bit_cy, bit_x, bit_y, header_rows[0])

        # NOVA (derecha)
        nova_cx = int(ref_nova.get("cx", 0))
        nova_cy = int(ref_nova.get("cy", 0))
        if nova_cx > 0 and nova_cy > 0:
            nova_y = max(int(round((header_height_emu - nova_cy) / 2)), 0)
            nova_x = header_width_emu - margin_right_emu - nova_cx
            min_right = title_x_end_emu + gap_title_emu
            if nova_x < min_right:
                nova_x = min_right
            if nova_x + nova_cx > header_width_emu:
                nova_x = max(0, header_width_emu - nova_cx)
            if nova_x < min_right:
                available = max(header_width_emu - min_right, 0)
                scale = min(
                    available / float(nova_cx) if nova_cx else 0.0,
                    header_height_emu / float(nova_cy) if nova_cy else 0.0,
                ) * 0.98
                if scale > 0 and scale < 1:
                    nova_cx = max(int(nova_cx * scale), 1)
                    nova_cy = max(int(nova_cy * scale), 1)
                    nova_y = max(int(round((header_height_emu - nova_cy) / 2)), 0)
                    nova_x = max(0, header_width_emu - margin_right_emu - nova_cx)
                    logger.info("Escalado de emergencia aplicado al logo NOVA (%.2f).", scale)
            self.place_logo_fixed(ws, nova_logo_path, nova_cx, nova_cy, nova_x, nova_y, header_rows[0])

    def _get_image_dimensions_px(self, img_path: Path) -> Optional[Tuple[int, int]]:
        if not img_path or not img_path.exists():
            return None
        try:
            if PILImage:
                with PILImage.open(img_path) as pil_img:
                    return (pil_img.width, pil_img.height)
            img = Image(str(img_path))
            if img.width and img.height:
                return (int(img.width), int(img.height))
        except Exception as exc:
            logger.warning("No se pudo leer el tamaño del logo %s: %s", img_path, exc)
        return None

    def _compute_target_size(
        self,
        img_path: Path,
        max_width: int,
        max_height: int,
    ) -> Optional[Tuple[int, int]]:
        dims = self._get_image_dimensions_px(img_path)
        if not dims:
            return None
        img_w, img_h = dims
        if img_w <= 0 or img_h <= 0:
            return None
        width_scale = max_width / float(img_w) if max_width else 1.0
        height_scale = max_height / float(img_h) if max_height else width_scale
        scale = min(width_scale, height_scale)
        return (int(img_w * scale), int(img_h * scale))

    def get_header_metrics(
        self,
        ws: Worksheet,
        title_text: str = "Informe de Actividades",
    ) -> Dict[str, object]:
        """Calcula métricas del header para posicionar logos con márgenes."""
        title_merge = self._find_title_merge(ws, title_text)
        if title_merge:
            title_min_row, title_max_row, title_min_col, title_max_col = title_merge
            header_start = 1
            header_end = title_max_row
            max_scan = min(title_max_row + 6, ws.max_row)
            for r in range(title_max_row + 1, max_scan + 1):
                has_fill = False
                for c in range(title_min_col, title_max_col + 1):
                    cell = ws.cell(row=r, column=c)
                    if cell.fill and cell.fill.fill_type:
                        has_fill = True
                        break
                if has_fill:
                    header_end = r
                else:
                    break
        else:
            header_start = 1
            header_end = min(3, ws.max_row or 3)
            title_min_row = header_start
            title_max_row = header_end
            title_min_col = 1
            title_max_col = 1

        header_rows = (header_start, header_end)
        last_col = self._get_last_header_col(ws, header_rows, title_merge)

        header_height_px = 0
        default_height = getattr(ws.sheet_format, "defaultRowHeight", 15.0)
        for r in range(header_start, header_end + 1):
            header_height_px += self._row_height_to_pixels(ws.row_dimensions[r].height, default_height)

        header_width_px = 0
        for c in range(1, last_col + 1):
            col_letter = get_column_letter(c)
            header_width_px += self._column_width_to_pixels(ws.column_dimensions[col_letter].width)

        title_x_start_px = 0
        title_x_end_px = header_width_px
        if title_merge:
            title_x_start_px = 0
            for c in range(1, title_min_col):
                col_letter = get_column_letter(c)
                title_x_start_px += self._column_width_to_pixels(ws.column_dimensions[col_letter].width)
            title_x_end_px = title_x_start_px
            for c in range(title_min_col, title_max_col + 1):
                col_letter = get_column_letter(c)
                title_x_end_px += self._column_width_to_pixels(ws.column_dimensions[col_letter].width)

        if header_width_px > 0:
            # Cuando el título ocupa casi todo el ancho, usa una zona central segura
            if title_x_start_px <= header_width_px * 0.1 and title_x_end_px >= header_width_px * 0.9:
                title_x_start_px = int(round(header_width_px * 0.35))
                title_x_end_px = int(round(header_width_px * 0.65))

        return {
            "headerRows": header_rows,
            "headerHeightPx": header_height_px,
            "headerWidthPx": header_width_px,
            "titleXStartPx": title_x_start_px,
            "titleXEndPx": title_x_end_px,
            "lastColUsedInHeader": last_col,
        }

    def place_logo_fixed(
        self,
        ws: Worksheet,
        img_path: Path,
        cx: int,
        cy: int,
        x_emu: int,
        y_emu: int,
        header_start_row: int,
    ) -> None:
        """Inserta un logo en posición absoluta (EMU) respecto al inicio del header."""
        if not img_path or not img_path.exists():
            return
        if cx <= 0 or cy <= 0:
            return

        img = Image(str(img_path))
        col_idx0, row_idx0, col_off, row_off = self.xy_to_anchor(ws, x_emu, y_emu, start_row=header_start_row)
        marker = AnchorMarker(
            col=col_idx0,
            colOff=col_off,
            row=row_idx0,
            rowOff=row_off,
        )
        ext = XDRPositiveSize2D(int(cx), int(cy))
        img.anchor = OneCellAnchor(_from=marker, ext=ext)
        ws.add_image(img)

    def normalize_header_logos(
        self,
        ws: Worksheet,
        bit_logo_path: Optional[Path],
        nova_logo_path: Optional[Path],
        *,
        title_text: str = "Informe de Actividades",
        bit_max_size: Tuple[int, int] = (150, 52),
        nova_max_size: Tuple[int, int] = (140, 48),
        margin_left_px: int = 18,
        margin_right_px: int = 18,
        safe_gap_px: int = 12,
    ) -> None:
        """Wrapper legacy: usa tamaños fijos (px) y normaliza con EMU."""
        if not bit_logo_path or not nova_logo_path:
            return
        bit_target = self._compute_target_size(bit_logo_path, *bit_max_size)
        nova_target = self._compute_target_size(nova_logo_path, *nova_max_size)
        if not bit_target or not nova_target:
            return
        emu_per_px = 9525
        ref_bit = {"cx": int(bit_target[0]) * emu_per_px, "cy": int(bit_target[1]) * emu_per_px}
        ref_nova = {"cx": int(nova_target[0]) * emu_per_px, "cy": int(nova_target[1]) * emu_per_px}
        self.normalize_sheet_header_logos(
            ws,
            ref_bit,
            ref_nova,
            bit_logo_path,
            nova_logo_path,
            title_texts=[title_text, "Informe Consolidado de Actividades"],
        )

    def _position_logo_in_block(
        self,
        ws: Worksheet,
        img_path: Path,
        header_rows: Tuple[int, int],
        block_cols: Tuple[int, int],
        *,
        max_width: int,
        max_height: int,
    ) -> None:
        if not img_path.exists():
            return
        img = Image(str(img_path))
        if not img.width or not img.height:
            return

        r1, r2 = header_rows
        c1, c2 = block_cols

        header_height_px = 0
        default_height = getattr(ws.sheet_format, "defaultRowHeight", 15.0)
        for r in range(r1, r2 + 1):
            header_height_px += self._row_height_to_pixels(ws.row_dimensions[r].height, default_height)

        block_width_px = 0
        for c in range(c1, c2 + 1):
            col_letter = get_column_letter(c)
            block_width_px += self._column_width_to_pixels(ws.column_dimensions[col_letter].width)

        # Escalado anti-recorte
        scale = min(
            block_width_px / float(img.width) if block_width_px else 1.0,
            header_height_px / float(img.height) if header_height_px else 1.0,
            max_width / float(img.width),
            max_height / float(img.height),
        )
        scale = min(scale, 1.0)
        img.width = int(img.width * scale)
        img.height = int(img.height * scale)

        x_off_px = max(int(round((block_width_px - img.width) / 2)), 0)
        y_off_px = max(int(round((header_height_px - img.height) / 2)), 0)

        emu_per_px = 9525
        marker = AnchorMarker(col=c1 - 1, colOff=x_off_px * emu_per_px, row=r1 - 1, rowOff=y_off_px * emu_per_px)
        ext = XDRPositiveSize2D(img.width * emu_per_px, img.height * emu_per_px)
        img.anchor = OneCellAnchor(_from=marker, ext=ext)
        ws.add_image(img)

    def get_header_layout(
        self,
        ws: Worksheet,
        title_text: str = "Informe de Actividades",
    ) -> Dict[str, object]:
        """Detecta layout del header y calcula cajas para logos."""
        title_merge = self._find_title_merge(ws, title_text)
        if title_merge:
            header_rows = (1, title_merge[1])
        else:
            header_rows = (1, min(3, ws.max_row or 3))

        last_col = self._get_last_header_col(ws, header_rows, title_merge)

        def _box_width_px(c1: int, c2: int) -> int:
            width = 0
            for c in range(c1, c2 + 1):
                col_letter = get_column_letter(c)
                width += self._column_width_to_pixels(ws.column_dimensions[col_letter].width)
            return width

        header_height_px = 0
        default_height = getattr(ws.sheet_format, "defaultRowHeight", 15.0)
        for r in range(header_rows[0], header_rows[1] + 1):
            header_height_px += self._row_height_to_pixels(ws.row_dimensions[r].height, default_height)

        if title_merge:
            left_box = (1, max(title_merge[2] - 1, 1))
            right_box = (min(title_merge[3] + 1, last_col), last_col)
        else:
            left_box = (1, max(1, min(3, last_col)))
            right_box = (max(1, last_col - 1), last_col)

        min_box_px = 60
        left_w = _box_width_px(left_box[0], left_box[1]) if left_box[1] >= left_box[0] else 0
        right_w = _box_width_px(right_box[0], right_box[1]) if right_box[1] >= right_box[0] else 0

        if left_w < min_box_px or right_w < min_box_px:
            # Fallback por porcentaje
            left_end = max(1, int(round(last_col * 0.2)))
            right_start = max(left_end + 1, int(round(last_col * 0.8)))
            left_box = (1, left_end)
            right_box = (right_start, last_col)

        return {
            "header_rows": header_rows,
            "title_merge_range": title_merge,
            "lastColUsedInHeader": last_col,
            "leftLogoBox": left_box,
            "rightLogoBox": right_box,
            "headerHeightPx": header_height_px,
        }

    def place_logo_in_box(
        self,
        ws: Worksheet,
        img_path: Path,
        box: Tuple[int, int],
        header_rows: Tuple[int, int],
        max_scale: float = 1.0,
    ) -> None:
        """Posiciona logo dentro de un box con escalado y offsets reales."""
        if not img_path.exists():
            return

        if PILImage:
            with PILImage.open(img_path) as pil_img:
                img_w = pil_img.width
                img_h = pil_img.height
        else:
            img = Image(str(img_path))
            img_w = img.width
            img_h = img.height

        if not img_w or not img_h:
            return

        r1, r2 = header_rows
        c1, c2 = box

        header_height_px = 0
        default_height = getattr(ws.sheet_format, "defaultRowHeight", 15.0)
        for r in range(r1, r2 + 1):
            header_height_px += self._row_height_to_pixels(ws.row_dimensions[r].height, default_height)

        box_width_px = 0
        for c in range(c1, c2 + 1):
            col_letter = get_column_letter(c)
            box_width_px += self._column_width_to_pixels(ws.column_dimensions[col_letter].width)

        if box_width_px == 0 or header_height_px == 0:
            return

        scale = min(box_width_px / float(img_w), header_height_px / float(img_h)) * 0.92
        if max_scale is not None:
            scale = min(scale, max_scale)

        new_w = int(img_w * scale)
        new_h = int(img_h * scale)

        x_off_px = max(int(round((box_width_px - new_w) / 2)), 0)
        y_off_px = max(int(round((header_height_px - new_h) / 2)), 0)

        img = Image(str(img_path))
        img.width = new_w
        img.height = new_h

        emu_per_px = 9525
        marker = AnchorMarker(col=c1 - 1, colOff=x_off_px * emu_per_px, row=r1 - 1, rowOff=y_off_px * emu_per_px)
        ext = XDRPositiveSize2D(new_w * emu_per_px, new_h * emu_per_px)
        img.anchor = OneCellAnchor(_from=marker, ext=ext)
        ws.add_image(img)

    def normalize_header(
        self,
        ws: Worksheet,
        bit_logo_path: Optional[Path],
        nova_logo_path: Optional[Path],
        title_text: str = "Informe de Actividades",
    ) -> None:
        """Normaliza logos BIT/NOVA con layout detectado del header."""
        layout = self.get_header_layout(ws, title_text=title_text)
        header_rows = layout["header_rows"]
        left_box = layout["leftLogoBox"]
        right_box = layout["rightLogoBox"]
        last_col = layout["lastColUsedInHeader"]

        # Eliminar logos existentes en header (izq/der)
        kept_images = []
        for img in getattr(ws, "_images", []):
            anchor = img.anchor
            img_col = None
            img_row = None
            if isinstance(anchor, str):
                try:
                    col_letter, row = re.match(r"([A-Z]+)(\d+)", anchor).groups()
                    img_col = column_index_from_string(col_letter)
                    img_row = int(row)
                except Exception:
                    img_col = None
            elif hasattr(anchor, "_from"):
                img_col = anchor._from.col + 1
                img_row = anchor._from.row + 1

            if img_col is not None and img_row is not None:
                if header_rows[0] <= img_row <= header_rows[1]:
                    if img_col <= int(last_col * 0.3) or img_col >= int(last_col * 0.7):
                        continue
            kept_images.append(img)
        ws._images = kept_images

        if bit_logo_path and bit_logo_path.exists():
            self.place_logo_in_box(ws, bit_logo_path, left_box, header_rows, max_scale=1.0)
        if nova_logo_path and nova_logo_path.exists():
            self.place_logo_in_box(ws, nova_logo_path, right_box, header_rows, max_scale=1.0)

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
        collab = rates_manager.find_collaborator(nombre)
        if collab and collab.nombre_completo:
            nombre = collab.nombre_completo
            metadata["employee"] = nombre

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
    def _excel_safe_value(value: object) -> object:
        """Evita que openpyxl falle con valores <NA> o NaN."""
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        return value

    @staticmethod
    def _get_used_range_limits(ws: Worksheet) -> Tuple[int, int]:
        max_row = 0
        max_col = 0
        for cell in ws._cells.values():
            value = cell.value
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if cell.row > max_row:
                max_row = cell.row
            if cell.column > max_col:
                max_col = cell.column
        for merged in ws.merged_cells.ranges:
            if merged.max_row > max_row:
                max_row = merged.max_row
            if merged.max_col > max_col:
                max_col = merged.max_col
        if max_row == 0:
            max_row = ws.max_row or 1
        if max_col == 0:
            max_col = ws.max_column or 1
        return max_row, max_col

    @staticmethod
    def _row_is_empty(ws: Worksheet, row: int, max_col: int) -> bool:
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            value = cell.value
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return False
        return True

    @staticmethod
    def _row_has_merge(merged_ranges: List[object], row: int) -> bool:
        for merged in merged_ranges:
            if merged.min_row <= row <= merged.max_row:
                return True
        return False

    @staticmethod
    def _clear_row_format(ws: Worksheet, row: int, max_col: int) -> None:
        ws.row_dimensions[row].height = None
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            if isinstance(cell, MergedCell):
                continue
            cell.border = Border()
            cell.fill = PatternFill()
            cell.alignment = Alignment()
            cell.number_format = "General"

    def clean_blank_rows_and_footer(self, ws: Worksheet) -> None:
        max_row, max_col = self._get_used_range_limits(ws)
        footer_row = None
        for row in range(1, max_row + 1):
            value = ws.cell(row=row, column=1).value
            if value is None:
                continue
            text = str(value).strip().lower()
            if text.startswith("elaborado por"):
                footer_row = row
                break

        if not footer_row:
            logger.debug("No se encontró footer en hoja '%s'.", ws.title)
            return

        last_data_row = None
        for row in range(footer_row - 1, 0, -1):
            if not self._row_is_empty(ws, row, max_col):
                last_data_row = row
                break
        if last_data_row is None:
            last_data_row = footer_row - 1

        merged_ranges = list(ws.merged_cells.ranges)
        deleted_between = 0
        cleaned_between = 0
        for row in range(footer_row - 1, last_data_row, -1):
            if self._row_is_empty(ws, row, max_col):
                if not self._row_has_merge(merged_ranges, row):
                    ws.delete_rows(row, 1)
                    deleted_between += 1
                else:
                    self._clear_row_format(ws, row, max_col)
                    cleaned_between += 1

        if deleted_between:
            footer_row -= deleted_between

        max_row, max_col = self._get_used_range_limits(ws)
        merged_ranges = list(ws.merged_cells.ranges)
        rows_to_delete_footer: List[int] = []
        cleaned_footer = 0
        empty_streak = 0
        for row in range(footer_row, max_row + 1):
            if self._row_is_empty(ws, row, max_col):
                empty_streak += 1
                if empty_streak == 1:
                    self._clear_row_format(ws, row, max_col)
                    cleaned_footer += 1
                else:
                    if not self._row_has_merge(merged_ranges, row):
                        rows_to_delete_footer.append(row)
                    else:
                        self._clear_row_format(ws, row, max_col)
                        cleaned_footer += 1
            else:
                empty_streak = 0

        deleted_footer = 0
        for row in reversed(rows_to_delete_footer):
            ws.delete_rows(row, 1)
            deleted_footer += 1

        logger.info(
            "Limpieza footer hoja '%s': footer_row=%s last_data_row=%s "
            "eliminadas_entre=%d limpiadas_entre=%d eliminadas_footer=%d limpiadas_footer=%d",
            ws.title,
            footer_row,
            last_data_row,
            deleted_between,
            cleaned_between,
            deleted_footer,
            cleaned_footer,
        )

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

    def _get_sorted_metrics(
        self, metrics_list: Optional[List["ConsultorMetrics"]] = None
    ) -> List["ConsultorMetrics"]:
        """Ordena consultores por cargo (Senior -> Semisenior -> Junior) y nombre."""
        metrics_list = metrics_list or self.consultores_metrics

        def _normalize_seniority(value: object) -> str:
            text = str(value or "").strip().lower()
            if "semi" in text:
                return "Semisenior"
            if "senior" in text:
                return "Senior"
            if "junior" in text:
                return "Junior"
            return str(value or "").strip() or "Junior"

        seniority_order = {"Senior": 1, "Semisenior": 2, "Junior": 3}
        return sorted(
            metrics_list,
            key=lambda m: (seniority_order.get(_normalize_seniority(m.cargo), 4), m.nombre),
        )

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

        sorted_metrics = self._get_sorted_metrics(self.consultores_metrics)

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
        sheet_names = [
            self._sanitize_sheet_name(f"{idx}. {metrics.nombre}")
            for idx, metrics in enumerate(sorted_metrics, start=1)
        ]
        self._create_summary_sheet(
            ws_resumen, periodo, dias_laborables, sorted_metrics, sheet_names
        )

        sheet_df_map: Dict[str, pd.DataFrame] = {}

        # 2. Crear hojas individuales por consultor
        for idx, metrics in enumerate(sorted_metrics, start=1):
            sheet_name = self._sanitize_sheet_name(f"{idx}. {metrics.nombre}")
            ws_individual = wb.create_sheet(sheet_name)
            self._create_individual_sheet(ws_individual, metrics)
            sheet_df_map[sheet_name] = metrics.dataframe

        # Normalizar logos en header usando referencia del Resumen
        if self.client_logo_path and self.logo_path:
            refs = self.extract_logo_reference_from_resumen(wb)
            if refs:
                ref_bit, ref_nova = refs
                for ws in wb.worksheets:
                    self.normalize_sheet_header_logos(
                        ws,
                        ref_bit,
                        ref_nova,
                        self.logo_path,
                        self.client_logo_path,
                        title_texts=[
                            "Informe de Actividades",
                            "Informe Consolidado de Actividades",
                            "INFORME ACTIVIDADES OUTSOURCING BUSINESS IT",
                        ],
                    )
            else:
                logger.warning("No se pudo extraer referencia de logos desde Resumen.")

        # Post-procesar tablas para ocultar filas vacias (sin tocar footer)
        self.postprocess_hide_empty_table_rows_preserve_footer(wb, sheet_df_map)

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

        # Limpieza visual final de tablas (no toca footer)
        self.postprocess_hide_empty_table_rows_preserve_footer(wb, {ws.title: metrics.dataframe})

        # Normalizar logos en header usando referencia del propio sheet
        if self.client_logo_path and self.logo_path:
            refs = self.extract_logo_reference_from_resumen(wb)
            if refs:
                ref_bit, ref_nova = refs
                self.normalize_sheet_header_logos(
                    ws,
                    ref_bit,
                    ref_nova,
                    self.logo_path,
                    self.client_logo_path,
                    title_texts=[
                        "Informe de Actividades",
                        "Informe Consolidado de Actividades",
                        "INFORME ACTIVIDADES OUTSOURCING BUSINESS IT",
                    ],
                )

        from io import BytesIO
        buffer = BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    def _create_summary_sheet(
        self,
        ws: Worksheet,
        periodo: str,
        dias_laborables: int,
        sorted_metrics: List["ConsultorMetrics"],
        sheet_names: Optional[List[str]] = None,
    ) -> None:
        """Crea la hoja de resumen con diseno corporativo NOVA-TI."""
        # Limpieza de merges previos para evitar conflictos con el nuevo layout
        for merged_range in list(ws.merged_cells.ranges):
            ws.unmerge_cells(str(merged_range))

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
            # Logo cliente en resumen
            client_stem = self.client_logo_path.stem.lower()
            if "nova" in client_stem:
                # Insercion temporal para obtener el tamano de referencia
                self._add_logo(ws, anchor=f"{end_col}1", logo_path=self.client_logo_path, max_width=150, max_height=52)
            elif "baninter" in client_stem:
                self._add_logo(ws, anchor="L1", logo_path=self.client_logo_path, max_width=150, max_height=52)
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
            cargo_norm = str(metrics.cargo or "").lower().strip()
            if "semi" in cargo_norm:
                row_fill = SEMISENIOR_ROW_FILL
            elif "senior" in cargo_norm:
                row_fill = SENIOR_ROW_FILL
            elif "junior" in cargo_norm:
                row_fill = JUNIOR_ROW_FILL
            else:
                row_fill = None
            horas_extras_formula = None
            if sheet_names and idx - 1 < len(sheet_names):
                sheet_name = sheet_names[idx - 1]
                last_detail_row = 9 + len(metrics.dataframe)
                has_hour_col = False
                for col in list(metrics.dataframe.columns):
                    header = str(col).strip().lower()
                    if "hora" in header and "tipo" not in header:
                        has_hour_col = True
                        break
                total_row = (last_detail_row + 1) if has_hour_col else None
                last_data_row = total_row or last_detail_row
                start_row = max(last_data_row + 2, 41)
                r_total_2 = start_row + 1
                r_total_3 = start_row + 2
                horas_extras_formula = f"='{sheet_name}'!L{r_total_2}+'{sheet_name}'!L{r_total_3}"
            values = [
                idx,
                metrics.nombre,
                metrics.cargo,
                None,  # DIAS LABORADOS (formula desde header)
                round(metrics.valor_tarifa, 2),
                None,  # VALOR DÍA (formula)
                None,  # TOTAL (formula)
                None,  # DIAS LABORADOS REALES (formula desde HN)
                round(metrics.total_horas_normales, 2),  # HN (valor)
                horas_extras_formula or round(metrics.total_horas_extras, 2),
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
                elif col_idx == 8:  # DIAS LABORADOS = HN (col 9) / 8
                    cell.value = f"=I{row}/8"
                elif col_idx == 11:  # VALOR A FACTURAR = DIAS LABORADOS (col 8) * VALOR DÍA
                    cell.value = f"=H{row}*F{row}"
                elif col_idx == 13:  # Total Horas Extras = Valor Horas Extras * Horas Extras
                    cell.value = f"=L{row}*J{row}"
                elif col_idx == 14:  # TOTAL GENERAL solo se calcula en la fila TOTAL
                    cell.value = None

                if row_fill:
                    cell.fill = row_fill
                elif idx % 2 == 0:
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
            8: f"=SUM(H{header_row + 1}:H{total_row - 1})",
            9: f"=SUM(I{header_row + 1}:I{total_row - 1})",
            10: f"=SUM(J{header_row + 1}:J{total_row - 1})",
            11: f"=SUM(K{header_row + 1}:K{total_row - 1})",
            12: '',
            13: f"=SUM(M{header_row + 1}:M{total_row - 1})",
            14: f"=K{total_row}+M{total_row}",
        }

        highlight_total_cols = {9, 11, 13}
        for col_idx, total_value in totals.items():
            cell = ws.cell(row=total_row, column=col_idx, value=total_value)
            cell.font = TOTAL_ROW_FONT
            if col_idx == 14:
                cell.fill = TOTAL_ROW_GRAND_FILL
            elif col_idx in highlight_total_cols:
                cell.fill = TOTAL_ROW_HIGHLIGHT_FILL
            else:
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
        # Eliminar columnas vacias al final (evita columna extra en el Excel)
        drop_cols = []
        for col in list(dataframe.columns):
            header = str(col).strip()
            if header == "" or header.startswith("Col_"):
                series = dataframe[col]
                if series.isna().all() or series.astype(str).str.strip().eq("").all():
                    drop_cols.append(col)
        if drop_cols:
            dataframe = dataframe.drop(columns=drop_cols)
        metadata = metrics.metadata or {}

        def _format_date_only(value: object) -> str:
            if not value:
                return ""
            if isinstance(value, (date, datetime)):
                return value.strftime("%d/%m/%Y")
            text = str(value).strip()
            # Evitar mostrar hora cuando llega "2026-01-01 00:00:00"
            if " " in text:
                text = text.split(" ")[0]
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
                    return raw_text if raw_text else ""
            return ""

        report_date_raw = _raw_from_metadata(["fecha del informe", "fecha informe"])
        period_raw = _raw_from_metadata(["periodo informe", "periodo"])

        report_date = _format_date_only(report_date_raw or metadata.get("report_date"))
        period_start = _format_date_only(metadata.get("period_start"))
        period_end = _format_date_only(metadata.get("period_end"))
        if (not period_raw or ("-" not in period_raw and "–" not in period_raw)) and period_start and period_end:
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
            if "baninter" in self.client_logo_path.stem.lower():
                for col_idx in range(1, total_cols + 1):
                    header_value = dataframe.columns[col_idx - 1]
                    header_text = str(header_value).strip().lower()
                    if "fase/ciclo" in header_text or "tipo actividad" in header_text:
                        client_anchor_col = get_column_letter(col_idx)
                        break
                self._add_logo(
                    ws,
                    anchor=f"{client_anchor_col}1",
                    logo_path=self.client_logo_path,
                    max_width=175,
                    max_height=60,
                )
            else:
                self._add_logo(
                    ws,
                    anchor=f"{client_anchor_col}1",
                    logo_path=self.client_logo_path,
                    max_width=95,
                    max_height=28,
                )
        title_start_col = 2 if total_cols >= 2 else 1
        title_start_letter = get_column_letter(title_start_col)
        ws.merge_cells(f"{title_start_letter}1:{end_col_letter}1")
        title_cell = ws.cell(row=1, column=title_start_col, value="INFORME ACTIVIDADES OUTSOURCING BUSINESS IT")
        title_cell.font = Font(name="Calibri", size=18, bold=True, color=COLOR_LIME)
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
                safe_value = self._excel_safe_value(value)
                cell = ws.cell(row=r_idx, column=c_idx, value=safe_value)
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

        # Fila total (suma de Horas)
        data_start_row = table_header_row + 1
        data_end_row = table_header_row + len(dataframe)
        if data_end_row >= data_start_row and hour_col_indices:
            total_row = data_end_row + 1
            label_cell = ws.cell(row=total_row, column=1, value="TOTAL HORAS")
            label_cell.font = Font(name="Calibri", size=10, bold=True, color=COLOR_BLACK)
            label_cell.alignment = LEFT_ALIGNMENT
            label_cell.border = THIN_BORDER

            for c_idx in range(2, ws.max_column + 1):
                cell = ws.cell(row=total_row, column=c_idx)
                cell.border = THIN_BORDER

            for hour_col in sorted(hour_col_indices):
                col_letter = get_column_letter(hour_col)
                total_cell = ws.cell(
                    row=total_row,
                    column=hour_col,
                    value=f"=SUM({col_letter}{data_start_row}:{col_letter}{data_end_row})",
                )
                total_cell.font = Font(name="Calibri", size=10, bold=True, color=COLOR_BLACK)
                total_cell.alignment = RIGHT_ALIGNMENT
                total_cell.number_format = "0.0"
                total_cell.border = THIN_BORDER

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
        def _is_blank(value: object) -> bool:
            if value is None:
                return True
            try:
                if pd.isna(value):
                    return True
            except Exception:
                pass
            return isinstance(value, str) and value.strip() == ""

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
                    return raw_text
            return ""

        report_date_raw = _raw_from_metadata(["fecha del informe", "fecha informe"])
        periodo_raw = _raw_from_metadata(["periodo informe", "periodo"])

        # NOVA: mismo criterio que BANINTER (logo + titulo en una sola fila)
        total_cols_nova = max(5, len(metrics.dataframe.columns))
        end_col_letter_nova = get_column_letter(total_cols_nova)
        self._add_logo(ws, anchor="A1", max_width=200, max_height=66)
        if self.client_logo_path:
            if not "nova" in self.client_logo_path.stem.lower():
                client_anchor_col = get_column_letter(max(6, total_cols_nova - 1))
                self._add_logo(
                    ws,
                    anchor=f"{client_anchor_col}1",
                    logo_path=self.client_logo_path,
                    max_width=140 if ("baninter" in self.client_logo_path.stem.lower()) else 95,
                    max_height=48 if ("baninter" in self.client_logo_path.stem.lower()) else 28,
                )
            else:
                self._add_logo(
                    ws,
                    anchor=f"{end_col_letter_nova}1",
                    logo_path=self.client_logo_path,
                    max_width=140,
                    max_height=48,
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
            ws["B2"] = _format_date(report_date_raw)
        elif report_date:
            ws["B2"] = _format_date(report_date)
        elif period_end:
            ws["B2"] = _format_date(period_end)
        else:
            ws["B2"] = ""
        ws["A3"] = "Tema del Informe:"
        ws["B3"] = "Informe de Actividades"
        ws["A4"] = "Periodo Informe:"
        if periodo_raw and ("-" in periodo_raw or "–" in periodo_raw):
            ws["B4"] = periodo_raw
        elif period_start and period_end:
            ws["B4"] = f"{_format_date(period_start)} - {_format_date(period_end)}"
        else:
            ws["B4"] = periodo_raw or ""
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
                safe_value = self._excel_safe_value(value)
                cell = ws.cell(row=r_idx, column=c_idx, value=safe_value)
                cell.border = THIN_BORDER

                # Header de tabla
                if r_idx == 9:
                    cell.font = TABLE_HEADER_FONT
                    cell.fill = TABLE_HEADER_FILL
                    cell.alignment = CENTER_ALIGNMENT
                    if not _is_blank(value) and "fecha" in str(value).lower():
                        date_col_indices.add(c_idx)
                    if not _is_blank(value) and "hora" in str(value).lower():
                        hour_col_indices.add(c_idx)
                else:
                    if c_idx in date_col_indices and not _is_blank(value):
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

                    if c_idx in hour_col_indices and not _is_blank(value):
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
        # Fila TOTAL (solo NOVA/CD): sumar horas numericas
        # ---------------------------------------------------------
        total_row = None
        hour_col_idx = None
        for col_idx in range(1, ws.max_column + 1):
            header_value = ws.cell(row=9, column=col_idx).value
            if header_value and "hora" in str(header_value).lower():
                hour_col_idx = col_idx
                break

        if hour_col_idx is not None:
            total_row = 9 + len(metrics.dataframe) + 1
            ws.cell(row=total_row, column=1, value="TOTAL")
            ws.cell(row=total_row, column=1).font = Font(name="Calibri", size=11, bold=True)

            start_cell = f"{get_column_letter(hour_col_idx)}10"
            end_cell = f"{get_column_letter(hour_col_idx)}{total_row - 1}"
            total_cell = ws.cell(row=total_row, column=hour_col_idx)
            total_cell.value = f"=SUM({start_cell}:{end_cell})"
            total_cell.number_format = "0.0"
            total_cell.font = Font(name="Calibri", size=11, bold=True)
            total_cell.alignment = RIGHT_ALIGNMENT

        # ---------------------------------------------------------
        # Footer (formato Alfredo Aguirre)
        # ---------------------------------------------------------
        table_header_row = 9
        first_detail_row = table_header_row + 1
        last_detail_row = table_header_row + len(metrics.dataframe)
        last_data_row = total_row or last_detail_row

        # Footer oficial NOVA (formato Alfredo Aguirre) para todos los consultores
        start_row = max(last_data_row + 2, 41)
        self.buildFooter(
            ws=ws,
            startRow=start_row,
            resourceName=metrics.nombre,
            approverName="Wilmer Jaramillo",
            approverTitle="Subgerente Regional de Tecnología",
            sharepointPath=r"\\NOVA\\Tecnología - Documentos\\IT\\Desarrollo\\Documentación",
            firstDetailRow=first_detail_row,
            lastDetailRow=last_detail_row,
        )

    def buildFooter(
        self,
        ws: Worksheet,
        startRow: int,
        resourceName: str,
        approverName: str,
        approverTitle: str,
        sharepointPath: str,
        firstDetailRow: int,
        lastDetailRow: int,
    ) -> None:
        """Construye el pie con formato Alfredo Aguirre."""
        header_row = max(1, firstDetailRow - 1)
        tipo_col = None
        horas_col = None
        for col_idx in range(1, ws.max_column + 1):
            header_value = ws.cell(row=header_row, column=col_idx).value
            if not header_value:
                continue
            header_text = str(header_value).strip().lower()
            if "tipo hora" in header_text:
                tipo_col = col_idx
            elif "horas" in header_text or header_text == "hora":
                if "tipo" not in header_text:
                    horas_col = col_idx

        tipo_letter = get_column_letter(tipo_col) if tipo_col else None
        horas_letter = get_column_letter(horas_col) if horas_col else None

        def _sumif(tipo: str) -> str:
            if not tipo_letter or not horas_letter:
                return ""
            tipo_range = f"{tipo_letter}{firstDetailRow}:{tipo_letter}{lastDetailRow}"
            horas_range = f"{horas_letter}{firstDetailRow}:{horas_letter}{lastDetailRow}"
            return f'=SUMIF({tipo_range},"{tipo}",{horas_range})'

        bold_font = Font(name="Calibri", size=10, bold=True, color=COLOR_BLACK)
        normal_font = Font(name="Calibri", size=10, bold=False, color=COLOR_BLACK)
        center_wrap = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)
        gray_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

        r_total_1 = startRow
        r_total_2 = startRow + 1
        r_total_3 = startRow + 2
        r_legend = startRow + 4
        r_repo = startRow + 6
        r_sig_header = startRow + 8
        r_sig_space = startRow + 9
        r_sig_name = startRow + 10
        r_sig_title = startRow + 11

        ws.merge_cells(f"H{r_total_1}:K{r_total_1}")
        ws.merge_cells(f"H{r_total_2}:K{r_total_2}")
        ws.merge_cells(f"H{r_total_3}:K{r_total_3}")

        ws[f"H{r_total_1}"].value = "Total Horas Normales"
        ws[f"H{r_total_2}"].value = "Total Horas Extras entre semana"
        ws[f"H{r_total_3}"].value = "Total Horas Extras fin de semana o feriado"

        if "Resumen" in ws.parent.sheetnames:
            ws[f"L{r_total_1}"].value = (
                '=IFERROR(INDEX(Resumen!$I:$I,MATCH($B$6,Resumen!$B:$B,0)),"")'
            )
        else:
            ws[f"L{r_total_1}"].value = _sumif("HN")

        ws[f"L{r_total_2}"].value = _sumif("HS")
        ws[f"L{r_total_3}"].value = _sumif("HF")

        for r in (r_total_1, r_total_2, r_total_3):
            ws[f"H{r}"].font = bold_font
            ws[f"H{r}"].alignment = left_wrap
            ws[f"L{r}"].font = bold_font
            ws[f"L{r}"].alignment = center_wrap

        ws.merge_cells(f"A{r_legend}:L{r_legend}")
        ws[f"A{r_legend}"].value = (
            "Tipo Hora - HN: hora normal / HS: hora extra entre semana / "
            "HF: hora extra fin de semana o feriado"
        )
        ws[f"A{r_legend}"].font = bold_font
        ws[f"A{r_legend}"].alignment = center_wrap
        ws.row_dimensions[r_legend].height = 13

        ws.merge_cells(f"A{r_repo}:L{r_repo}")
        ws[f"A{r_repo}"].value = (
            "Repositorio Base Sharepoint de DocumentaciónEntregada:\n"
            f"{sharepointPath}"
        )
        ws[f"A{r_repo}"].font = bold_font
        ws[f"A{r_repo}"].alignment = center_wrap
        ws.row_dimensions[r_repo].height = 26

        ws.merge_cells(f"A{r_sig_header}:F{r_sig_header}")
        ws.merge_cells(f"G{r_sig_header}:L{r_sig_header}")
        ws[f"A{r_sig_header}"].value = "Elaborado por:"
        ws[f"G{r_sig_header}"].value = "Aprobado por:"
        for cell in (ws[f"A{r_sig_header}"], ws[f"G{r_sig_header}"]):
            cell.font = bold_font
            cell.alignment = center_wrap
            cell.fill = gray_fill

        ws.merge_cells(f"A{r_sig_space}:F{r_sig_space}")
        ws.merge_cells(f"G{r_sig_space}:L{r_sig_space}")
        ws.row_dimensions[r_sig_space].height = 49.5

        ws.merge_cells(f"A{r_sig_name}:F{r_sig_name}")
        ws.merge_cells(f"G{r_sig_name}:L{r_sig_name}")
        ws[f"A{r_sig_name}"].value = resourceName
        ws[f"G{r_sig_name}"].value = approverName
        ws[f"A{r_sig_name}"].font = normal_font
        ws[f"G{r_sig_name}"].font = normal_font
        ws[f"A{r_sig_name}"].alignment = center_wrap
        ws[f"G{r_sig_name}"].alignment = center_wrap

        ws.merge_cells(f"A{r_sig_title}:F{r_sig_title}")
        ws.merge_cells(f"G{r_sig_title}:L{r_sig_title}")
        ws[f"A{r_sig_title}"].value = "Cargo Recurso"
        ws[f"G{r_sig_title}"].value = approverTitle
        ws[f"A{r_sig_title}"].font = normal_font
        ws[f"G{r_sig_title}"].font = normal_font
        ws[f"A{r_sig_title}"].alignment = center_wrap
        ws[f"G{r_sig_title}"].alignment = center_wrap

        for r in range(r_total_1, r_sig_title + 1):
            for c in range(1, 13):
                ws.cell(row=r, column=c).border = THIN_BORDER

    @staticmethod
    def _detect_footer_format(footer_block: Optional[Dict[str, object]]) -> str:
        """Detecta el formato de footer basado en textos del archivo original."""
        if not footer_block:
            return "alfredo"
        cells = footer_block.get("cells") or []
        texts = []
        for cell in cells:
            value = cell.get("value")
            if value is None:
                continue
            texts.append(str(value).strip().lower())
        joined = " | ".join(texts)
        if "total horas normales" in joined or "tipo hora" in joined or "repositorio base sharepoint" in joined:
            return "alfredo"
        if "elaborado por" in joined and "aprobado por" in joined:
            return "simple"
        return "alfredo"

    @staticmethod
    def _apply_footer_block(
        ws: Worksheet,
        footer_block: Dict[str, object],
        last_data_row: int,
    ) -> None:
        """Aplica el footer original capturado desde el Excel fuente."""
        try:
            original_data_end = int(footer_block.get("data_end_row", 0))
            original_footer_start = int(footer_block.get("start_row", original_data_end + 1))
            original_footer_end = int(footer_block.get("max_row", original_footer_start))
            new_footer_start = last_data_row + 2
            offset = new_footer_start - original_footer_start

            for original_row, height in (footer_block.get("row_heights") or {}).items():
                new_row = original_row + offset
                ws.row_dimensions[new_row].height = height

            for cell_info in footer_block.get("cells", []):
                new_row = cell_info["row"] + offset
                col = cell_info["col"]
                cell = ws.cell(row=new_row, column=col, value=cell_info.get("value"))
                cell.font = cell_info.get("font")
                cell.fill = cell_info.get("fill")
                cell.border = cell_info.get("border")
                cell.alignment = cell_info.get("alignment")
                cell.number_format = cell_info.get("number_format") or cell.number_format

            for min_row, min_col, max_row, max_col in footer_block.get("merges", []):
                try:
                    ws.merge_cells(
                        start_row=min_row + offset,
                        start_column=min_col,
                        end_row=max_row + offset,
                        end_column=max_col,
                    )
                except Exception as merge_exc:
                    logger.warning("No se pudo mergear footer cells: %s", merge_exc)
        except Exception as exc:
            logger.warning("No se pudo aplicar footer original: %s", exc)
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

    # -------------------------------------------------------------
    # Post-procesamiento: ocultar filas vacias sin tocar footer
    # -------------------------------------------------------------
    def postprocess_hide_empty_table_rows_preserve_footer(
        self, wb: Workbook, sheet_df_map: Dict[str, pd.DataFrame]
    ) -> None:
        def norm(text: object) -> str:
            return str(text or "").replace("\u200b", "").replace("\xa0", " ").strip().lower()

        def strip_invisible(text: str) -> str:
            return text.replace("\u200b", "").replace("\xa0", " ").strip()

        def detect_table_start_row(ws: Worksheet) -> Optional[int]:
            best_row = None
            best_score = -1
            for row in range(1, min(35, ws.max_row) + 1):
                values = [norm(cell.value) for cell in ws[row] if norm(cell.value)]
                if not values:
                    continue
                has_fecha = any("fecha" in v for v in values)
                has_act = any("actividad" in v or "tarea" in v for v in values)
                has_horas_or_proy = any("hora" in v or "proyecto" in v for v in values)
                score = sum(
                    1
                    for t in ("fecha", "proyecto", "horas", "actividad", "tareas")
                    if any(t in v for v in values)
                )
                if has_fecha and has_act and has_horas_or_proy:
                    return row
                if score > best_score and score >= 2:
                    best_score = score
                    best_row = row
            return best_row

        def detect_footer_row(ws: Worksheet, start_row: int) -> Optional[int]:
            for row in range(start_row + 1, ws.max_row + 1):
                val = norm(ws.cell(row=row, column=1).value)
                if val == "elaborado por:":
                    return row
            return None

        def detect_lock_row(ws: Worksheet, start_row: int, footer_row: int, scan_cols: int) -> int:
            keywords = [
                "total horas normales",
                "total horas extras",
                "tipo hora - hn",
                "repositorio base sharepoint",
            ]
            for row in range(start_row + 1, footer_row):
                for col in range(1, scan_cols + 1):
                    text = norm(ws.cell(row=row, column=col).value)
                    if not text:
                        continue
                    for kw in keywords:
                        if kw in text:
                            return row
            return footer_row

        def formula_returns_empty(formula: str) -> bool:
            if '""' not in formula:
                return False
            cleaned = formula.replace('""', "")
            return not re.search(r'"[^"]+"', cleaned)

        def is_effectively_empty(cell) -> bool:
            value = cell.value
            if value is None:
                return True
            if isinstance(value, str):
                stripped = strip_invisible(value)
                if stripped == "":
                    return True
                if cell.data_type == "f" or stripped.startswith("="):
                    cleaned = re.sub(r"\s+", "", stripped)
                    if cleaned == '=""' or formula_returns_empty(cleaned):
                        return True
                return False
            if cell.data_type == "f":
                if value is None:
                    return True
            return False

        def is_total_formula(cell) -> bool:
            value = cell.value
            if value is None:
                return False
            text = value if isinstance(value, str) else ""
            if not text and cell.data_type == "f":
                text = str(value)
            if not text:
                return False
            upper = text.upper().replace(" ", "")
            return "SUM(" in upper or "SUMIF(" in upper or "SUBTOTAL(" in upper

        def is_day_only(value: object) -> bool:
            if value is None:
                return False
            if isinstance(value, (date, datetime)):
                return False
            if isinstance(value, (int, float)):
                try:
                    return 1 <= int(value) <= 31
                except Exception:
                    return False
            if isinstance(value, str):
                raw = strip_invisible(value)
                if raw.isdigit():
                    try:
                        num = int(raw)
                        return 1 <= num <= 31
                    except Exception:
                        return False
                if "/" in raw or "-" in raw:
                    return False
                try:
                    num = int(float(raw))
                    return 1 <= num <= 31
                except Exception:
                    return False
            return False

        for ws in wb.worksheets:
            if "resumen" in ws.title.lower():
                continue
            try:
                table_start_row = detect_table_start_row(ws)
                if not table_start_row:
                    logger.info("hide_empty: %s sin header detectado, omitido", ws.title)
                    continue

                footer_row = detect_footer_row(ws, table_start_row)
                if not footer_row:
                    logger.info("hide_empty: %s sin footer detectado, omitido", ws.title)
                    continue

                # Determinar última columna con header no vacío
                table_max_col = 0
                for cell in ws[table_start_row]:
                    if norm(cell.value):
                        table_max_col = max(table_max_col, cell.column)
                if table_max_col == 0:
                    logger.info("hide_empty: %s header vacío, omitido", ws.title)
                    continue

                # Determinar columnas clave
                header_values = [
                    norm(ws.cell(row=table_start_row, column=c).value)
                    for c in range(1, table_max_col + 1)
                ]
                col_fecha = next((i for i, v in enumerate(header_values, start=1) if "fecha" in v), None)
                col_actividad = next(
                    (i for i, v in enumerate(header_values, start=1) if "actividad" in v or "tarea" in v or "tareas" in v),
                    None,
                )
                col_horas = next((i for i, v in enumerate(header_values, start=1) if "hora" in v), None)

                if not col_fecha or not col_actividad or not col_horas:
                    logger.info(
                        "hide_empty: %s sin col_fecha/col_actividad/col_horas, omitido",
                        ws.title,
                    )
                    continue

                scan_cols = max(table_max_col, 12)
                lock_row = detect_lock_row(ws, table_start_row, footer_row, scan_cols)
                rows_in_df = len(sheet_df_map.get(ws.title, []))

                # Snapshot footer para validacion
                footer_max_row = min(lock_row + 120, ws.max_row)
                footer_max_col = max(table_max_col, 12)
                footer_cells: Dict[Tuple[int, int], Tuple[object, str, object, object, object, object]] = {}
                footer_rows_meta: Dict[int, Tuple[Optional[float], Optional[bool]]] = {}
                for r in range(lock_row, footer_max_row + 1):
                    rd = ws.row_dimensions.get(r)
                    footer_rows_meta[r] = (
                        rd.height if rd else None,
                        rd.hidden if rd else None,
                    )
                    for c in range(1, footer_max_col + 1):
                        cell = ws.cell(row=r, column=c)
                        footer_cells[(r, c)] = (
                            cell.value,
                            cell.number_format,
                            copy(cell.font),
                            copy(cell.fill),
                            copy(cell.border),
                            copy(cell.alignment),
                        )
                footer_merges = {
                    str(mr)
                    for mr in ws.merged_cells.ranges
                    if not (mr.max_row < lock_row or mr.min_row > footer_max_row)
                }

                hidden_rows: List[int] = []
                protected_rows: List[int] = []
                for r in range(table_start_row + 1, lock_row):
                    horas_cell = ws.cell(row=r, column=col_horas)
                    if is_total_formula(horas_cell):
                        protected_rows.append(r)
                        continue

                    fecha_empty = is_effectively_empty(ws.cell(row=r, column=col_fecha))
                    act_empty = is_effectively_empty(ws.cell(row=r, column=col_actividad))
                    horas_empty = is_effectively_empty(horas_cell)

                    if fecha_empty and act_empty and horas_empty:
                        ws.row_dimensions[r].hidden = True
                        ws.row_dimensions[r].height = 1
                        for c in range(1, table_max_col + 1):
                            cell = ws.cell(row=r, column=c)
                            if is_effectively_empty(cell):
                                cell.border = Border()
                                cell.fill = PatternFill()
                                cell.font = Font()
                                cell.alignment = Alignment()
                                cell.number_format = "General"
                        hidden_rows.append(r)

                # Validar footer intacto
                footer_ok = True
                for r in range(lock_row, footer_max_row + 1):
                    rd = ws.row_dimensions.get(r)
                    current_meta = (
                        rd.height if rd else None,
                        rd.hidden if rd else None,
                    )
                    if footer_rows_meta.get(r) != current_meta:
                        footer_ok = False
                        break
                    for c in range(1, footer_max_col + 1):
                        cell = ws.cell(row=r, column=c)
                        snapshot = footer_cells.get((r, c))
                        current = (
                            cell.value,
                            cell.number_format,
                            cell.font,
                            cell.fill,
                            cell.border,
                            cell.alignment,
                        )
                        if snapshot is None or current != snapshot:
                            footer_ok = False
                            break
                    if not footer_ok:
                        break
                current_merges = {
                    str(mr)
                    for mr in ws.merged_cells.ranges
                    if not (mr.max_row < lock_row or mr.min_row > footer_max_row)
                }
                if current_merges != footer_merges:
                    footer_ok = False

                logger.info(
                    "hide_empty: %s table_start=%s lock_row=%s footer_row=%s max_col=%s col_fecha=%s col_actividad=%s col_horas=%s rows_in_df=%s protected=%s hidden=%s protected_validation=%s",
                    ws.title,
                    table_start_row,
                    lock_row,
                    footer_row,
                    table_max_col,
                    col_fecha,
                    col_actividad,
                    col_horas,
                    rows_in_df,
                    protected_rows if len(protected_rows) <= 50 else f"{len(protected_rows)} rows",
                    hidden_rows if len(hidden_rows) <= 50 else f"{len(hidden_rows)} rows",
                    "OK" if footer_ok else "FAIL",
                )

                if not footer_ok:
                    raise RuntimeError(f"Footer modificado en hoja {ws.title}")
            except Exception as exc:
                logger.error("hide_empty: error en hoja %s: %s", ws.title, exc)
                raise

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
            self.cliente = "BIT Nova - TI"
