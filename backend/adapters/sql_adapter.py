"""
SQL Data Source Adapter for Microsoft Fabric SQL Endpoint

Connects to Microsoft Fabric Data Warehouse and loads timesheet data
into ParsedSheet format for processing pipeline compatibility.
"""

import logging
import os
import re
from typing import Optional, Dict, Any

import pandas as pd
import pyodbc

from backend.adapters import DataSourceAdapter, DataSourceConfig
from backend.application.parsing.models import ParsedSheet
from backend.shared.tabular.pandas_mapper import from_pandas_table

logger = logging.getLogger(__name__)


class FabricSQLAdapter(DataSourceAdapter):
    """
    Adapter for Microsoft Fabric SQL Endpoint / Data Warehouse.

    Supports both Azure AD authentication and SQL Server authentication.
    Loads data from SQL and transforms it into ParsedSheet format.

    Environment Variables:
        FABRIC_SQL_SERVER: Server endpoint (e.g., workspace.datawarehouse.fabric.microsoft.com)
        FABRIC_SQL_DATABASE: Database name
        FABRIC_SQL_AUTH_METHOD: Authentication method ('managed_identity', 'service_principal', 'azure_ad_user', 'sql_auth')

        # For Managed Identity (recommended for production):
        FABRIC_SQL_AUTH_METHOD=managed_identity

        # For Service Principal:
        FABRIC_SQL_AUTH_METHOD=service_principal
        AZURE_CLIENT_ID: Application (client) ID
        AZURE_CLIENT_SECRET: Client secret
        AZURE_TENANT_ID: Directory (tenant) ID

        # For Azure AD User (development only):
        FABRIC_SQL_AUTH_METHOD=azure_ad_user

        # For SQL Server Authentication (legacy):
        FABRIC_SQL_AUTH_METHOD=sql_auth
        FABRIC_SQL_USERNAME: SQL username
        FABRIC_SQL_PASSWORD: SQL password

        # Legacy support:
        FABRIC_SQL_USE_AZURE_AD=true|false

        FABRIC_SQL_TABLE: Table name (default: Timesheets)
    """

    def __init__(self, config: DataSourceConfig):
        super().__init__(config)

        # Load configuration from environment
        self.server = os.getenv("FABRIC_SQL_SERVER")
        self.database = os.getenv("FABRIC_SQL_DATABASE")
        self.table_name = os.getenv("FABRIC_SQL_TABLE", "Timesheets")
        self.custom_query = config.query
        self.additional_params = config.additional_params or {}
        self.connection: Optional[pyodbc.Connection] = None

        auth_method = os.getenv("FABRIC_SQL_AUTH_METHOD")
        if auth_method:
            self.auth_method = auth_method.lower()
        else:
            legacy_use_azure_ad = os.getenv("FABRIC_SQL_USE_AZURE_AD")
            if legacy_use_azure_ad is not None:
                use_azure_ad = legacy_use_azure_ad.lower() == "true"
                self.auth_method = "azure_ad_user" if use_azure_ad else "sql_auth"
            else:
                self.auth_method = "managed_identity"

        # Auth-specific credentials
        self.username = os.getenv("FABRIC_SQL_USERNAME")
        self.password = os.getenv("FABRIC_SQL_PASSWORD")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.tenant_id = os.getenv("AZURE_TENANT_ID")

        # Validate required configuration
        if not self.server:
            raise ValueError("FABRIC_SQL_SERVER environment variable is required")
        if not self.database:
            raise ValueError("FABRIC_SQL_DATABASE environment variable is required")

        valid_methods = {"managed_identity", "service_principal", "azure_ad_user", "sql_auth"}
        if self.auth_method not in valid_methods:
            raise ValueError(
                f"Invalid auth_method: {self.auth_method}. "
                "Valid options: managed_identity, service_principal, azure_ad_user, sql_auth"
            )

        if self.auth_method == "sql_auth" and (not self.username or not self.password):
            raise ValueError(
                "USERNAME and PASSWORD required when using sql_auth authentication "
                "(FABRIC_SQL_USERNAME/FABRIC_SQL_PASSWORD)"
            )

        if self.auth_method == "service_principal":
            if not self.client_id or not self.client_secret or not self.tenant_id:
                raise ValueError(
                    "AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID required "
                    "when using service_principal authentication"
                )

    def _build_connection_string(self) -> str:
        """Build connection string based on auth method."""
        driver = os.getenv("FABRIC_SQL_DRIVER", "ODBC Driver 18 for SQL Server")
        base_conn = (
            f"Driver={{{driver}}};"
            f"Server={self.server};"
            f"Database={self.database};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
        )

        if self.auth_method == "managed_identity":
            # Managed Identity (best for Azure production)
            logger.info("Using Managed Identity authentication")
            conn_str = base_conn + "Authentication=ActiveDirectoryMsi;"
            if self.client_id:
                conn_str += f"UID={self.client_id};"

        elif self.auth_method == "service_principal":
            # Service Principal with Client ID/Secret
            logger.info("Using Service Principal authentication")
            conn_str = (
                base_conn
                + "Authentication=ActiveDirectoryServicePrincipal;"
                + f"UID={self.client_id};"
                + f"PWD={self.client_secret};"
            )
            if self.tenant_id:
                conn_str += f"Authority Id={self.tenant_id};"

        elif self.auth_method == "azure_ad_user":
            # Azure AD User (interactive or integrated)
            logger.info("Using Azure AD User authentication")
            conn_str = base_conn + "Authentication=ActiveDirectoryIntegrated;"

        else:  # sql_auth
            # SQL Server authentication (legacy)
            logger.info("Using SQL Server authentication")
            conn_str = (
                base_conn
                + f"UID={self.username};"
                + f"PWD={self.password};"
            )

        return conn_str

    def _get_connection(self) -> pyodbc.Connection:
        """Get or create database connection."""
        if self.connection is None or not self._is_connection_alive():
            try:
                conn_str = self._build_connection_string()
                logger.info(f"Connecting to Fabric SQL: {self.server}/{self.database}")
                self.connection = pyodbc.connect(conn_str, timeout=30)
                logger.info("Successfully connected to Fabric SQL")
            except pyodbc.Error as e:
                logger.error(f"Failed to connect to Fabric SQL: {e}", exc_info=True)
                raise ConnectionError(f"Database connection failed: {e}") from e

        return self.connection

    def _is_connection_alive(self) -> bool:
        """Check if connection is still active."""
        if self.connection is None:
            return False
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception:
            return False

    def _build_query(self) -> str:
        """
        Build SQL query to fetch timesheet data.

        Returns query that selects all necessary columns.
        Customize column names based on your Fabric SQL schema.
        """
        if self.custom_query:
            return self.custom_query

        # Default query aligned to Registro_Actividades_HorasExtras schema.
        query = f"""
            SELECT
                Fecha,
                Horas,
                Descripcion_Actividad AS Actividad,
                Proyecto,
                Colaborador,
                Email,
                Cliente,
                Tipo_Hora,
                Tipo_Registro,
                SubArea,
                Area_Solicitante,
                Numero_Ticket,
                Descripcion_Requerimiento,
                Tipo_Actividad,
                Ruta_Soportes,
                Equipos,
                Colaborador AS employee_name,
                Cliente AS company_name,
                MIN(Fecha) OVER() AS period_start,
                MAX(Fecha) OVER() AS period_end
            FROM {self.table_name}
        """

        # Add filters from additional_params
        filters = []

        if "employee_id" in self.additional_params:
            employee_value = str(self.additional_params["employee_id"]).replace("'", "''")
            filters.append(f"(Colaborador = '{employee_value}' OR Email = '{employee_value}')")

        period_month = self.additional_params.get("period_month")
        period_year = self.additional_params.get("period_year")
        if period_month is not None and period_year is not None:
            try:
                month_value = int(period_month)
                year_value = int(period_year)
                if 1 <= month_value <= 12:
                    filters.append(f"YEAR(Fecha) = {year_value}")
                    filters.append(f"MONTH(Fecha) = {month_value}")
            except (TypeError, ValueError):
                logger.warning(
                    "Filtros de periodo invalidos: month=%s year=%s",
                    period_month,
                    period_year,
                )
        else:
            if "period_start" in self.additional_params:
                start_value = str(self.additional_params["period_start"]).replace("'", "''")
                filters.append(f"Fecha >= '{start_value}'")

            if "period_end" in self.additional_params:
                end_value = str(self.additional_params["period_end"]).replace("'", "''")
                filters.append(f"Fecha <= '{end_value}'")

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY Fecha, Colaborador"

        return query

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize SQL column names to match expected Excel format.

        IMPORTANT: Customize this mapping based on your SQL schema.

        Args:
            df: Raw DataFrame from SQL query

        Returns:
            DataFrame with normalized column names
        """
        # Column mapping: SQL_COLUMN -> EXPECTED_EXCEL_COLUMN
        # Las columnas ya vienen con los nombres correctos desde la query
        # Solo mapeamos si es necesario algún ajuste
        column_mapping = {}

        df_normalized = df.rename(columns=column_mapping)

        # Ensure required columns exist
        required_columns = ["Fecha", "Horas", "Actividad"]
        missing_columns = [col for col in required_columns if col not in df_normalized.columns]

        if missing_columns:
            raise ValueError(
                f"SQL data missing required columns: {missing_columns}. "
                f"Available columns: {list(df_normalized.columns)}"
            )

        return df_normalized

    def _extract_metadata(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Extract metadata from SQL data.

        Args:
            df: DataFrame with SQL data (must include metadata columns)

        Returns:
            Metadata dict with employee, company, period info
        """
        metadata = {}

        # Extract from first row or use defaults
        if len(df) > 0:
            metadata["employee"] = df["employee_name"].iloc[0] if "employee_name" in df.columns else "Unknown"
            metadata["company"] = df["company_name"].iloc[0] if "company_name" in df.columns else "Unknown"

            # Period dates
            if "period_start" in df.columns and pd.notna(df["period_start"].iloc[0]):
                metadata["period_start"] = pd.to_datetime(df["period_start"].iloc[0])
            else:
                metadata["period_start"] = df["Fecha"].min()

            if "period_end" in df.columns and pd.notna(df["period_end"].iloc[0]):
                metadata["period_end"] = pd.to_datetime(df["period_end"].iloc[0])
            else:
                metadata["period_end"] = df["Fecha"].max()

            # Month and year from period_start
            period_start = metadata.get("period_start")
            if period_start:
                metadata["month_name"] = period_start.strftime("%B")
                metadata["year"] = period_start.year
            else:
                metadata["month_name"] = ""
                metadata["year"] = 0
        else:
            # Empty dataset
            metadata = {
                "employee": "Unknown",
                "company": "Unknown",
                "period_start": None,
                "period_end": None,
                "month_name": "",
                "year": 0
            }

        return metadata

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and prepare DataFrame for processing pipeline.

        Args:
            df: Raw DataFrame from SQL

        Returns:
            Cleaned DataFrame
        """
        df = df.copy()

        # Convert Fecha to datetime
        if "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

        # Convert Horas to float, handling HH:MM and decimal strings.
        if "Horas" in df.columns:
            def _parse_hours_value(value: object) -> Optional[float]:
                if pd.isna(value):
                    return None
                text = str(value).strip()
                if not text:
                    return None
                if ":" in text:
                    parts = text.split(":")
                    if 2 <= len(parts) <= 3:
                        try:
                            hours = int(parts[0])
                            minutes = int(parts[1])
                            seconds = int(parts[2]) if len(parts) == 3 else 0
                            return hours + (minutes / 60.0) + (seconds / 3600.0)
                        except ValueError:
                            pass
                cleaned = text.replace(",", ".")
                cleaned = re.sub(r"[^\d.\-]", "", cleaned)
                if cleaned in {"", "-", ".", "-."}:
                    return None
                try:
                    return float(cleaned)
                except ValueError:
                    return None

            df["Horas"] = df["Horas"].apply(_parse_hours_value)

        # Strip whitespace from string columns
        string_columns = df.select_dtypes(include=["object"]).columns
        for col in string_columns:
            df[col] = df[col].astype(str).str.strip()

        # Drop metadata columns (not needed in main DataFrame)
        metadata_columns = ["employee_name", "company_name", "period_start", "period_end"]
        df = df.drop(columns=[col for col in metadata_columns if col in df.columns], errors="ignore")

        return df

    def load(self) -> ParsedSheet:
        """
        Load data from Fabric SQL and return ParsedSheet.

        Returns:
            ParsedSheet: Data formatted for processing pipeline

        Raises:
            ConnectionError: If database connection fails
            ValueError: If data is invalid or missing required columns
        """
        try:
            # Get connection and execute query
            conn = self._get_connection()
            query = self._build_query()

            logger.info("Executing SQL query to load timesheet data")
            logger.debug(f"Query: {query}")

            df_raw = pd.read_sql(query, conn)

            logger.info(f"Loaded {len(df_raw)} rows from Fabric SQL")
            logger.info(f"Columnas recibidas de SQL: {list(df_raw.columns)}")
            logger.info(f"Primeras 3 filas de Horas: {df_raw['Horas'].head(3).tolist() if 'Horas' in df_raw.columns else 'NO EXISTE COLUMNA'}")
            logger.info(f"Tipo de dato de Horas: {df_raw['Horas'].dtype if 'Horas' in df_raw.columns else 'N/A'}")

            if df_raw.empty:
                logger.warning("SQL query returned no data")
                raise ValueError("No data found in SQL database for given parameters")

            # Extract metadata before cleaning
            metadata = self._extract_metadata(df_raw)

            # Normalize and clean
            df_normalized = self._normalize_columns(df_raw)
            logger.info(f"Columnas después de normalizar: {list(df_normalized.columns)}")
            logger.info(f"Primeras 3 filas de Horas después de normalizar: {df_normalized['Horas'].head(3).tolist() if 'Horas' in df_normalized.columns else 'NO EXISTE'}")
            
            df_clean = self._clean_dataframe(df_normalized)
            logger.info(f"Primeras 3 filas de Horas después de limpiar: {df_clean['Horas'].head(3).tolist() if 'Horas' in df_clean.columns else 'NO EXISTE'}")
            logger.info(f"Tipo de dato de Horas después de limpiar: {df_clean['Horas'].dtype if 'Horas' in df_clean.columns else 'N/A'}")

            # Add original_row_numbers for error traceability
            df_clean = self._simulate_row_numbers(df_clean, offset=2)

            # Create ParsedSheet
            parsed_sheet = ParsedSheet(
                dataframe=from_pandas_table(df_clean),
                header_row=1,  # Simulated header row
                row_offset=2,  # Simulated data start row
                sheet_name="SQL_Data",  # Virtual sheet name
                metadata=metadata
            )

            logger.info(
                "Successfully created ParsedSheet from SQL: "
                f"{len(parsed_sheet.dataframe)} rows, "
                f"employee='{metadata.get('employee')}', "
                f"period={metadata.get('period_start')} to {metadata.get('period_end')}"
            )

            return parsed_sheet

        except pyodbc.Error as e:
            logger.error(f"SQL query failed: {e}", exc_info=True)
            raise ConnectionError(f"Failed to load data from SQL: {e}") from e
        except Exception as e:
            logger.error(f"Failed to create ParsedSheet from SQL data: {e}", exc_info=True)
            raise ValueError(f"Error processing SQL data: {e}") from e

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            bool: True if connection successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            logger.info("SQL connection test successful")
            return True
        except Exception as e:
            logger.error(f"SQL connection test failed: {e}")
            return False

    def close(self):
        """Close database connection."""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Closed SQL connection")
            except Exception:
                pass
            finally:
                self.connection = None

    def __del__(self):
        """Cleanup connection on object destruction."""
        self.close()
