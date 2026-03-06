from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from api.main import app
from api.presentation import handlers_batch, handlers_common, handlers_download, handlers_individual_process
from api.presentation.dependencies import auth_provider
from backend.application.batch.batch_processor import BatchFileResult
from backend.application.processing.correction_result import CorrectionResult
from backend.application.processing.models import ProcessorResult
from backend.infrastructure.ai.llm_corrector_adapter import LLMCorrectorAdapter


GOLDEN_DIR = Path(__file__).resolve().parents[1] / "golden"


@dataclass
class _StoredBatch:
    results: list
    source: str = "batch"


class _DeterministicFileStore:
    def __init__(self) -> None:
        self.files: Dict[str, Dict[str, object]] = {}
        self.batches: Dict[str, _StoredBatch] = {}
        self._file_counter = 0
        self._batch_counter = 0

    def store_file(self, data: bytes, filename: str, content_type: str) -> str:
        self._file_counter += 1
        file_id = f"file-{self._file_counter}"
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
        self._batch_counter += 1
        batch_id = f"batch-{self._batch_counter}"
        self.batches[batch_id] = _StoredBatch(results=list(results), source=source)
        return batch_id

    def get_batch(self, batch_id: str):
        return self.batches.get(batch_id)


def _individual_payload(profile_id: str) -> Dict[str, object]:
    return {
        "profileId": profile_id,
        "maxWorkers": 1,
        "settings": {
            "correctSpelling": False,
            "duplicateSimilarityThreshold": 90,
            "duplicateMinOccurrences": 3,
            "hoursToleranceFactor": 1.5,
        },
    }


def _workbook_bytes(
    *,
    sheet_name: str,
    company: Optional[str],
    employee: Optional[str],
    headers: Iterable[str],
    rows: Iterable[Iterable[object]],
    report_date: str = "2026-01-31",
    period: str = "01/01/2026 - 31/01/2026",
    extra_sheets: Optional[List[Dict[str, object]]] = None,
) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    if company or employee:
        ws.append(["INFORME ACTIVIDADES"])
        ws.append(["Fecha del Informe:", report_date])
        ws.append(["Periodo Informe:", period])
        ws.append(["Empresa:", company or ""])
        ws.append(["Consultor:", employee or ""])
        ws.append([])
    ws.append(list(headers))
    for row in rows:
        ws.append(list(row))

    for extra in extra_sheets or []:
        extra_ws = wb.create_sheet(str(extra["title"]))
        if extra.get("rows"):
            for row in extra["rows"]:  # type: ignore[index]
                extra_ws.append(list(row))

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _nova_excel_bytes() -> bytes:
    return _workbook_bytes(
        sheet_name="BIT Nova",
        company="BIT Nova",
        employee="Victor Jaramillo",
        headers=["Fecha", "Horas", "Actividad", "Tipo Actividad"],
        rows=[
            ["13/01/2026", 8.0, "Desarrollo de API de pagos", "Desarrollo"],
            ["14/01/2026", 8.0, "Soporte a pruebas QA", "Soporte"],
        ],
    )


def _baninter_excel_bytes(*, with_generic_sheet: bool = False) -> bytes:
    extra_sheets = None
    if with_generic_sheet:
        extra_sheets = [
            {
                "title": "Hoja1",
                "rows": [
                    ["Fecha", "Horas", "Tareas", "Proyecto"],
                    ["2026-01-02", 4.0, "Fila auxiliar", "Aux"],
                ],
            }
        ]
    return _workbook_bytes(
        sheet_name="Victor Jaramillo",
        company="Banco Internacional",
        employee="Victor Jaramillo",
        headers=["Fecha", "Horas", "Tareas", "Proyecto"],
        rows=[
            ["13/01/2026", 8.0, "Atencion de incidentes baninter", "BAN-OPS"],
            ["14/01/2026", 8.0, "Revision de tickets criticos", "BAN-OPS"],
        ],
        extra_sheets=extra_sheets,
    )


def _generic_only_excel_bytes() -> bytes:
    return _workbook_bytes(
        sheet_name="Hoja1",
        company=None,
        employee=None,
        headers=["Fecha", "Horas", "Actividad", "Proyecto"],
        rows=[["2026-01-02", 8.0, "Fila sin metadata", "GEN"]],
    )


def _normalize_holiday_info(payload: Optional[Dict[str, object]]) -> Optional[Dict[str, object]]:
    if not payload:
        return None
    return {
        "month": payload.get("month"),
        "year": payload.get("year"),
        "source": payload.get("source"),
        "holiday_count": len(payload.get("holidays") or []),
    }


