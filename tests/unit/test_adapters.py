"""
Unit tests for data source adapters.

Tests the adapter factory, Excel adapter, and SQL adapter functionality.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from backend.adapters import DataSourceConfig
from backend.adapters.adapter_factory import create_adapter
from backend.adapters.excel_adapter import ExcelAdapter
from backend.adapters.sql_adapter import FabricSQLAdapter
from backend.domain.parsing.excel_parser import ParsedSheet


# ============================================================================
# Adapter Factory Tests
# ============================================================================

def test_create_adapter_excel(tmp_path):
    """Test creating Excel adapter from factory."""
    test_file = tmp_path / "test.xlsx"
    test_file.touch()
    adapter = create_adapter(source_type="excel", file_path=str(test_file))
    assert isinstance(adapter, ExcelAdapter)


def test_create_adapter_sql():
    """Test creating SQL adapter from factory."""
    with patch.dict("os.environ", {
        "FABRIC_SQL_SERVER": "test.server.com",
        "FABRIC_SQL_DATABASE": "TestDB",
        "FABRIC_SQL_USE_AZURE_AD": "true"
    }):
        adapter = create_adapter(source_type="sql")
        assert isinstance(adapter, FabricSQLAdapter)


def test_create_adapter_invalid_type():
    """Test factory with invalid source type."""
    with pytest.raises(ValueError, match="Unknown source_type"):
        create_adapter(source_type="invalid")


def test_create_adapter_excel_without_filepath():
    """Test Excel adapter requires file_path."""
    with pytest.raises(ValueError, match="requires file_path"):
        create_adapter(source_type="excel")


def test_create_adapter_from_env_var():
    """Test factory reads DATA_SOURCE_TYPE from environment."""
    with patch.dict("os.environ", {"DATA_SOURCE_TYPE": "excel"}):
        # Should not raise - uses env var
        with pytest.raises(ValueError, match="requires file_path"):
            create_adapter(file_path=None)


# ============================================================================
# Excel Adapter Tests
# ============================================================================

def test_excel_adapter_invalid_extension(tmp_path):
    """Test Excel adapter rejects invalid file extensions."""
    test_file = tmp_path / "test.txt"
    test_file.touch()
    config = DataSourceConfig(source_type="excel", file_path=str(test_file))
    
    with pytest.raises(ValueError, match="Invalid Excel file extension"):
        ExcelAdapter(config)


def test_excel_adapter_file_not_found():
    """Test Excel adapter handles missing files."""
    config = DataSourceConfig(source_type="excel", file_path="nonexistent.xlsx")
    
    with pytest.raises(FileNotFoundError):
        ExcelAdapter(config)


def test_excel_adapter_test_connection(tmp_path):
    """Test Excel adapter connection test."""
    # Create a temporary Excel file
    test_file = tmp_path / "test.xlsx"
    test_file.touch()
    
    config = DataSourceConfig(source_type="excel", file_path=str(test_file))
    adapter = ExcelAdapter(config)
    
    assert adapter.test_connection() is True


def test_excel_adapter_load(tmp_path):
    """Test Excel adapter loads data correctly."""
    # Create a simple Excel file
    test_file = tmp_path / "test.xlsx"
    df = pd.DataFrame({
        "Fecha": [datetime(2024, 1, 1)],
        "Horas": [8.0],
        "Actividad": ["Test task"]
    })
    df.to_excel(test_file, index=False)
    
    config = DataSourceConfig(source_type="excel", file_path=str(test_file))
    adapter = ExcelAdapter(config)
    
    # Mock load_sheet_with_header to return test data
    with patch("backend.adapters.excel_adapter.load_sheet_with_header") as mock_load:
        mock_parsed = ParsedSheet(
            dataframe=df,
            header_row=0,
            row_offset=1,
            sheet_name="Sheet1",
            metadata={"employee": "Test Employee"}
        )
        mock_load.return_value = mock_parsed
        
        result = adapter.load()
        
        assert isinstance(result, ParsedSheet)
        assert len(result.dataframe) == 1
        mock_load.assert_called_once()


# ============================================================================
# SQL Adapter Tests
# ============================================================================

def test_sql_adapter_missing_server():
    """Test SQL adapter requires server configuration."""
    config = DataSourceConfig(source_type="sql")
    
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="FABRIC_SQL_SERVER"):
            FabricSQLAdapter(config)


def test_sql_adapter_missing_database():
    """Test SQL adapter requires database configuration."""
    config = DataSourceConfig(source_type="sql")
    
    with patch.dict("os.environ", {"FABRIC_SQL_SERVER": "test.server.com"}, clear=True):
        with pytest.raises(ValueError, match="FABRIC_SQL_DATABASE"):
            FabricSQLAdapter(config)


def test_sql_adapter_missing_credentials():
    """Test SQL adapter requires credentials when not using Azure AD."""
    config = DataSourceConfig(source_type="sql")
    
    with patch.dict("os.environ", {
        "FABRIC_SQL_SERVER": "test.server.com",
        "FABRIC_SQL_DATABASE": "TestDB",
        "FABRIC_SQL_USE_AZURE_AD": "false"
    }, clear=True):
        with pytest.raises(ValueError, match="USERNAME and PASSWORD required"):
            FabricSQLAdapter(config)


def test_sql_adapter_build_connection_string_azure_ad():
    """Test SQL adapter builds correct connection string for Azure AD."""
    config = DataSourceConfig(source_type="sql")
    
    with patch.dict("os.environ", {
        "FABRIC_SQL_SERVER": "test.server.com",
        "FABRIC_SQL_DATABASE": "TestDB",
        "FABRIC_SQL_USE_AZURE_AD": "true"
    }):
        adapter = FabricSQLAdapter(config)
        conn_str = adapter._build_connection_string()
        
        assert "Driver={ODBC Driver 18 for SQL Server}" in conn_str
        assert "Server=test.server.com" in conn_str
        assert "Database=TestDB" in conn_str
        assert "Authentication=ActiveDirectoryIntegrated" in conn_str


def test_sql_adapter_build_connection_string_sql_auth():
    """Test SQL adapter builds correct connection string for SQL auth."""
    config = DataSourceConfig(source_type="sql")
    
    with patch.dict("os.environ", {
        "FABRIC_SQL_SERVER": "test.server.com",
        "FABRIC_SQL_DATABASE": "TestDB",
        "FABRIC_SQL_USE_AZURE_AD": "false",
        "FABRIC_SQL_USERNAME": "testuser",
        "FABRIC_SQL_PASSWORD": "testpass"
    }):
        adapter = FabricSQLAdapter(config)
        conn_str = adapter._build_connection_string()
        
        assert "UID=testuser" in conn_str
        assert "PWD=testpass" in conn_str


@pytest.mark.requires_sql
def test_sql_adapter_test_connection_success():
    """Test SQL adapter connection test (requires actual SQL server)."""
    config = DataSourceConfig(source_type="sql")
    
    with patch.dict("os.environ", {
        "FABRIC_SQL_SERVER": "test.server.com",
        "FABRIC_SQL_DATABASE": "TestDB",
        "FABRIC_SQL_USE_AZURE_AD": "true"
    }):
        adapter = FabricSQLAdapter(config)
        
        # Mock pyodbc connection
        with patch("pyodbc.connect") as mock_connect:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            result = adapter.test_connection()
            
            assert result is True
            mock_cursor.execute.assert_called_once_with("SELECT 1")


@pytest.mark.requires_sql
def test_sql_adapter_load_success():
    """Test SQL adapter loads data correctly (requires SQL server)."""
    config = DataSourceConfig(source_type="sql")
    
    with patch.dict("os.environ", {
        "FABRIC_SQL_SERVER": "test.server.com",
        "FABRIC_SQL_DATABASE": "TestDB",
        "FABRIC_SQL_USE_AZURE_AD": "true"
    }):
        adapter = FabricSQLAdapter(config)
        
        # Mock SQL query result
        mock_df = pd.DataFrame({
            "Fecha": [datetime(2024, 1, 1)],
            "Horas": [8.0],
            "Actividad": ["Test task"],
            "Proyecto": ["Project A"],
            "role_column": ["Developer"],
            "employee_name": ["John Doe"],
            "company_name": ["Test Company"],
            "period_start": [datetime(2024, 1, 1)],
            "period_end": [datetime(2024, 1, 31)]
        })
        
        with patch("pyodbc.connect") as mock_connect, \
             patch("pandas.read_sql") as mock_read_sql:
            
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_read_sql.return_value = mock_df
            
            result = adapter.load()
            
            assert isinstance(result, ParsedSheet)
            assert len(result.dataframe) > 0
            assert "Fecha" in result.dataframe.columns
            assert "Horas" in result.dataframe.columns
            assert "Actividad" in result.dataframe.columns
            assert result.metadata["employee"] == "John Doe"
            assert result.metadata["company"] == "Test Company"


def test_sql_adapter_normalize_columns():
    """Test SQL adapter normalizes column names correctly."""
    config = DataSourceConfig(source_type="sql")
    
    with patch.dict("os.environ", {
        "FABRIC_SQL_SERVER": "test.server.com",
        "FABRIC_SQL_DATABASE": "TestDB",
        "FABRIC_SQL_USE_AZURE_AD": "true"
    }):
        adapter = FabricSQLAdapter(config)
        
        df = pd.DataFrame({
            "Fecha": [datetime(2024, 1, 1)],
            "Horas": [8.0],
            "Actividad": ["Test"],
            "Proyecto": ["ProjectA"]
        })
        
        normalized = adapter._normalize_columns(df)
        
        assert "Fecha" in normalized.columns
        assert "Horas" in normalized.columns
        assert "Actividad" in normalized.columns
        assert "Proyecto" in normalized.columns


def test_sql_adapter_normalize_columns_missing_required():
    """Test SQL adapter raises error for missing required columns."""
    config = DataSourceConfig(source_type="sql")
    
    with patch.dict("os.environ", {
        "FABRIC_SQL_SERVER": "test.server.com",
        "FABRIC_SQL_DATABASE": "TestDB",
        "FABRIC_SQL_USE_AZURE_AD": "true"
    }):
        adapter = FabricSQLAdapter(config)
        
        df = pd.DataFrame({
            "Fecha": [datetime(2024, 1, 1)],
            # Missing hours_column and description_column
        })
        
        with pytest.raises(ValueError, match="missing required columns"):
            adapter._normalize_columns(df)


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
def test_adapter_factory_integration():
    """Integration test: Factory creates correct adapter based on config."""
    # Test Excel
    with patch("backend.adapters.excel_adapter.Path.exists", return_value=True), \
         patch("backend.adapters.excel_adapter.Path.is_file", return_value=True):
        
        excel_adapter = create_adapter(source_type="excel", file_path="test.xlsx")
        assert isinstance(excel_adapter, ExcelAdapter)
    
    # Test SQL
    with patch.dict("os.environ", {
        "FABRIC_SQL_SERVER": "test.server.com",
        "FABRIC_SQL_DATABASE": "TestDB",
        "FABRIC_SQL_USE_AZURE_AD": "true"
    }):
        sql_adapter = create_adapter(source_type="sql")
        assert isinstance(sql_adapter, FabricSQLAdapter)
