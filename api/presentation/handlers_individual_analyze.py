from __future__ import annotations

from typing import Dict, Optional

from fastapi import Depends, File, UploadFile

from api.serializers import sanitize_payload
from api.services import auto_detect_profile_from_files, detect_area_from_names, get_profile_catalog
from backend.infrastructure.parsing.excel_sheet_parser import load_multiple_sheets
from backend.shared.tabular.pandas_mapper import to_pandas_table

from api.presentation.dependencies import auth_provider
from api.presentation.parsing import compact_metadata as _compact_metadata


def analyze_individual(
    file: UploadFile = File(...),
    user: Optional[Dict[str, object]] = Depends(auth_provider.require_user),
) -> Dict[str, object]:
    file_bytes = file.file.read()
    sheets = load_multiple_sheets(file_bytes)
    filtered = []
    skipped = []
    for sheet in sheets:
        name_lower = sheet.sheet_name.lower()
        metadata = sheet.metadata or {}
        is_generic = name_lower in ["hoja1", "sheet1", "hoja", "sheet", "hoja 1", "sheet 1"]
        has_no_metadata = not metadata.get("company") and not metadata.get("employee")
        if is_generic and has_no_metadata:
            skipped.append(sheet.sheet_name)
            continue
        filtered.append(sheet)

    sheets = filtered
    profiles = list(get_profile_catalog().values())
    auto_profile_id = None
    metadata = sheets[0].metadata if sheets else {}
    if sheets:
        auto_profile_id = auto_detect_profile_from_files(file_bytes, file.filename, profiles)[0]
        if not auto_profile_id:
            company = str(metadata.get("company", "")).lower()
            for profile in profiles:
                if profile.name.lower() in company:
                    auto_profile_id = profile.client_id
                    break
                aliases = profile.company_aliases or []
                if isinstance(aliases, str):
                    aliases = [aliases]
                for alias in aliases:
                    if str(alias).lower() in company:
                        auto_profile_id = profile.client_id
                        break
                if auto_profile_id:
                    break

    names_for_area = [
        (sheet.metadata or {}).get("employee") or sheet.sheet_name for sheet in sheets
    ]
    company_name = str((metadata or {}).get("company", ""))
    is_nova = "nova" in company_name.lower()
    if not is_nova and auto_profile_id:
        profile = get_profile_catalog().get(auto_profile_id)
        if profile and "nova" in profile.name.lower():
            is_nova = True

    auto_area = detect_area_from_names(names_for_area) if is_nova else None

    sheet_payload = []
    for sheet in sheets:
        df = to_pandas_table(sheet.dataframe)
        safe_meta = _compact_metadata(sheet.metadata)
        sheet_payload.append(
            {
                "sheet_name": sheet.sheet_name,
                "metadata": safe_meta,
                "columns": [str(c) for c in df.columns],
                "row_count": len(df),
                "header_row": sheet.header_row,
            }
        )

    return sanitize_payload({
        "sheets": sheet_payload,
        "skipped_sheets": skipped,
        "auto_profile_id": auto_profile_id,
        "is_nova": is_nova,
        "auto_area": auto_area,
        "company": company_name,
        "employee_count": len(sheets),
    })


__all__ = ["analyze_individual"]
