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

from backend.collaborator_rates import get_collaborator_rates_manager

from .models import ConsultorMetrics, ConsolidatedReport
from .styles import *

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None  # type: ignore

logger = logging.getLogger(__name__)



class MetricsCleanupMixin:
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
