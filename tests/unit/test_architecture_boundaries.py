from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, List, Sequence, get_args, get_origin, get_type_hints

from backend.application.consolidation.models import ConsultorMetrics
from backend.application.parsing.models import ParsedSheet
from backend.application.ports.timesheet_reporting_port import TimesheetReportingPort
from backend.application.ports.workbook_export_port import WorkbookExportPort
from backend.application.processing.models import ProcessorResult
from backend.application.tabular.table_data import TableData


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
DOMAIN_ROOT = BACKEND_ROOT / "domain"
APPLICATION_ROOT = BACKEND_ROOT / "application"

FORBIDDEN_DOMAIN_IMPORT_PREFIXES = (
    "backend.infrastructure",
    "pandas",
    "openpyxl",
)
FORBIDDEN_APPLICATION_IMPORT_PREFIXES = ("backend.infrastructure",)
CORE_CONTRACT_PATHS = (
    APPLICATION_ROOT / "ports",
    APPLICATION_ROOT / "parsing",
    APPLICATION_ROOT / "consolidation" / "models.py",
    APPLICATION_ROOT / "processing" / "models.py",
)
FORBIDDEN_CORE_CONTRACT_IMPORT_PREFIXES = (
    "pandas",
    "openpyxl",
    "backend.infrastructure",
)


def _python_files(root: Path) -> List[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def _iter_paths(paths: Sequence[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_dir():
            yield from _python_files(path)
        elif path.is_file():
            yield path


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _imported_modules(path: Path) -> List[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    modules: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def _offending_imports(paths: Sequence[Path], forbidden_prefixes: Sequence[str]) -> List[str]:
    offenses: List[str] = []
    for path in _iter_paths(paths):
        forbidden = sorted(
            {
                module
                for module in _imported_modules(path)
                if any(
                    module == prefix or module.startswith(f"{prefix}.")
                    for prefix in forbidden_prefixes
                )
            }
        )
        if forbidden:
            offenses.append(f"{_relative(path)} -> {', '.join(forbidden)}")
    return offenses


def _assert_table_data_annotation(annotation: object, *, context: str) -> None:
    assert annotation is TableData, f"{context} debe usar TableData y no {annotation!r}"


def _assert_list_of_tabledata_tuple(annotation: object, *, context: str) -> None:
    origin = get_origin(annotation)
    assert origin in (list, List), f"{context} debe ser List[...]"
    tuple_type = get_args(annotation)[0]
    assert get_origin(tuple_type) is tuple, f"{context} debe contener tuplas"
    tuple_args = get_args(tuple_type)
    assert tuple_args and tuple_args[0] is TableData, (
        f"{context} debe transportar TableData como primer elemento de la tupla"
    )


def test_domain_remains_pure_and_free_of_infrastructure_imports() -> None:
    offenses = _offending_imports([DOMAIN_ROOT], FORBIDDEN_DOMAIN_IMPORT_PREFIXES)
    assert not offenses, (
        "backend/domain no debe importar infraestructura ni librerias tecnicas.\n"
        + "\n".join(offenses)
    )


def test_application_and_domain_do_not_import_infrastructure() -> None:
    offenses = _offending_imports(
        [APPLICATION_ROOT, DOMAIN_ROOT],
        FORBIDDEN_APPLICATION_IMPORT_PREFIXES,
    )
    assert not offenses, (
        "backend/application y backend/domain no deben depender de backend.infrastructure.\n"
        + "\n".join(offenses)
    )


def test_core_contract_modules_do_not_import_pandas_or_openpyxl() -> None:
    offenses = _offending_imports(CORE_CONTRACT_PATHS, FORBIDDEN_CORE_CONTRACT_IMPORT_PREFIXES)
    assert not offenses, (
        "Los contratos centrales del core deben permanecer neutrales.\n"
        + "\n".join(offenses)
    )


def test_core_dtos_use_tabledata_instead_of_dataframe() -> None:
    parsed_hints = get_type_hints(ParsedSheet)
    processor_hints = get_type_hints(ProcessorResult)
    metrics_hints = get_type_hints(ConsultorMetrics)

    _assert_table_data_annotation(parsed_hints["dataframe"], context="ParsedSheet.dataframe")
    _assert_table_data_annotation(
        processor_hints["corrected_dataframe"],
        context="ProcessorResult.corrected_dataframe",
    )
    _assert_table_data_annotation(
        processor_hints["errors_dataframe"],
        context="ProcessorResult.errors_dataframe",
    )
    _assert_table_data_annotation(
        metrics_hints["dataframe"],
        context="ConsultorMetrics.dataframe",
    )


def test_output_ports_keep_tabledata_at_the_boundary() -> None:
    workbook_hints = get_type_hints(WorkbookExportPort.export_workbook)
    reporting_consolidated_hints = get_type_hints(
        TimesheetReportingPort.generate_consolidated_report
    )
    reporting_single_hints = get_type_hints(
        TimesheetReportingPort.generate_single_consultant_report
    )

    _assert_table_data_annotation(
        workbook_hints["corrected_df"],
        context="WorkbookExportPort.export_workbook.corrected_df",
    )
    _assert_table_data_annotation(
        workbook_hints["errors_df"],
        context="WorkbookExportPort.export_workbook.errors_df",
    )
    _assert_table_data_annotation(
        reporting_single_hints["dataframe"],
        context="TimesheetReportingPort.generate_single_consultant_report.dataframe",
    )
    _assert_list_of_tabledata_tuple(
        reporting_consolidated_hints["consultores_data"],
        context="TimesheetReportingPort.generate_consolidated_report.consultores_data",
    )
