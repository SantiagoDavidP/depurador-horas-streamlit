from __future__ import annotations

import io
import logging
import re
from copy import copy
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from openpyxl import Workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.drawing.image import Image
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.utils import get_column_letter, column_index_from_string
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.worksheet import Worksheet

from .models import ConsultorMetrics, ConsolidatedReport
from .styles import *
from backend.shared.tabular.pandas_mapper import to_pandas_table

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None  # type: ignore

logger = logging.getLogger(__name__)



class IndividualNovaMixin:
    def _create_individual_sheet_nova(
        self, ws: Worksheet, metrics: ConsultorMetrics
    ) -> None:
        """Hoja individual NOVA (layout con metadata + tabla)."""
        dataframe = to_pandas_table(metrics.dataframe)

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
        total_cols_nova = max(5, len(dataframe.columns))
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
            dataframe_to_rows(dataframe, index=False, header=True), start=9
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
            total_row = 9 + len(dataframe) + 1
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
        last_detail_row = table_header_row + len(dataframe)
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
