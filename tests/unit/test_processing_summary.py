import pandas as pd
import pytest

from backend.application.processing.summary import ProcessingSummaryMixin
from backend.domain.models import ColumnMapping


class _SummaryHarness(ProcessingSummaryMixin):
    pass


@pytest.mark.unit
def test_create_summary_computes_quality_score_and_counts():
    harness = _SummaryHarness()
    df = pd.DataFrame({"Horas": [2, 6]})
    errors = [
        {
            "fila": 2,
            "fecha": "2025-01-02",
            "tipo_error": "completitud",
            "descripcion": "faltan dias",
            "valor_original": "",
            "valor_corregido": "",
        },
        {
            "fila": 3,
            "fecha": "2025-01-02",
            "tipo_error": "horas_excesivas",
            "descripcion": "too much",
            "valor_original": "10",
            "valor_corregido": "8",
        },
        {
            "fila": 4,
            "fecha": "2025-01-03",
            "tipo_error": "descripcion_calidad",
            "descripcion": "muy corta",
            "valor_original": "x",
            "valor_corregido": "",
        },
        {
            "fila": 5,
            "fecha": "2025-01-03",
            "tipo_error": "duplicado_exacto",
            "descripcion": "copy paste",
            "valor_original": "igual",
            "valor_corregido": "",
        },
    ]
    mapping = ColumnMapping(date="Fecha", hours="Horas", description="Actividad")

    summary = harness._create_summary(df, errors, mapping, metadata_removed=1)

    assert summary.total_registros == 2
    assert summary.total_errores == 4
    assert summary.horas_totales == 8.0
    assert summary.metadata_removidas == 1
    assert summary.errores_criticos == 1
    assert summary.errores_advertencia == 2
    assert summary.quality_score == pytest.approx(59.0, abs=0.01)
    assert summary.errores_por_tipo["completitud"] == 1
    assert summary.errores_por_tipo["duplicado_exacto"] == 1


@pytest.mark.unit
def test_create_summary_clamps_quality_score_to_zero():
    harness = _SummaryHarness()
    df = pd.DataFrame({"Horas": [8]})
    errors = []
    for i in range(20):
        errors.append(
            {
                "fila": i + 2,
                "fecha": "2025-01-02",
                "tipo_error": "horas_excesivas",
                "descripcion": "critico",
                "valor_original": "10",
                "valor_corregido": "8",
            }
        )

    mapping = ColumnMapping(date="Fecha", hours="Horas", description="Actividad")
    summary = harness._create_summary(df, errors, mapping, metadata_removed=0)
    assert summary.quality_score == 0.0
