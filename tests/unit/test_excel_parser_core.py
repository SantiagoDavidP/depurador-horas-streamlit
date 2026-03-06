from io import BytesIO

import pandas as pd
import pytest
from openpyxl import Workbook

from backend.infrastructure.parsing import excel_sheet_parser as parser


@pytest.mark.unit
def test_parse_date_from_text_supports_common_formats():
    assert parser._parse_date_from_text("2025-01-15") == "2025-01-15"
    assert parser._parse_date_from_text("15/01/2025") == "2025-01-15"
    assert parser._parse_date_from_text("15-01-2025") == "2025-01-15"


@pytest.mark.unit
def test_extract_metadata_rows_detects_period_company_and_employee():
    df = pd.DataFrame(
        [
            ["INFORME ACTIVIDADES", None],
            ["Fecha del Informe:", "2025-09-01"],
            ["Periodo Informe:", "01/09/2025 - 30/09/2025"],
            ["Empresa:", "Business IT"],
            ["Consultor:", "Victor Jaramillo"],
        ]
    )
    metadata = parser._extract_metadata_rows(df)
    assert metadata["period_start"] == "2025-09-01"
    assert metadata["period_end"] == "2025-09-30"
    assert metadata["company"] == "Business IT"
    assert metadata["employee"] == "Victor Jaramillo"


@pytest.mark.unit
def test_correct_period_from_data_prioritizes_data_over_header():
    df = pd.DataFrame(
        {
            "Fecha": ["01/09/2025", "05/09/2025", "30/09/2025"],
            "Horas": [8, 8, 8],
        }
    )
    metadata = {
        "period_start": "2024-08-01",
        "period_end": "2024-08-31",
        "month_name": "August",
        "year": 2024,
    }
    corrected = parser.correct_period_from_data(df, metadata, date_column="Fecha")
    assert corrected["period_start"] == "2025-09-01"
    assert corrected["period_end"] == "2025-09-30"
    assert corrected["year"] == 2025
    assert corrected["period_source"] == "data_corrected"


@pytest.mark.unit
def test_infer_column_mapping_prefers_profile_mapping():
    df = pd.DataFrame(
        columns=["Fecha", "Horas", "Actividad", "Proyecto, Requerimiento"]
    )
    profile_mapping = {
        "date": "Fecha",
        "hours": "Horas",
        "description": "Actividad",
        "project": "Proyecto, Requerimiento",
    }
    mapping = parser.infer_column_mapping(df, profile_mapping)
    assert mapping is not None
    assert mapping.date == "Fecha"
    assert mapping.hours == "Horas"
    assert mapping.description == "Actividad"
    assert mapping.project == "Proyecto, Requerimiento"


@pytest.mark.unit
def test_select_best_sheet_prefers_timesheet_content():
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Hoja1"
    ws1.append(["solo", "texto"])
    ws1.append(["sin", "estructura"])

    ws2 = wb.create_sheet("Detalle")
    ws2.append(["Fecha", "Horas", "Actividad", "Proyecto"])
    ws2.append(["2025-01-01", 8, "Trabajo detallado", "Proyecto A"])
    ws2.append(["2025-01-02", 8, "Trabajo detallado 2", "Proyecto A"])

    buffer = BytesIO()
    wb.save(buffer)
    selected = parser.select_best_sheet(buffer.getvalue())
    assert selected == "Detalle"
