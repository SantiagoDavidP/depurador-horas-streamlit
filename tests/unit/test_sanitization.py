from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException

from api.presentation.parsing import parse_payload, to_bool
from api.serializers import sanitize_payload


@pytest.mark.unit
def test_sanitize_payload_converts_numpy_and_datetime():
    payload = {
        "num": np.int64(7),
        "when": pd.Timestamp("2025-01-01"),
        "nested": {"dt": datetime(2025, 1, 2, 10, 30)},
    }
    safe = sanitize_payload(payload)
    assert safe["num"] == 7
    assert safe["when"].startswith("2025-01-01")
    assert safe["nested"]["dt"].startswith("2025-01-02T10:30")


@pytest.mark.unit
def test_parse_payload_rejects_invalid_json():
    with pytest.raises(HTTPException) as exc:
        parse_payload("{invalid-json}")
    assert exc.value.status_code == 400
    assert "Invalid JSON payload" in str(exc.value.detail)


@pytest.mark.unit
def test_to_bool_handles_string_variants():
    assert to_bool("true") is True
    assert to_bool("1") is True
    assert to_bool("false") is False
    assert to_bool("0") is False
    assert to_bool(None, default=True) is True
