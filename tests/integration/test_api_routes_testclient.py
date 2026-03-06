import json
from dataclasses import dataclass

import pandas as pd
from fastapi.testclient import TestClient

from api.main import app
from api.presentation import handlers_batch, handlers_common, handlers_download
from api.presentation import handlers_individual_analyze, handlers_individual_process
from api.presentation.dependencies import auth_provider
from backend.application.parsing.models import ParsedSheet
from backend.application.batch.batch_processor import BatchFileResult
from backend.application.consolidation.models import ConsolidatedReport
from backend.application.processing.models import ProcessorResult, ProcessorSummary
from backend.domain.models import ColumnMapping
from backend.domain.profiles.client_profiles import ClientProfile


@dataclass
class _StoredBatch:
    results: list
    source: str = "batch"


class _MemoryFileStore:
    def __init__(self):
        self.files = {}
        self.batches = {}
        self._f = 0
        self._b = 0

    def store_file(self, data: bytes, filename: str, content_type: str) -> str:
        self._f += 1
        file_id = f"file-{self._f}"
        self.files[file_id] = {
            "filename": filename,
            "content_type": content_type,
            "data": data,
        }
        return file_id

    def get_file(self, file_id: str):
        stored = self.files.get(file_id)
        if not stored:
            return None
        return type("StoredFile", (), stored)

    def store_batch(self, results, source: str = "batch") -> str:
        self._b += 1
        batch_id = f"batch-{self._b}"
        self.batches[batch_id] = _StoredBatch(results=list(results), source=source)
        return batch_id

    def get_batch(self, batch_id: str):
        return self.batches.get(batch_id)


def _build_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Fecha": ["2026-01-02", "2026-01-03"],
            "Horas": [8.0, 2.0],
            "Actividad": ["Desarrollo backend", "Soporte QA"],
            "Proyecto": ["P1", "P1"],
        }
    )


def _build_processor_result() -> ProcessorResult:
    df = _build_df()
    summary = ProcessorSummary(
        total_registros=2,
        total_errores=1,
        horas_totales=10.0,
        dias_con_problemas_horas=0,
        errores_por_tipo={"warning": 1},
        errores_criticos=0,
        errores_advertencia=1,
        quality_score=95.0,
    )
    return ProcessorResult(
        workbook_bytes=b"excel-bytes",
        output_filename="resultado.xlsx",
        validation_errors=[],
        corrections_log=[],
        summary=summary,
        corrected_dataframe=df,
        errors_dataframe=pd.DataFrame(
            [{"fila": 2, "tipo_error": "descripcion_repetida", "detalle": "texto"}]
        ),
        metadata={"month_name": "January", "year": 2026, "employee": "Luis Avila", "company": "NOVA"},
    )


def _profile() -> ClientProfile:
    return ClientProfile(
        client_id="cliente_bit",
        name="NOVA - TI",
        mapping={
            "date": "Fecha",
            "hours": "Horas",
            "description": "Actividad",
            "project": "Proyecto",
        },
        settings={
            "correct_spelling": False,
            "duplicate_similarity_threshold": 90,
            "duplicate_min_occurrences": 3,
            "hours_tolerance_factor": 1.5,
            "rol_default": "Consultor",
        },
    )


