import pandas as pd

from backend.application.parsing.models import ParsedSheet
from backend.application.processing.normalization import ProcessingNormalizationMixin
from backend.application.processing.service import TimeSheetProcessor
from backend.domain.models import ColumnMapping
from backend.application.processing.correction_result import CorrectionResult


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


class _BlobStorageStub:
    def __init__(self):
        self.uploads = []

    def upload_bytes_to_blob(self, blob_name, data, *, overwrite=True):
        self.uploads.append((blob_name, data, overwrite))

    def download_blob_to_bytes(self, blob_name):
        raise NotImplementedError


class _WorkbookExporterStub:
    def export_workbook(self, corrected_df, errors_df, summary, *, debug_hours_df=None, debug_detail_df=None):
        return b"workbook-bytes"


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


def test_timesheet_processor_uses_injected_blob_storage_port():
    blob_storage = _BlobStorageStub()
    processor = TimeSheetProcessor(
        llm_corrector=_LLMStub(),
        blob_storage=blob_storage,
        workbook_exporter=_WorkbookExporterStub(),
        role_validator=_RoleValidatorStub(),
    )
    mapping = ColumnMapping(date="Fecha", hours="Horas", description="Actividad", project="Proyecto")
    parsed = ParsedSheet(
        dataframe=pd.DataFrame(
            {
                "Fecha": ["2026-01-01"],
                "Horas": [8],
                "Actividad": ["trabajo detallado"],
                "Proyecto": ["Proyecto X"],
            }
        ),
        header_row=0,
        row_offset=2,
        sheet_name="Sheet1",
        metadata={"company": "Nova"},
    )

    result = processor.process_parsed_sheet(
        parsed_sheet=parsed,
        mapping=mapping,
        source_name="archivo.xlsx",
        original_excel_bytes=b"original",
        correct_spelling=False,
        upload_to_blob=True,
        blob_name_original="raw/blob.xlsx",
        blob_name_corrected="clean/blob.xlsx",
        enable_debug_exports=False,
    )

    assert result.uploaded_blob_original == "raw/blob.xlsx"
    assert result.uploaded_blob_corrected == "clean/blob.xlsx"
    assert [item[0] for item in blob_storage.uploads] == [
        "raw/blob.xlsx",
        "clean/blob.xlsx",
    ]


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
