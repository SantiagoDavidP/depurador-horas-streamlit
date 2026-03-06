from io import BytesIO

import pytest
from openpyxl import Workbook

from backend.application.batch.batch_processor import BatchFileRequest, BatchProcessor
from backend.domain.models import ColumnMapping
from backend.infrastructure.composition.processing_factory import build_timesheet_processor
from backend.infrastructure.parsing.excel_sheet_parser_adapter import ExcelSheetParserAdapter


@pytest.fixture
def sample_excel_bytes():
    wb = Workbook()
    ws = wb.active
    ws.title = "Hoja1"
    ws.append(["Fecha", "Horas", "Descripcion", "Proyecto"])
    ws.append(["2025-01-13", 8.0, "Desarrollo feature X", "Proyecto A"])
    ws.append(["2025-01-14", 8.0, "Code review modulo", "Proyecto A"])
    ws.append(["2025-01-15", 8.0, "Testing modulo Y", "Proyecto A"])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


@pytest.mark.unit
def test_unit_successful_batch_processing(sample_excel_bytes):
    processor = build_timesheet_processor()
    batch_processor = BatchProcessor(processor, sheet_parser=ExcelSheetParserAdapter())
    mapping = ColumnMapping(
        date="Fecha",
        hours="Horas",
        description="Descripcion",
        project="Proyecto",
    )
    files = [
        BatchFileRequest(
            file_name="archivo1.xlsx",
            file_bytes=sample_excel_bytes,
            mapping=mapping,
            processor_kwargs={"correct_spelling": False},
        )
    ]

    results = batch_processor.process_batch(files)

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].result is not None
    assert results[0].result.summary.quality_score >= 0


@pytest.mark.unit
def test_unit_batch_with_invalid_file_returns_error():
    processor = build_timesheet_processor()
    batch_processor = BatchProcessor(processor, sheet_parser=ExcelSheetParserAdapter())
    mapping = ColumnMapping(
        date="Fecha",
        hours="Horas",
        description="Descripcion",
    )
    files = [
        BatchFileRequest(
            file_name="invalid.xlsx",
            file_bytes=b"invalid excel data",
            mapping=mapping,
            processor_kwargs={"correct_spelling": False},
        )
    ]

    results = batch_processor.process_batch(files)
    assert len(results) == 1
    assert results[0].success is False
    assert results[0].error
