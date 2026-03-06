"""
Excel Data Source Adapter

Thin wrapper around existing load_sheet_with_header() function to maintain
100% backward compatibility with the current Excel processing pipeline.
"""

import logging
from pathlib import Path
from typing import Optional

from backend.adapters import DataSourceAdapter, DataSourceConfig
from backend.application.parsing.models import ParsedSheet
from backend.infrastructure.parsing.excel_sheet_parser import load_sheet_with_header

logger = logging.getLogger(__name__)


class ExcelAdapter(DataSourceAdapter):
    """
    Adapter for Excel files (.xlsx, .xls).
    
    This adapter wraps the existing load_sheet_with_header() function
    without modification to ensure zero breaking changes.
    """
    
    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        
        if not config.file_path:
            raise ValueError("Excel adapter requires file_path in config")
        
        self.file_path = Path(config.file_path)
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.file_path}")
        
        if self.file_path.suffix.lower() not in ['.xlsx', '.xls']:
            raise ValueError(f"Invalid Excel file extension: {self.file_path.suffix}")
    
    def load(self) -> ParsedSheet:
        """
        Load Excel file using existing load_sheet_with_header() function.
        
        Returns:
            ParsedSheet: Parsed data with metadata
            
        Raises:
            ValueError: If Excel file cannot be parsed
        """
        try:
            logger.info(f"Loading Excel file: {self.file_path}")
            
            # Use existing function - no changes to core logic
            parsed_sheet = load_sheet_with_header(self.file_path.read_bytes())
            
            logger.info(
                f"Successfully loaded Excel: {len(parsed_sheet.dataframe)} rows, "
                f"sheet='{parsed_sheet.sheet_name}', header_row={parsed_sheet.header_row}"
            )
            
            return parsed_sheet
            
        except Exception as e:
            logger.error(f"Failed to load Excel file: {e}", exc_info=True)
            raise ValueError(f"Error loading Excel file: {e}") from e
    
    def test_connection(self) -> bool:
        """
        Test if Excel file is accessible and readable.
        
        Returns:
            bool: True if file exists and is readable
        """
        try:
            return self.file_path.exists() and self.file_path.is_file()
        except Exception as e:
            logger.warning(f"Connection test failed for {self.file_path}: {e}")
            return False
