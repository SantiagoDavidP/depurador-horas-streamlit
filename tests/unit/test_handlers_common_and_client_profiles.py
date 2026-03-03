import json

import pandas as pd

from api.presentation import handlers_common
from backend.application.batch.batch_processor import BatchFileResult
from backend.application.processing.models import ProcessorResult, ProcessorSummary
from backend.domain.models import ColumnMapping
from backend.domain.profiles.client_profiles import ClientProfile, ClientProfileManager


class _Store:
    def __init__(self):
        self.files = {}
        self.idx = 0

    def store_file(self, data: bytes, filename: str, content_type: str) -> str:
        self.idx += 1
        file_id = f"f{self.idx}"
        self.files[file_id] = (data, filename, content_type)
        return file_id


def _processor_result() -> ProcessorResult:
    summary = ProcessorSummary(
        total_registros=1,
        total_errores=0,
        horas_totales=8.0,
        dias_con_problemas_horas=0,
        errores_por_tipo={},
        quality_score=100.0,
    )
    return ProcessorResult(
        workbook_bytes=b"xlsx",
        output_filename="out.xlsx",
        validation_errors=[],
        corrections_log=[],
        summary=summary,
        corrected_dataframe=pd.DataFrame(
            {"Fecha": ["2026-01-01"], "Horas": [8], "Actividad": ["Actividad"], "Proyecto": ["P1"]}
        ),
        errors_dataframe=pd.DataFrame([{"fila": 2, "tipo_error": "descripcion_repetida", "detalle": "d"}]),
        metadata={"month_name": "January", "year": 2026},
    )


def test_handlers_common_serialize_and_zip(monkeypatch):
    store = _Store()
    monkeypatch.setattr(handlers_common, "file_store", store)

    result_ok = BatchFileResult(
        file_name="a.xlsx",
        success=True,
        result=_processor_result(),
        client_id="cliente_bit",
        metadata={"employee": "Ana", "company": "NOVA"},
    )
    mapping = ColumnMapping(date="Fecha", hours="Horas", description="Actividad", project="Proyecto")
    payload = handlers_common._serialize_result(result_ok, mapping=mapping, source_filename="a.xlsx")
    assert payload["success"] is True
    assert "download_id" in payload
    assert "summary" in payload and "quality_score" in payload["summary"]

    result_fail = BatchFileResult(file_name="b.xlsx", success=False, error="boom")
    payload_fail = handlers_common._serialize_result(result_fail, mapping=mapping, source_filename="b.xlsx")
    assert payload_fail["success"] is False
    assert payload_fail["error"] == "boom"

    monkeypatch.setattr(handlers_common, "is_baninter_result", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        handlers_common,
        "generate_individual_business_it_excel",
        lambda *_args, **_kwargs: (b"excel-baninter", "consultor.xlsx"),
    )
    zip_bytes = handlers_common._build_baninter_zip([result_ok, result_ok])
    assert isinstance(zip_bytes, (bytes, bytearray))
    assert len(zip_bytes) > 20

    assert handlers_common._infer_client_id_for_file("baninter.xlsx", {}, None) == "cliente_talent"
    assert handlers_common._infer_client_id_for_file("nova.xlsx", {}, None) == "cliente_bit"
    assert handlers_common._infer_client_id_for_file("x.xlsx", {}, "fallback") == "fallback"


def test_client_profile_manager_load_get_save(tmp_path):
    profiles_path = tmp_path / "profiles.json"
    data = {
        "cliente_demo": {
            "nombre": "Cliente Demo",
            "mapeo_columnas": {
                "date": "Fecha",
                "hours": "Horas",
                "description": "Actividad",
                "project": "Proyecto",
            },
            "configuraciones": {"horas_esperadas_dia": 8},
            "keywords": ["demo"],
            "company_aliases": ["cliente demo"],
        }
    }
    profiles_path.write_text(json.dumps(data), encoding="utf-8")

    manager = ClientProfileManager(profiles_path=profiles_path)
    loaded = manager.load_profiles()
    assert "cliente_demo" in loaded

    profile = manager.get_profile("cliente_demo")
    assert profile is not None
    mapping = manager.get_mapping("cliente_demo")
    assert mapping is not None
    assert mapping.description == "Actividad"

    all_profiles = manager.list_profiles()
    assert len(all_profiles) == 1

    new_profile = ClientProfile(
        client_id="cliente_new",
        name="Cliente New",
        mapping={"date": "F", "hours": "H", "description": "D"},
        settings={},
    )
    manager.save_profile(new_profile)
    reloaded = manager.load_profiles(force_reload=True)
    assert "cliente_new" in reloaded


def test_client_profile_manager_missing_and_invalid_json(tmp_path):
    missing_path = tmp_path / "missing.json"
    manager_missing = ClientProfileManager(profiles_path=missing_path)
    assert manager_missing.load_profiles() == {}

    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{bad json", encoding="utf-8")
    manager_bad = ClientProfileManager(profiles_path=bad_path)
    assert manager_bad.load_profiles() == {}