def _normalize_result(payload: Dict[str, object]) -> Dict[str, object]:
    summary = payload.get("summary") or {}
    normalized = {
        "file_name": payload.get("file_name"),
        "sheet_name": payload.get("sheet_name"),
        "success": payload.get("success"),
        "client_id": payload.get("client_id"),
        "metadata": payload.get("metadata"),
        "summary": {
            "total_registros": summary.get("total_registros"),
            "total_errores": summary.get("total_errores"),
            "horas_totales": summary.get("horas_totales"),
            "dias_con_problemas_horas": summary.get("dias_con_problemas_horas"),
            "errores_por_tipo": summary.get("errores_por_tipo"),
            "errores_criticos": summary.get("errores_criticos"),
            "errores_advertencia": summary.get("errores_advertencia"),
            "quality_score": summary.get("quality_score"),
        }
        if summary
        else None,
        "errors": [
            {
                key: err.get(key)
                for key in ("fila", "tipo_error", "detalle", "fecha")
                if key in err
            }
            for err in (payload.get("errors") or [])
        ],
        "employee_info": payload.get("employee_info"),
        "download_id": payload.get("download_id"),
        "output_filename": payload.get("output_filename"),
        "holiday_info": _normalize_holiday_info(payload.get("holiday_info")),
        "llm_enabled": payload.get("llm_enabled"),
        "llm_corrections_count": payload.get("llm_corrections_count"),
    }
    if "baninter_business_id" in payload:
        normalized["baninter_business_id"] = payload.get("baninter_business_id")
        normalized["baninter_business_filename"] = payload.get("baninter_business_filename")
    return normalized


def _normalize_batch_process_response(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "batch_id": payload.get("batch_id"),
        "is_baninter": payload.get("is_baninter"),
        "default_client_name": payload.get("default_client_name"),
        "auto_area": payload.get("auto_area"),
        "results": [_normalize_result(item) for item in payload.get("results") or []],
    }


def _normalize_individual_process_response(payload: Dict[str, object]) -> Dict[str, object]:
    consolidated = payload.get("consolidated") or {}
    baninter_zip = payload.get("baninter_zip") or {}
    return {
        "batch_id": payload.get("batch_id"),
        "results": [_normalize_result(item) for item in payload.get("results") or []],
        "skipped_sheets": payload.get("skipped_sheets"),
        "consolidated": {
            "download_id": consolidated.get("download_id"),
            "filename": consolidated.get("filename"),
            "consultores": consolidated.get("consultores"),
            "total_horas": consolidated.get("total_horas"),
        }
        if consolidated
        else None,
        "baninter_zip": {
            "download_id": baninter_zip.get("download_id"),
            "filename": baninter_zip.get("filename"),
        }
        if baninter_zip
        else None,
    }


def _load_golden(name: str) -> Dict[str, object]:
    return json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def api_client(monkeypatch):
    store = _DeterministicFileStore()
    monkeypatch.setattr(auth_provider, "require_user", lambda authorization=None: {"id": "test-user"})
    monkeypatch.setattr(LLMCorrectorAdapter, "correct_descriptions", lambda self, rows, *, role="Desconocido", project="No especificado": [])

    for module in (handlers_batch, handlers_common, handlers_download, handlers_individual_process):
        monkeypatch.setattr(module, "file_store", store)

    client = TestClient(app)
    return client, store


