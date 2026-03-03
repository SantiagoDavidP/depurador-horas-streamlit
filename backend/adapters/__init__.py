"""
Data Source Adapters for ProyectoStaffAumentado

This module provides a flexible adapter pattern for loading timesheet data from multiple sources
(Excel files, SQL databases, etc.) while maintaining compatibility with the existing processing pipeline.

All adapters must return ParsedSheet instances that conform to the expected data contract.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd
from backend.domain.parsing.excel_parser import ParsedSheet


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""
    source_type: str  # "excel" or "sql"
    file_path: Optional[str] = None  # For Excel
    connection_string: Optional[str] = None  # For SQL
    query: Optional[str] = None  # For SQL
    additional_params: Optional[Dict[str, Any]] = None  # Extra parameters


class DataSourceAdapter(ABC):
    """
    Abstract base class for data source adapters.
    
    All adapters must implement load() to return a ParsedSheet instance that is compatible
    with the existing processing pipeline.
    """
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
    
    @abstractmethod
    def load(self) -> ParsedSheet:
        """
        Load data from the source and return a ParsedSheet instance.
        
        Returns:
            ParsedSheet: Parsed data with metadata, ready for processing
            
        Raises:
            ValueError: If data cannot be loaded or is invalid
            ConnectionError: If connection to data source fails
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if the data source is accessible.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    def _build_metadata(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Build metadata dictionary from DataFrame or provided parameters.
        
        Args:
            df: DataFrame containing timesheet data
            **kwargs: Additional metadata parameters
            
        Returns:
            Dict with keys: employee, company, period_start, period_end, month_name, year
        """
        metadata = {
            "employee": kwargs.get("employee", "Unknown"),
            "company": kwargs.get("company", "Unknown"),
            "period_start": kwargs.get("period_start"),
            "period_end": kwargs.get("period_end"),
            "month_name": kwargs.get("month_name", ""),
            "year": kwargs.get("year", 0)
        }
        return metadata
    
    def _simulate_row_numbers(self, df: pd.DataFrame, offset: int = 2) -> pd.DataFrame:
        """
        Add original_row_numbers column to DataFrame for error traceability.
        
        Args:
            df: DataFrame to modify
            offset: Starting row number (default 2 to simulate Excel with header)
            
        Returns:
            DataFrame with original_row_numbers column
        """
        df = df.copy()
        df["original_row_numbers"] = range(offset, offset + len(df))
        return df
