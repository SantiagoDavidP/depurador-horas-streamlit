import pandas as pd
import pytest

from backend.application.profiles.profile_validations import run_profile_validations


@pytest.mark.unit
def test_run_profile_validations_returns_empty_without_profile():
    df = pd.DataFrame({"Fecha": ["2025-01-01"], "Horas": [8]})
    issues = run_profile_validations(None, df, {}, row_numbers=[2])
    assert issues == []


@pytest.mark.unit
def test_validate_bit_nova_detects_employee_inconsistency_and_ticket():
    df = pd.DataFrame(
        {
            "Tecnico": ["Juan Perez"],
            "Fecha": ["2025-01-15"],
            "Ticket": ["TK-001*"],
            "Tipo Hora": ["HN"],
        }
    )
    metadata = {
        "employee": "Maria Perez",
        "period_start": "2025-01-01",
        "period_end": "2025-01-31",
        "tipos_hora_validos": ["HN"],
    }
    issues = run_profile_validations("cliente_bit", df, metadata, row_numbers=[2])
    issue_types = {item["tipo_error"] for item in issues}
    assert "inconsistencia_empleado" in issue_types
    assert "ticket_invalido" in issue_types


@pytest.mark.unit
def test_validate_bit_nova_detects_out_of_period_and_invalid_hour_type():
    df = pd.DataFrame(
        {
            "Tecnico": ["Luis", "Luis"],
            "Fecha": ["2025-02-05", "2025-01-10"],
            "Ticket": ["1001", "1002"],
            "Tipo Hora": ["ZZ", "HN"],
        }
    )
    metadata = {
        "employee": "Luis",
        "period_start": "2025-01-01",
        "period_end": "2025-01-31",
        "tipos_hora_validos": ["HN"],
    }
    issues = run_profile_validations("cliente_bit", df, metadata, row_numbers=[2, 3])
    issue_types = {item["tipo_error"] for item in issues}
    assert "fecha_fuera_periodo" in issue_types
    assert "tipo_hora_invalido" in issue_types
