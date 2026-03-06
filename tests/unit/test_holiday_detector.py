import pandas as pd
import pytest

from backend.application.calendar.holiday_detector import HolidayDetector


@pytest.mark.unit
def test_detect_month_holidays_empty_dataframe():
    detector = HolidayDetector()
    info = detector.detect_month_holidays(pd.DataFrame(), "Fecha")
    assert info.source == "vacio"
    assert info.holidays == []


@pytest.mark.unit
def test_detect_month_holidays_missing_column_raises():
    detector = HolidayDetector()
    df = pd.DataFrame({"Otra": ["2025-01-01"]})
    with pytest.raises(ValueError, match="no existe"):
        detector.detect_month_holidays(df, "Fecha")


@pytest.mark.unit
def test_detect_period_holidays_handles_invalid_period():
    detector = HolidayDetector()
    info = detector.detect_period_holidays("invalid", "also-invalid")
    assert info.source == "periodo_invalido"
    assert info.holidays == []


@pytest.mark.unit
def test_detect_period_holidays_handles_reversed_year_range():
    detector = HolidayDetector()
    info = detector.detect_period_holidays("2025-09-01", "2024-09-30")
    assert info.month == 9
    assert info.year == 2025
    assert info.source in {"holidays_lib", "fallback"}
