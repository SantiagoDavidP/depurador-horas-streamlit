from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from api import serializers, services
from backend.domain.models import ColumnMapping
from backend.domain.profiles.client_profiles import ClientProfile
from backend.domain.parsing.excel_parser import ParsedSheet


def _profile_bit() -> ClientProfile:
    return ClientProfile(
        client_id="cliente_bit",
        name="NOVA - TI",
        mapping={"date": "Fecha", "hours": "Horas", "description": "Actividad", "project": "Proyecto"},
        settings={},
        keywords=["nova", "bit"],
        company_aliases=["nova", "business it"],
    )


def test_build_mapping_and_baninter_helpers():
    mapping = services.build_mapping_from_values(
        {"date": "Fecha", "hours": "Horas", "description": "Actividad", "project": "Proyecto"}
    )
    assert isinstance(mapping, ColumnMapping)
    assert mapping.project == "Proyecto"

    no_mapping = services.build_mapping_from_values({"date": "", "hours": "Horas", "description": "Actividad"})
    assert no_mapping is None

    assert services.is_baninter_result("Resumen Actividades Recursos.xlsx", {}, None) is True
    assert services.is_baninter_result("otro.xlsx", {"company": "Banco Internacional"}, None) is True
    assert services.is_baninter_result("otro.xlsx", {}, "cliente_talent") is True


def test_detect_area_and_profile_detection(monkeypatch):
    class _Collab:
        def __init__(self, cargo):
            self.cargo = cargo

    class _Manager:
        def find_collaborator(self, name):
            return _Collab("Analista") if "cd" in name.lower() else _Collab(None)

    monkeypatch.setattr(services, "get_collaborator_rates_manager", lambda: _Manager())
    assert services.detect_area_from_names(["persona_cd", "otra"]) == "TI"

    profile = _profile_bit()
    parsed = ParsedSheet(
        dataframe=pd.DataFrame(columns=["Fecha", "Horas", "Actividad", "Proyecto"]),
        header_row=0,
        row_offset=1,
        sheet_name="Sheet1",
        metadata={"company": "NOVA Ecuador"},
    )
    detected = services.auto_detect_profile_from_parsed(parsed, {"cliente_bit": profile})
    assert detected == "cliente_bit"


def test_auto_detect_profile_from_files_and_filename_helpers(monkeypatch):
    profile = _profile_bit()
    parsed = ParsedSheet(
        dataframe=pd.DataFrame({"Fecha": ["2026-01-01"], "Horas": [8], "Actividad": ["Task"], "Proyecto": ["P"]}),
        header_row=0,
        row_offset=1,
        sheet_name="Sheet1",
        metadata={"company": "NOVA", "employee": "Luis Avila", "month_name": "January", "year": 2026},
    )
    monkeypatch.setattr(services, "load_multiple_sheets", lambda *_args, **_kwargs: [parsed])
    monkeypatch.setattr(services, "detect_profile_basic", lambda *_args, **_kwargs: None)

    profile_id, metadata = services.auto_detect_profile_from_files(b"xlsx", "sample.xlsx", [profile])
    assert profile_id == "cliente_bit"
    assert metadata.get("company") == "NOVA"

    @dataclass
    class _Result:
        success: bool
        client_id: str
        metadata: dict

    name = services.infer_client_name_from_results([_Result(True, "cliente_bit", {})], {"cliente_bit": profile})
    assert name == "NOVA - TI"

    default_output = services.build_default_output_filename(
        "NOVA - TI",
        [_Result(True, "cliente_bit", {"month_name": "January", "year": 2026})],
    )
    assert "Consolidado_NOVA_-_TI_January_2026.xlsx" == default_output

    employee = services.resolve_employee({"employee": "Ana Perez"}, "ana.xlsx")
    assert employee["final"] == "Ana Perez"


def test_serializers_core_paths(monkeypatch):
    payload = serializers.sanitize_payload(
        {
            "n": np.int64(5),
            "dt": pd.Timestamp("2026-01-01"),
            "list": [datetime(2026, 1, 1), {"x": np.float64(1.5)}],
        }
    )
    assert payload["n"] == 5
    assert "2026-01-01" in payload["dt"]
    assert isinstance(payload["list"], list)

    errors_df = pd.DataFrame(
        [
            {"tipo_error": "descripcion_repetida", "detalle": "w"},
            {"tipo_error": "fecha_invalida", "detalle": "c"},
        ]
    )
    sorted_df = serializers.sort_errors_dataframe(errors_df)
    assert sorted_df.iloc[0]["tipo_error"] == "fecha_invalida"

    records = serializers.dataframe_to_records(pd.DataFrame([{"a": 1, "b": np.nan}]))
    assert records[0]["b"] == ""

    @dataclass
    class _HolidayInfo:
        month: int
        year: int
        month_name: str
        holidays: list
        source: str

    monkeypatch.setattr(
        serializers._holiday_detector,
        "detect_month_holidays",
        lambda *_args, **_kwargs: _HolidayInfo(
            month=1,
            year=2026,
            month_name="January",
            holidays=[{"date": "2026-01-01", "name": "Año Nuevo"}],
            source="column",
        ),
    )
    holiday = serializers.build_holiday_info(
        pd.DataFrame({"Fecha": ["2026-01-01"]}),
        "Fecha",
        metadata={},
    )
    assert holiday["month"] == 1
    assert "January" in holiday["month_label"]
