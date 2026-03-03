import pandas as pd

from backend.application.processing.baninter_processor import (
    BANINTER_PHASE_COLUMN,
    prepare_baninter_dataframe,
)
from backend.domain.models import ColumnMapping


def test_baninter_schema_drops_extra_columns():
    df = pd.DataFrame(
        {
            "Fecha": ["2025-09-01", "2025-09-02"],
            "Proyecto": ["Proyecto A", "Proyecto A"],
            "Tareas": ["Actividad 1", "Actividad 2"],
            "Horas": [4, 4],
            "Ticket": ["TK-1", "TK-2"],
            "Cliente": ["Cliente X", "Cliente X"],
            "Tecnologia": ["Tech", "Tech"],
            BANINTER_PHASE_COLUMN: ["Fase 1", ""],
        }
    )

    mapping = ColumnMapping(
        date="Fecha",
        hours="Horas",
        description="Tareas",
        project="Proyecto",
    )

    out_df, report = prepare_baninter_dataframe(df, mapping)

    assert list(out_df.columns) == [
        "Fecha",
        "Proyecto",
        "Actividad",
        "Horas",
        BANINTER_PHASE_COLUMN,
    ]
    assert "Ticket" not in out_df.columns
    assert "Cliente" not in out_df.columns
    assert "Tecnologia" not in out_df.columns
    assert report.get("missing_optional_columns") == []


def test_baninter_schema_keeps_id_and_reports_missing_phase():
    df = pd.DataFrame(
        {
            "Fecha": ["2025-09-01", "2025-09-02"],
            "Proyecto": ["Proyecto B", "Proyecto B"],
            "Actividad": ["Actividad 1", "Actividad 2"],
            "Horas": [6, 2],
            "ID": [101, 102],
            "Cliente": ["Cliente X", "Cliente X"],
        }
    )

    mapping = ColumnMapping(
        date="Fecha",
        hours="Horas",
        description="Actividad",
        project="Proyecto",
    )

    out_df, report = prepare_baninter_dataframe(df, mapping)

    assert list(out_df.columns) == [
        "Fecha",
        "Proyecto",
        "ID",
        "Actividad",
        "Horas",
    ]
    assert "Cliente" not in out_df.columns
    assert BANINTER_PHASE_COLUMN in report.get("missing_optional_columns", [])
