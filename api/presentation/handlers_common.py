from __future__ import annotations

from typing import Dict, List, Optional

from api.serializers import (
    build_holiday_info,
    dataframe_to_records,
    sort_errors_dataframe,
    summary_to_dict,
)
from api.services import is_baninter_result, resolve_employee
from backend.application.batch.batch_processor import BatchFileResult
from backend.application.consolidation.consolidator_integration import generate_individual_business_it_excel
from backend.domain.models import ColumnMapping
from backend.infrastructure.config.collaborator_rates_repository import get_collaborator_rates_manager

from api.presentation.dependencies import file_store, timesheet_reporting
from api.presentation.parsing import compact_metadata as _compact_metadata
from api.presentation.parsing import to_bool as _to_bool


def _serialize_result(
    result: BatchFileResult,
    *,
    mapping: Optional[ColumnMapping],
    source_filename: str,
) -> Dict[str, object]:
    safe_meta = _compact_metadata(result.metadata)

    base = {
        "file_name": result.file_name,
        "sheet_name": result.sheet_name,
        "success": result.success,
        "client_id": result.client_id,
        "metadata": safe_meta,
    }
    if not result.success or not result.result:
        base["error"] = result.error
        return base

    res = result.result
    summary = summary_to_dict(res.summary)
    errors_df = sort_errors_dataframe(res.errors_dataframe)
    errors = dataframe_to_records(errors_df)
    employee_info = resolve_employee(result.metadata or {}, source_filename)

    download_id = file_store.store_file(
        res.workbook_bytes,
        res.output_filename,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    holiday_info = build_holiday_info(
        res.corrected_dataframe,
        mapping.date if mapping else None,
        metadata=res.metadata,
    )

    base.update(
        {
            "summary": summary,
            "errors": errors,
            "employee_info": employee_info,
            "download_id": download_id,
            "output_filename": res.output_filename,
            "holiday_info": holiday_info,
            "llm_enabled": _to_bool((res.metadata or {}).get("llm_enabled"), default=False),
            "llm_corrections_count": len(res.corrections_log or []),
        }
    )

    if is_baninter_result(result.file_name, result.metadata, result.client_id):
        try:
            business_bytes, business_name = generate_individual_business_it_excel(
                result,
                cliente="BANINTER",
                reporting_port=timesheet_reporting,
                collaborator_rates=get_collaborator_rates_manager(),
            )
            business_id = file_store.store_file(
                business_bytes,
                business_name,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            base["baninter_business_id"] = business_id
            base["baninter_business_filename"] = business_name
        except Exception:
            pass
    return base


def _build_baninter_zip(batch_results: List[BatchFileResult]) -> Optional[bytes]:
    import zipfile
    from io import BytesIO

    buffer = BytesIO()
    written = 0
    used_names = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, res in enumerate(batch_results):
            if not (res.success and res.result):
                continue
            if not is_baninter_result(res.file_name, res.metadata, res.client_id):
                continue
            business_bytes, business_name = generate_individual_business_it_excel(
                res,
                cliente="BANINTER",
                reporting_port=timesheet_reporting,
                collaborator_rates=get_collaborator_rates_manager(),
            )
            safe_name = business_name or f"BANINTER_{idx + 1}.xlsx"
            if safe_name in used_names:
                stem, ext = safe_name.rsplit(".", 1) if "." in safe_name else (safe_name, "xlsx")
                safe_name = f"{stem}_{idx + 1}.{ext}"
            used_names.add(safe_name)
            zf.writestr(safe_name, business_bytes)
            written += 1
    if written == 0:
        return None
    buffer.seek(0)
    return buffer.getvalue()


def _infer_client_id_for_file(
    file_name: str,
    metadata: Optional[Dict[str, object]],
    fallback_client_id: Optional[str],
) -> Optional[str]:
    if fallback_client_id == "cliente_talent":
        return fallback_client_id

    fname = str(file_name or "").lower()
    company = str((metadata or {}).get("company", "")).lower()

    if (
        "baninter" in fname
        or "banco internacional" in fname
        or "resumen actividades recursos" in fname
        or "baninter" in company
        or "banco internacional" in company
    ):
        return "cliente_talent"

    if (
        "nova" in fname
        or "bit" in fname
        or "nova" in company
        or "bit" in company
    ):
        return "cliente_bit"

    return fallback_client_id


__all__ = ["_serialize_result", "_build_baninter_zip", "_infer_client_id_for_file"]
