"""
Adapter Factory for Data Source Selection

Creates appropriate adapter instances based on configuration.
"""

import logging
import os
from typing import Optional

from backend.adapters import DataSourceAdapter, DataSourceConfig
from backend.adapters.excel_adapter import ExcelAdapter
from backend.adapters.sql_adapter import FabricSQLAdapter

logger = logging.getLogger(__name__)


def create_adapter(
    source_type: Optional[str] = None,
    file_path: Optional[str] = None,
    query: Optional[str] = None,
    **additional_params
) -> DataSourceAdapter:
    """
    Factory function to create appropriate data source adapter.
    
    Args:
        source_type: Type of data source ("excel" or "sql"). 
                     If None, reads from DATA_SOURCE_TYPE env var (default: "excel")
        file_path: Path to Excel file (required for Excel adapter)
        query: Custom SQL query (optional for SQL adapter)
        **additional_params: Additional parameters passed to adapter
    
    Returns:
        DataSourceAdapter: Instance of appropriate adapter
        
    Raises:
        ValueError: If source_type is invalid or required params missing
        
    Examples:
        # Excel source
        adapter = create_adapter(source_type="excel", file_path="data.xlsx")
        
        # SQL source with environment variables
        adapter = create_adapter(source_type="sql")
        
        # SQL source with custom query
        adapter = create_adapter(
            source_type="sql",
            query="SELECT * FROM Timesheets WHERE employee_id = 'E001'"
        )
    """
    # Determine source type from parameter or environment
    if source_type is None:
        source_type = os.getenv("DATA_SOURCE_TYPE", "excel").lower()
    else:
        source_type = source_type.lower()
    
    logger.info(f"Creating adapter for source_type: {source_type}")
    
    # Create configuration
    config = DataSourceConfig(
        source_type=source_type,
        file_path=file_path,
        query=query,
        additional_params=additional_params
    )
    
    # Select and instantiate adapter
    if source_type == "excel":
        if not file_path:
            raise ValueError("Excel adapter requires file_path parameter")
        return ExcelAdapter(config)
    
    elif source_type == "sql":
        return FabricSQLAdapter(config)
    
    else:
        raise ValueError(
            f"Unknown source_type: '{source_type}'. "
            f"Valid options: 'excel', 'sql'"
        )
