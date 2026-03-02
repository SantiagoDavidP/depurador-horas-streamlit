from __future__ import annotations

from typing import Dict, Optional

from api.serializers import (
    build_holiday_info,
    dataframe_to_records,
    sanitize_payload,
    sort_errors_dataframe,
    summary_to_dict,
)
from api.services import is_baninter_result, resolve_employee
from api.presentation.dependencies import file_store
from api.presentation.parsing import compact_metadata
from api.presentation.parsing import to_bool
from backend.batch_processor import BatchFileResult
from backend.consolidator_integration import generate_individual_business_it_excel
from backend.models import ColumnMapping


def _serialize_result(
    result: BatchFileResult,
    *,
    mapping: Optional[ColumnMapping],
    source_filename: str,
) -> Dict[str, object]:
    safe_meta = compact_metadata(result.metadata)

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
            "llm_enabled": to_bool((res.metadata or {}).get("llm_enabled"), default=False),
            "llm_corrections_count": len(res.corrections_log or []),
        }
    )

    if is_baninter_result(result.file_name, result.metadata, result.client_id):
        try:
            business_bytes, business_name = generate_individual_business_it_excel(
                result, cliente="BANINTER"
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
