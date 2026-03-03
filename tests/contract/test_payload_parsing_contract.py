import pytest
from fastapi import HTTPException

from api.presentation.parsing import parse_payload


@pytest.mark.contract
def test_parse_payload_accepts_json_string():
    payload = parse_payload('{"profileId":"cliente_bit","maxWorkers":4}')
    assert payload["profileId"] == "cliente_bit"
    assert payload["maxWorkers"] == 4


@pytest.mark.contract
def test_parse_payload_raises_http_400_on_invalid_json():
    with pytest.raises(HTTPException) as exc:
        parse_payload("{invalid}")
    assert exc.value.status_code == 400
    assert "Invalid JSON payload" in str(exc.value.detail)