def test_api_routes_batch_and_download_flow(monkeypatch):
    store = _MemoryFileStore()
    mapping = ColumnMapping(date="Fecha", hours="Horas", description="Actividad", project="Proyecto")

    monkeypatch.setattr(auth_provider, "require_user", lambda authorization=None: {"id": "u1"})
    monkeypatch.setattr(handlers_batch, "file_store", store)
    monkeypatch.setattr(handlers_common, "file_store", store)
    monkeypatch.setattr(handlers_download, "file_store", store)

    monkeypatch.setattr(handlers_batch, "auto_detect_profile_from_files", lambda *_: ("cliente_bit", {"company": "NOVA"}))
    monkeypatch.setattr(handlers_batch, "get_profile_catalog", lambda: {"cliente_bit": _profile()})
    monkeypatch.setattr(handlers_batch, "build_mapping_from_values", lambda values: mapping)
    monkeypatch.setattr(
        handlers_batch,
        "load_sheet_with_header",
        lambda *_args, **_kwargs: ParsedSheet(
            dataframe=_build_df(),
            header_row=0,
            row_offset=1,
            sheet_name="Sheet1",
            metadata={"employee": "Luis Avila", "company": "NOVA", "month_name": "January", "year": 2026},
        ),
    )
    monkeypatch.setattr(handlers_batch, "infer_column_mapping", lambda *_args, **_kwargs: mapping)
    monkeypatch.setattr(handlers_batch, "is_baninter_result", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(handlers_batch, "infer_client_name_from_results", lambda *_args, **_kwargs: "NOVA - TI")
    monkeypatch.setattr(handlers_batch, "detect_area_from_names", lambda *_args, **_kwargs: "TI")
    monkeypatch.setattr(
        handlers_batch.batch_processor,
        "process_batch",
        lambda requests, max_workers=4: [
            BatchFileResult(
                file_name=requests[0].file_name,
                success=True,
                result=_build_processor_result(),
                sheet_name="Sheet1",
                client_id="cliente_bit",
                metadata={"employee": "Luis Avila", "company": "NOVA", "month_name": "January", "year": 2026},
            )
        ],
    )

    monkeypatch.setattr(
        handlers_batch,
        "validate_batch_results_for_consolidation",
        lambda results: (True, ["ok"]),
    )
    monkeypatch.setattr(
        handlers_batch,
        "generate_consolidated_from_batch_results",
        lambda **_kwargs: ConsolidatedReport(
            workbook_bytes=b"consolidado-bytes",
            output_filename="Consolidado.xlsx",
            consultores_incluidos=1,
            total_facturar=100.0,
            total_horas=10.0,
            periodo="January 2026",
            dias_laborables=22,
        ),
    )
    monkeypatch.setattr(handlers_batch, "_build_baninter_zip", lambda *_args, **_kwargs: b"zip-bytes")

    client = TestClient(app)

    # /api/batch/analyze
    analyze_resp = client.post(
        "/api/batch/analyze",
        files=[("files", ("sample.xlsx", b"fake-xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
    )
    assert analyze_resp.status_code == 200
    analyze_json = analyze_resp.json()
    assert "auto_profile_id" in analyze_json
    assert "profile_mapping" in analyze_json

    # /api/batch/process
    payload = {
        "profileId": None,
        "mappingValues": {
            "date": "Fecha",
            "hours": "Horas",
            "description": "Actividad",
            "project": "Proyecto",
        },
        "settings": {"correctSpelling": False},
    }
    process_resp = client.post(
        "/api/batch/process",
        files=[("files", ("sample.xlsx", b"fake-xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        data={"payload": json.dumps(payload)},
    )
    assert process_resp.status_code == 200
    process_json = process_resp.json()
    assert "batch_id" in process_json
    assert "results" in process_json and process_json["results"]
    assert "summary" in process_json["results"][0]
    assert "quality_score" in process_json["results"][0]["summary"]

    batch_id = process_json["batch_id"]

    # /api/batch/consolidate
    consolidate_resp = client.post(
        "/api/batch/consolidate",
        json={"batchId": batch_id, "clientName": "NOVA - TI"},
    )
    assert consolidate_resp.status_code == 200
    consolidate_json = consolidate_resp.json()
    assert "download_id" in consolidate_json
    assert "filename" in consolidate_json

    # /api/download/{file_id}
    file_id = consolidate_json["download_id"]
    download_resp = client.get(f"/api/download/{file_id}")
    assert download_resp.status_code == 200
    assert len(download_resp.content) > 0

    # /api/batch/baninter-zip
    baninter_zip_resp = client.post(
        "/api/batch/baninter-zip",
        json={"batchId": batch_id},
    )
    assert baninter_zip_resp.status_code == 200
    baninter_zip_json = baninter_zip_resp.json()
    assert "download_id" in baninter_zip_json
    assert baninter_zip_json["filename"].endswith(".zip")

    zip_download = client.get(f"/api/download/{baninter_zip_json['download_id']}")
    assert zip_download.status_code == 200
    assert zip_download.content == b"zip-bytes"


def test_api_routes_individual_health_profile_me_and_download(monkeypatch):
    store = _MemoryFileStore()
    mapping = ColumnMapping(date="Fecha", hours="Horas", description="Actividad", project="Proyecto")
    profile = _profile()
    parsed_sheet = ParsedSheet(
        dataframe=_build_df(),
        header_row=0,
        row_offset=1,
        sheet_name="Luis Avila",
        metadata={"employee": "Luis Avila", "company": "NOVA", "month_name": "January", "year": 2026},
    )

    class _ProcessorStub:
        def process_parsed_sheet(self, **_kwargs):
            return _build_processor_result()

    monkeypatch.setattr(auth_provider, "require_user", lambda authorization=None: {"id": "u1", "name": "Tester"})
    monkeypatch.setattr(handlers_individual_analyze, "auth_provider", auth_provider)
    monkeypatch.setattr(handlers_individual_process, "auth_provider", auth_provider)

    monkeypatch.setattr(handlers_individual_analyze, "load_multiple_sheets", lambda *_: [parsed_sheet])
    monkeypatch.setattr(handlers_individual_analyze, "auto_detect_profile_from_files", lambda *_: ("cliente_bit", {}))
    monkeypatch.setattr(handlers_individual_analyze, "get_profile_catalog", lambda: {"cliente_bit": profile})
    monkeypatch.setattr(handlers_individual_analyze, "detect_area_from_names", lambda *_: "TI")

    monkeypatch.setattr(handlers_individual_process, "file_store", store)
    monkeypatch.setattr(handlers_common, "file_store", store)
    monkeypatch.setattr(handlers_download, "file_store", store)

    monkeypatch.setattr(handlers_individual_process, "load_multiple_sheets", lambda *_: [parsed_sheet])
    monkeypatch.setattr(handlers_individual_process, "get_profile_catalog", lambda: {"cliente_bit": profile})
    monkeypatch.setattr(handlers_individual_process, "infer_column_mapping", lambda *_args, **_kwargs: mapping)
    monkeypatch.setattr(handlers_individual_process, "processor", _ProcessorStub())
    monkeypatch.setattr(handlers_individual_process, "get_individual_thread_processor", lambda: _ProcessorStub())
    monkeypatch.setattr(handlers_individual_process, "is_baninter_result", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(handlers_individual_process, "_build_baninter_zip", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        handlers_individual_process,
        "generate_consolidated_from_batch_results",
        lambda **_kwargs: ConsolidatedReport(
            workbook_bytes=b"consolidado-individual",
            output_filename="Consolidado_Individual.xlsx",
            consultores_incluidos=1,
            total_facturar=80.0,
            total_horas=10.0,
            periodo="January 2026",
            dias_laborables=22,
        ),
    )

    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    profiles = client.get("/api/profiles")
    assert profiles.status_code == 200
    assert "profiles" in profiles.json()

    me = client.get("/api/me")
    assert me.status_code == 200
    assert "user" in me.json()

    analyze_ind = client.post(
        "/api/individual/analyze",
        files={"file": ("individual.xlsx", b"fake", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert analyze_ind.status_code == 200
    analyze_json = analyze_ind.json()
    assert "sheets" in analyze_json
    assert "auto_profile_id" in analyze_json

    process_payload = {"profileId": "cliente_bit", "settings": {"correctSpelling": False}, "maxWorkers": 1}
    process_ind = client.post(
        "/api/individual/process",
        files={"file": ("individual.xlsx", b"fake", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"payload": json.dumps(process_payload)},
    )
    assert process_ind.status_code == 200
    process_json = process_ind.json()
    assert "batch_id" in process_json
    assert "results" in process_json and process_json["results"]
    assert "summary" in process_json["results"][0]
    assert "quality_score" in process_json["results"][0]["summary"]

    result_download_id = process_json["results"][0]["download_id"]
    download = client.get(f"/api/download/{result_download_id}")
    assert download.status_code == 200
    assert len(download.content) > 0
