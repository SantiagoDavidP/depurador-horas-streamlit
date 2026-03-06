from __future__ import annotations

import threading

from api.infrastructure.auth.azure_ad_user_auth_adapter import AzureADUserAuthAdapter
from api.infrastructure.storage.in_memory_file_store_adapter import InMemoryFileStoreAdapter
from backend.application.batch.batch_processor import BatchProcessor
from backend.application.processing.service import TimeSheetProcessor
from backend.infrastructure.composition.processing_factory import build_timesheet_processor
from backend.infrastructure.parsing.excel_sheet_parser_adapter import ExcelSheetParserAdapter
from backend.infrastructure.reporting.excel_timesheet_reporting_adapter import ExcelTimesheetReportingAdapter
from backend.infrastructure.storage.azure_blob_storage_adapter import AzureBlobStorageAdapter

blob_storage = AzureBlobStorageAdapter()
processor = build_timesheet_processor(blob_storage=blob_storage)
sheet_parser = ExcelSheetParserAdapter()
batch_processor = BatchProcessor(processor, sheet_parser=sheet_parser)
timesheet_reporting = ExcelTimesheetReportingAdapter()
_individual_processor_tls = threading.local()
auth_provider = AzureADUserAuthAdapter()
file_store = InMemoryFileStoreAdapter()


def get_individual_thread_processor() -> TimeSheetProcessor:
    thread_processor = getattr(_individual_processor_tls, "processor", None)
    if thread_processor is None:
        processor_kwargs = {
            "expected_hours_per_day": processor.expected_hours,
            "role_validator": processor.role_validator,
        }
        llm_corrector = getattr(processor, "llm_corrector", None)
        if llm_corrector is not None:
            processor_kwargs["llm_corrector"] = llm_corrector
        workbook_exporter = getattr(processor, "workbook_exporter", None)
        if workbook_exporter is not None:
            processor_kwargs["workbook_exporter"] = workbook_exporter
        blob_storage = getattr(processor, "blob_storage", None)
        if blob_storage is not None:
            processor_kwargs["blob_storage"] = blob_storage
        try:
            thread_processor = TimeSheetProcessor(**processor_kwargs)
        except TypeError:
            processor_kwargs.pop("blob_storage", None)
            processor_kwargs.pop("workbook_exporter", None)
            thread_processor = TimeSheetProcessor(**processor_kwargs)
        _individual_processor_tls.processor = thread_processor
    return thread_processor
