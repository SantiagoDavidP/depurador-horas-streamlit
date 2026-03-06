import json

import pytest
from fastapi import HTTPException

from api.presentation import handlers_batch
from api.presentation.parsing import parse_payload
from backend.domain.profiles.client_profiles import ClientProfile


class _BatchProcessorStub:
    def process_batch(self, files, *, max_workers=4):
        return []


class _FileStoreStub:
    def __init__(self):
        self.last_source = None
        self.last_results = None

    def store_batch(self, results, source="batch"):
        self.last_results = results
        self.last_source = source
        return "batch-test-id"


@pytest.mark.unit
def test_parse_payload_accepts_json_string():
    payload = parse_payload('{"profileId":"cliente_bit","maxWorkers":4}')
    assert payload["profileId"] == "cliente_bit"
    assert payload["maxWorkers"] == 4


@pytest.mark.unit
def test_parse_payload_raises_http_400_on_invalid_json():
    with pytest.raises(HTTPException) as exc:
        parse_payload("{invalid}")
    assert exc.value.status_code == 400
    assert "Invalid JSON payload" in str(exc.value.detail)


@pytest.mark.unit
def test_process_batch_requires_mappingvalues_when_profile_is_null():
    payload = {
        "profileId": None,
        "mapping": {
            "date": "Fecha",
            "hours": "Horas",
            "description": "Actividad",
        },
    }
    with pytest.raises(HTTPException) as exc:
        handlers_batch.process_batch(files=[], payload=json.dumps(payload), user=None)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Missing required mapping"


@pytest.mark.unit
def test_process_batch_accepts_mappingvalues_without_profile(monkeypatch):
    monkeypatch.setattr(handlers_batch, "get_profile_catalog", lambda: {})
    monkeypatch.setattr(handlers_batch, "batch_processor", _BatchProcessorStub())
    file_store = _FileStoreStub()
    monkeypatch.setattr(handlers_batch, "file_store", file_store)

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
    response = handlers_batch.process_batch(
        files=[],
        payload=json.dumps(payload),
        user=None,
    )
    assert response["batch_id"] == "batch-test-id"
    assert response["results"] == []
    assert file_store.last_source == "batch"


@pytest.mark.unit
def test_process_batch_allows_missing_mappingvalues_when_profile_exists(monkeypatch):
    profile = ClientProfile(
        client_id="cliente_demo",
        name="Cliente Demo",
        mapping={
            "date": "Fecha",
            "hours": "Horas",
            "description": "Actividad",
            "project": "Proyecto",
        },
        settings={},
    )
    monkeypatch.setattr(handlers_batch, "get_profile_catalog", lambda: {"cliente_demo": profile})
    monkeypatch.setattr(handlers_batch, "batch_processor", _BatchProcessorStub())
    monkeypatch.setattr(handlers_batch, "file_store", _FileStoreStub())

    payload = {
        "profileId": "cliente_demo",
        "mapping": {
            "date": "A",
            "hours": "B",
            "description": "C",
        },
    }
    response = handlers_batch.process_batch(
        files=[],
        payload=json.dumps(payload),
        user=None,
    )
    assert response["batch_id"] == "batch-test-id"
    assert isinstance(response["results"], list)


@pytest.mark.unit
def test_process_batch_rejects_legacy_auto_profile_payload():
    payload = {
        "auto_profile_id": "cliente_demo",
        "profile_mapping": {
            "date": "Fecha",
            "hours": "Horas",
            "description": "Actividad",
        },
    }
    with pytest.raises(HTTPException) as exc:
        handlers_batch.process_batch(files=[], payload=json.dumps(payload), user=None)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Missing required mapping"
