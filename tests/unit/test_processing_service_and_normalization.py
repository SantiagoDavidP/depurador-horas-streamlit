import pandas as pd

from backend.application.processing.normalization import ProcessingNormalizationMixin
from backend.application.processing.service import TimeSheetProcessor
from backend.domain.models import ColumnMapping
from backend.domain.parsing.excel_parser import ParsedSheet
from backend.infrastructure.ai.llm_corrector import CorrectionResult


class _LLMStub:
    def correct_descriptions(self, rows, *, role="Desconocido", project="No especificado"):
        return [
            CorrectionResult(
                fila=rows[0][0],
                original_text=rows[0][1],
                corrected_text=f"{rows[0][1]} (ok)",
                changes=["typo"],
            )
        ]


class _RoleResult:
    def __init__(self, is_valid, score, rol, reason):
        self.is_valid = is_valid
        self.confidence_score = score
        self.rol_detectado = rol
        self.reasoning = reason


class _RoleValidatorStub:
    def batch_validate(self, descriptions, declared_role):
        out = []
        for d in descriptions:
            out.append(_RoleResult(bool(d.strip()), 0.8 if d.strip() else 0.0, declared_role, "ok"))
        return out


def test_timesheet_processor_helpers_and_apply_corrections():
    processor = TimeSheetProcessor(llm_corrector=_LLMStub(), role_validator=_RoleValidatorStub())
    mapping = ColumnMapping(date="Fecha", hours="Horas", description="Actividad", project="Proyecto")

    parsed = ParsedSheet(
        dataframe=pd.DataFrame(
            {
                "Fecha": ["2026-01-01", "2026-01-02"],
                "Horas": [8, 2],
                "Actividad": ["texto base", " "],
            }
        ),
        header_row=1,
        row_offset=2,
        sheet_name="Sheet1",
        metadata={},
    )

    rows = processor._get_row_numbers(parsed)
    assert rows == [3, 4]
    assert processor._build_output_filename("archivo.xlsx").endswith("_CORREGIDO.xlsx")

    analyzed = processor._analyze_role(parsed.dataframe, mapping, "developer", rows)
    assert analyzed["score"] is not None
    assert isinstance(analyzed["details"], list)

    corrected = parsed.dataframe.copy()
    corrections = processor._apply_corrections(
        corrected,
        mapping,
        rows,
        enable_llm=True,
        role="developer",
        project="Proyecto X",
    )
    assert corrections
    assert "(ok)" in corrected.loc[0, "Actividad"]

    assert processor._is_baninter_profile("cliente_talent", {}) is True
    assert processor._is_baninter_profile(None, {"company": "Banco Internacional"}) is True


def test_normalization_ticket_and_validation_filtering():
    helper = ProcessingNormalizationMixin()
    mapping = ColumnMapping(date="Fecha", hours="Horas", description="Actividad", project="Proyecto")

    df = pd.DataFrame(
        {
            "Fecha": ["2026-01-01", None, None],
            "Horas": [1, 2, 0],
            "Actividad": ["Trabajo", "Soporte", "total del dia"],
            "Ticket": ["ABC 1", "??", "SN"],
            "Proyecto": ["P1", "P1", ""],
        }
    )
    filled = helper._fill_grouped_dates_for_payload(
        df,
        date_column="Fecha",
        hours_column="Horas",
        description_column="Actividad",
    )
    assert filled >= 1

    helper._normalize_ticket_columns(df)
    assert df.loc[0, "Ticket"] == "ABC1"

    issues = [
        {"fila": 2, "tipo_error": "ticket_no_numerico", "descripcion": "bad"},
        {"fila": 3, "tipo_error": "ticket_invalido", "descripcion": "bad"},
        {"fila": 4, "tipo_error": "otro", "descripcion": "x"},
    ]
    filtered = helper._normalize_ticket_validation_errors(issues, df, "Ticket", [2, 3, 4])
    assert any(i["tipo_error"] == "otro" for i in filtered)
    assert all(i["tipo_error"] != "ticket_no_numerico" for i in filtered)

    sorted_df = helper._sort_errors_df(pd.DataFrame([{"tipo_error": "descripcion_repetida"}, {"tipo_error": "fecha_invalida"}]))
    assert sorted_df.iloc[0]["tipo_error"] == "fecha_invalida"

    helper._apply_validation_corrections(
        df,
        mapping,
        [2, 3, 4],
        [{"fila": 2, "tipo_error": "descripcion_calidad", "valor_corregido": "Texto limpio"}],
    )
    assert df.loc[0, "Actividad"] == "Texto limpio"