@pytest.mark.integration
def test_post_batch_process_returns_400_for_invalid_json(api_client):
    client, _ = api_client
    response = client.post(
        "/api/batch/process",
        files=[("files", ("nova.xlsx", _nova_excel_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        data={"payload": "{invalid"},
    )
    assert response.status_code == 400
    assert "Invalid JSON payload" in response.json()["detail"]


@pytest.mark.integration
def test_post_batch_process_returns_400_when_mapping_missing_without_profile(api_client):
    client, _ = api_client
    response = client.post(
        "/api/batch/process",
        files=[("files", ("nova.xlsx", _nova_excel_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        data={"payload": json.dumps({"profileId": None, "settings": {"correctSpelling": False}})},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing required mapping"


@pytest.mark.integration
def test_post_batch_process_preserves_input_order_for_multiple_files(api_client):
    client, _ = api_client
    payload = {"profileId": "cliente_bit", "settings": {"correctSpelling": False}, "maxWorkers": 2}
    response = client.post(
        "/api/batch/process",
        files=[
            ("files", ("02_segundo.xlsx", _nova_excel_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ("files", ("01_primero.xlsx", _nova_excel_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ],
        data={"payload": json.dumps(payload)},
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert [item["file_name"] for item in results] == ["02_segundo.xlsx", "01_primero.xlsx"]
    assert all(item["success"] for item in results)


@pytest.mark.integration
def test_post_batch_process_golden_nova_single_excel(api_client):
    client, _ = api_client
    payload = {"profileId": "cliente_bit", "settings": {"correctSpelling": False}, "maxWorkers": 1}
    response = client.post(
        "/api/batch/process",
        files=[("files", ("nova_golden.xlsx", _nova_excel_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        data={"payload": json.dumps(payload)},
    )
    assert response.status_code == 200
    normalized = _normalize_batch_process_response(response.json())
    assert normalized == _load_golden("batch_process_nova.json")


@pytest.mark.integration
def test_post_individual_process_returns_400_for_invalid_json(api_client):
    client, _ = api_client
    response = client.post(
        "/api/individual/process",
        files={"file": ("baninter.xlsx", _baninter_excel_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"payload": "{invalid"},
    )
    assert response.status_code == 400
    assert "Invalid JSON payload" in response.json()["detail"]


@pytest.mark.integration
def test_post_individual_process_returns_400_when_no_valid_sheets_exist(api_client):
    client, _ = api_client
    response = client.post(
        "/api/individual/process",
        files={"file": ("generic.xlsx", _generic_only_excel_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"payload": json.dumps(_individual_payload("cliente_bit"))},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "No valid timesheet sheets detected"


@pytest.mark.integration
def test_post_individual_process_skips_generic_sheet_and_processes_named_sheet(api_client):
    client, _ = api_client
    response = client.post(
        "/api/individual/process",
        files={
            "file": (
                "baninter_mixed.xlsx",
                _baninter_excel_bytes(with_generic_sheet=True),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"payload": json.dumps(_individual_payload("cliente_talent"))},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert payload["results"][0]["success"] is True
    assert any(item["name"] == "Hoja1" for item in payload["skipped_sheets"])


@pytest.mark.integration
def test_post_individual_process_golden_baninter_single_excel(api_client):
    client, _ = api_client
    response = client.post(
        "/api/individual/process",
        files={
            "file": (
                "Resumen Actividades Recursos Baninter.xlsx",
                _baninter_excel_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"payload": json.dumps(_individual_payload("cliente_talent"))},
    )
    assert response.status_code == 200
    normalized = _normalize_individual_process_response(response.json())
    assert normalized == _load_golden("individual_process_baninter.json")


@pytest.mark.integration
def test_post_batch_consolidate_returns_404_for_unknown_batch(api_client):
    client, _ = api_client
    response = client.post("/api/batch/consolidate", json={"batchId": "missing-batch"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Batch not found"


@pytest.mark.integration
def test_post_batch_consolidate_returns_400_for_invalid_stored_batch(api_client):
    client, store = api_client
    store.store_batch(
        [
            BatchFileResult(file_name="broken.xlsx", success=False, error="boom", metadata={})
        ]
    )
    response = client.post("/api/batch/consolidate", json={"batchId": "batch-1"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Batch results not valid for consolidation"


@pytest.mark.integration
def test_post_batch_consolidate_happy_path_returns_downloadable_excel(api_client):
    client, _ = api_client
    process_response = client.post(
        "/api/batch/process",
        files=[("files", ("nova_consolidate.xlsx", _nova_excel_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        data={"payload": json.dumps({"profileId": "cliente_bit", "settings": {"correctSpelling": False}, "maxWorkers": 1})},
    )
    assert process_response.status_code == 200
    batch_id = process_response.json()["batch_id"]

    consolidate = client.post("/api/batch/consolidate", json={"batchId": batch_id})
    assert consolidate.status_code == 200
    consolidate_payload = consolidate.json()
    assert consolidate_payload["filename"].endswith(".xlsx")
    assert consolidate_payload["consultores"] == 1

    download = client.get(f"/api/download/{consolidate_payload['download_id']}")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment; filename=" in download.headers["content-disposition"]
    assert len(download.content) > 100


@pytest.mark.integration
def test_get_download_returns_404_for_unknown_file(api_client):
    client, _ = api_client
    response = client.get("/api/download/unknown-file")
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"
