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

from backend.domain.rates.collaborator_rates import get_collaborator_rates_manager

from .models import ConsultorMetrics, ConsolidatedReport
from .styles import *

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None  # type: ignore

logger = logging.getLogger(__name__)



class IndividualBusinessMixin:
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
