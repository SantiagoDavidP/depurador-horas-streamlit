"""Tests de integración para el procesamiento por lotes."""
import pytest
from io import BytesIO
import pandas as pd
from openpyxl import Workbook

from backend.batch_processor import BatchProcessor, BatchFileRequest
from backend.processor import TimeSheetProcessor, ColumnMapping


@pytest.fixture
def sample_excel_bytes():
    """Crea un archivo Excel de ejemplo en bytes."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Hoja1"
    
    # Headers
    ws.append(["Fecha", "Horas", "Descripción", "Proyecto"])
    
    # Data
    ws.append(["2025-01-13", 8.0, "Desarrollo feature X", "Proyecto A"])
    ws.append(["2025-01-14", 8.0, "Code review", "Proyecto A"])
    ws.append(["2025-01-15", 8.0, "Testing módulo Y", "Proyecto A"])
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


class TestBatchProcessor:
    """Tests de integración para BatchProcessor."""
    
    def test_successful_batch_processing(self, sample_excel_bytes):
        """Debe procesar múltiples archivos exitosamente."""
        processor = TimeSheetProcessor()
        batch_processor = BatchProcessor(processor)
        
        mapping = ColumnMapping(
            date="Fecha",
            hours="Horas",
            description="Descripción",
            project="Proyecto"
        )
        
        files = [
            BatchFileRequest(
                file_name="archivo1.xlsx",
                file_bytes=sample_excel_bytes,
                mapping=mapping
            )
        ]
        
        results = batch_processor.process_batch(files)
        
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result is not None
    
    def test_batch_with_invalid_file(self):
        """Debe manejar archivos inválidos sin fallar el batch completo."""
        processor = TimeSheetProcessor()
        batch_processor = BatchProcessor(processor)
        
        mapping = ColumnMapping(
            date="Fecha",
            hours="Horas",
            description="Descripción"
        )
        
        files = [
            BatchFileRequest(
                file_name="invalid.xlsx",
                file_bytes=b"invalid excel data",
                mapping=mapping
            )
        ]
        
        results = batch_processor.process_batch(files)
        
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error is not None
