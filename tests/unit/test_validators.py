import pandas as pd
import pytest

from backend.domain.validation.validators import (
    _get_ec_holidays,
    run_all_validations,
    validate_calendar_constraints,
    validate_daily_hours,
    validate_mapping,
    validate_missing_fields,
)


@pytest.mark.unit
def test_validate_mapping_rejects_missing_required_columns(sample_dataframe):
    with pytest.raises(ValueError, match="columnas requeridas"):
        validate_mapping(
            sample_dataframe,
            date_col="FechaInexistente",
            hours_col="Horas",
            description_col="Descripcion",
        )


@pytest.mark.unit
def test_validate_calendar_constraints_detects_invalid_and_weekend():
    df = pd.DataFrame(
        {
            "Fecha": ["fecha-invalida", "2025-01-11", "2025-01-13"],
            "Horas": [8, 8, 8],
        }
    )
    issues = validate_calendar_constraints(df, date_column="Fecha")
    issue_types = {item["tipo_error"] for item in issues}
    assert "fecha_invalida" in issue_types
    assert "fin_semana" in issue_types


@pytest.mark.unit
def test_validate_daily_hours_detects_missing_and_incorrect():
    df = pd.DataFrame(
        {
            "Fecha": ["2025-01-13", "2025-01-13", "2025-01-14"],
            "Horas": [4, 3, 0],
        }
    )
    issues = validate_daily_hours(
        df,
        date_column="Fecha",
        hours_column="Horas",
        expected_hours=8.0,
    )
    issue_types = [item["tipo_error"] for item in issues]
    assert "horas_incorrectas" in issue_types
    assert "horas_faltantes" in issue_types


@pytest.mark.unit
def test_validate_missing_fields_ignores_technical_columns():
    df = pd.DataFrame(
        {
            "Fecha": ["2025-01-13"],
            "Horas": [8],
            "Actividad": [""],
            "Unnamed: 6": [None],
        }
    )
    issues = validate_missing_fields(
        df,
        date_column="Fecha",
        hours_column="Horas",
    )
    assert len(issues) == 1
    assert issues[0]["tipo_error"] == "campo_vacio"
    assert "Actividad" in issues[0]["descripcion"]


@pytest.mark.unit
def test_run_all_validations_includes_completeness():
    df = pd.DataFrame(
        {
            "Fecha": ["2025-01-02"],
            "Horas": [8],
            "Actividad": ["Desarrollo modulo core"],
            "Proyecto": ["Proyecto X"],
        }
    )
    issues = run_all_validations(
        df,
        date_column="Fecha",
        hours_column="Horas",
        description_column="Actividad",
        project_column="Proyecto",
        check_completeness=True,
        period_year=2025,
        period_month=1,
        duplicate_fuzzy_enabled=False,
    )
    issue_types = {item["tipo_error"] for item in issues}
    assert "completitud" in issue_types


@pytest.mark.unit
def test_get_ec_holidays_uses_cache():
    _get_ec_holidays.cache_clear()
    first = _get_ec_holidays(2025)
    info_before = _get_ec_holidays.cache_info()
    second = _get_ec_holidays(2025)
    info_after = _get_ec_holidays.cache_info()
    assert first == second
    assert info_after.hits > info_before.hits
