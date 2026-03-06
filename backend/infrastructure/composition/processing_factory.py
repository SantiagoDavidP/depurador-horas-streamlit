from __future__ import annotations

from typing import Optional

from backend.application.ports.blob_storage_port import BlobStoragePort
from backend.application.ports.llm_corrector_port import LLMCorrectorPort
from backend.application.ports.workbook_export_port import WorkbookExportPort
from backend.application.processing.service import TimeSheetProcessor
from backend.domain.roles.role_validator import RoleActivityValidator
from backend.infrastructure.ai.llm_corrector import LLMCorrector
from backend.infrastructure.ai.llm_corrector_adapter import LLMCorrectorAdapter
from backend.infrastructure.config.role_taxonomy_loader import load_role_validator
from backend.infrastructure.export.excel_workbook_exporter import ExcelWorkbookExporter


def build_timesheet_processor(
    *,
    expected_hours_per_day: float = 8.0,
    llm_corrector: Optional[LLMCorrectorPort] = None,
    blob_storage: Optional[BlobStoragePort] = None,
    workbook_exporter: Optional[WorkbookExportPort] = None,
    role_validator: Optional[RoleActivityValidator] = None,
) -> TimeSheetProcessor:
    resolved_llm_corrector = llm_corrector or LLMCorrectorAdapter(LLMCorrector(batch_size=20))
    resolved_role_validator = role_validator or load_role_validator()
    resolved_workbook_exporter = workbook_exporter or ExcelWorkbookExporter()
    return TimeSheetProcessor(
        expected_hours_per_day=expected_hours_per_day,
        llm_corrector=resolved_llm_corrector,
        blob_storage=blob_storage,
        workbook_exporter=resolved_workbook_exporter,
        role_validator=resolved_role_validator,
    )
