import json
from pathlib import Path

from backend.domain.profiles import detectors
from backend.domain.profiles.client_profiles import ClientProfile
from backend.domain.rates.collaborator_rates import CollaboratorRatesManager
from backend.domain.roles.role_validator import RoleActivityValidator


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
        settings={},
        keywords=["nova", "bit"],
        company_aliases=["nova", "business it"],
    )


def test_detectors_filename_metadata_and_dataframe_profile():
    profile = _profile()

    employee = detectors.extract_employee_from_filename("Resumen_Actividades_Luis_Avila_Enero_2026.xlsx")
    assert employee is not None

    assert detectors.detect_client_from_filename("NOVA_reporte.xlsx", profile) is True
    assert detectors.detect_client_from_metadata({"company": "Business IT NOVA"}, profile) is True

    auto = detectors.auto_detect_profile("NOVA_reporte.xlsx", {"company": "NOVA"}, [profile])
    assert auto == "cliente_bit"

    resolved = detectors.resolve_employee({"employee": "Ana Perez"}, "ana_perez.xlsx")
    assert resolved["final"] == "Ana Perez"

    by_columns = detectors.detect_profile_from_dataframe(
        ["Fecha", "Horas", "Actividad", "Proyecto"],
        [profile],
        min_score=2,
    )
    assert by_columns == "cliente_bit"


def test_role_validator_scoring_and_batch(tmp_path):
    taxonomy = {
        "developer": {"technical_skills": ["api", "sql", "commit"]},
        "qa": {"activities": ["testing", "regression"]},
        "devops": {"tools": ["docker", "kubernetes"]},
    }
    taxonomy_path = tmp_path / "roles.json"
    taxonomy_path.write_text(json.dumps(taxonomy), encoding="utf-8")

    validator = RoleActivityValidator.from_json(taxonomy_path)

    universal = validator.validate_activity_for_role("Daily meeting con equipo", "developer")
    assert universal.is_valid is True
    assert universal.confidence_score >= 0.9

    dev_ok = validator.validate_activity_for_role("Implementa endpoint API y hace commit en branch", "developer")
    assert dev_ok.rol_detectado == "developer"
    assert dev_ok.confidence_score > 0

    unknown = validator.validate_activity_for_role("Trabajo general", "rol_inexistente")
    assert unknown.is_valid is False

    detected = validator.detect_role_from_activity("Deploy con docker en kubernetes")
    assert detected in {"devops", "developer", "qa"}

    batch = validator.batch_validate(
        ["Testing regression y casos de prueba", "Deploy a producción con pipeline"],
        "qa",
    )
    assert len(batch) == 2

    # Cobertura explícita del helper contextual
    context = validator._analyze_developer_context("desarrollar pruebas de integración para pasar a qa")
    assert context["confidence_adjustment"] >= 0


def test_collaborator_rates_manager_load_and_lookup(tmp_path):
    config = {
        "collaborators": {
            "luis_avila": {
                "nombre_completo": "Luis Avila",
                "seniority": "Senior",
                "cargo": "Arquitecto",
                "dias_laborables_mes": 22,
                "salario_mensual": 3000,
                "valor_diario": 136.36,
                "valor_hora_extra": 25,
                "activo": True,
                "nombres_alternativos": ["Luis Avila", "L. Avila"],
            }
        },
        "seniority_defaults": {
            "Senior": {
                "salario_mensual_default": 2770,
                "valor_hora_extra_default": 25,
                "dias_laborables_default": 22,
            },
            "Junior": {
                "salario_mensual_default": 1670,
                "valor_hora_extra_default": 20,
                "dias_laborables_default": 21,
            },
        },
    }
    config_path = tmp_path / "collaborator_rates.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    manager = CollaboratorRatesManager(config_path=config_path)
    found = manager.find_collaborator("Luis Avila")
    assert found is not None
    assert found.seniority == "Senior"

    fuzzy = manager.find_collaborator("L Avila")
    assert fuzzy is not None

    by_seniority = manager.get_rate_by_seniority("Senior")
    assert by_seniority is not None
    assert by_seniority["salario_mensual"] == 2770

    full_rate = manager.get_rate_for_collaborator("Luis Avila", seniority_fallback="Junior")
    assert full_rate["source"] == "collaborator"
    assert full_rate["found_by_name"] is True

    fallback_rate = manager.get_rate_for_collaborator("Persona X", seniority_fallback="Junior")
    assert fallback_rate["source"] == "seniority"
    assert fallback_rate["found_by_name"] is False

    unknown = manager.get_rate_for_collaborator("Persona Y", seniority_fallback="NoExiste")
    assert unknown["source"] == "unknown"

    all_active = manager.list_all_collaborators(active_only=True)
    assert len(all_active) == 1
    by_sen = manager.list_by_seniority("Senior")
    assert len(by_sen) == 1

    manager.reload_config()
    assert manager.find_collaborator("Luis Avila") is not None
