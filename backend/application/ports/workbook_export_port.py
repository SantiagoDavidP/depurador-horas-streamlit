from __future__ import annotations

from typing import Optional, Protocol

from backend.application.processing.models import ProcessorSummary
from backend.application.tabular.table_data import TableData


class WorkbookExportPort(Protocol):
    def export_workbook(
        self,
        corrected_df: TableData,
        errors_df: TableData,
        summary: ProcessorSummary,
        *,
        debug_hours_df: Optional[TableData] = None,
        debug_detail_df: Optional[TableData] = None,
    ) -> bytes:
        ...
