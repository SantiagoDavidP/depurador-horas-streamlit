from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from fastapi import Depends, File, Form, HTTPException, UploadFile

from api.serializers import sanitize_payload
from api.services import auto_detect_profile_from_files, get_profile_catalog, is_baninter_result
from backend.batch_processor import BatchFileResult
from backend.consolidator_integration import generate_consolidated_from_batch_results
from backend.excel_parser import infer_column_mapping, load_multiple_sheets
from backend.models import ColumnMapping

from api.presentation.dependencies import (
    auth_provider,
    file_store,
    get_individual_thread_processor,
    processor,
)
from api.presentation.handlers_common import _build_baninter_zip, _serialize_result
from api.presentation.parsing import parse_payload as _parse_payload
from api.presentation.parsing import to_bool as _to_bool


logger = logging.getLogger(__name__)


def process_individual(
    file: UploadFile = File(...),
    payload: Optional[str] = Form(None),
    user: Optional[Dict[str, object]] = Depends(auth_provider.require_user),
) -> Dict[str, object]:
    file_bytes = file.file.read()
    data = _parse_payload(payload)

    settings = data.get("settings") or {}

    area_selection = data.get("areaSelection")
    profile_id = data.get("profileId")

    all_parsed_sheets = load_multiple_sheets(file_bytes)
    filtered_sheets = []
    skipped = []
    for sheet in all_parsed_sheets:
        sheet_name_lower = sheet.sheet_name.lower()
        metadata = sheet.metadata or {}
        is_generic = sheet_name_lower in ["hoja1", "sheet1", "hoja", "sheet", "hoja 1", "sheet 1"]
        has_no_metadata = not metadata.get("company") and not metadata.get("employee")
        if is_generic and has_no_metadata:
            skipped.append(sheet.sheet_name)
            continue
        filtered_sheets.append(sheet)
    all_parsed_sheets = filtered_sheets

    if not all_parsed_sheets:
        raise HTTPException(status_code=400, detail="No valid sheets detected")

    profiles = get_profile_catalog()
    profile_settings = profiles.get(profile_id).settings if profile_id in profiles else {}

    normalized_profile_settings = {
        "correctSpelling": profile_settings.get("correct_spelling", profile_settings.get("correctSpelling")),
        "duplicateSimilarityThreshold": profile_settings.get(
            "duplicate_similarity_threshold", profile_settings.get("duplicateSimilarityThreshold")
        ),
        "duplicateMinOccurrences": profile_settings.get(
            "duplicate_min_occurrences", profile_settings.get("duplicateMinOccurrences")
        ),
        "hoursToleranceFactor": profile_settings.get(
            "hours_tolerance_factor", profile_settings.get("hoursToleranceFactor")
        ),
        "role": profile_settings.get("rol_default", profile_settings.get("role")),
        "horas_esperadas_dia": profile_settings.get("horas_esperadas_dia"),
    }

    effective_settings = {**profile_settings, **normalized_profile_settings, **settings}

    correct_spelling = _to_bool(
        effective_settings.get(
            "correctSpelling",
            effective_settings.get("correct_spelling", True),
        ),
        default=True,
    )
    duplicate_similarity_threshold = int(effective_settings.get("duplicateSimilarityThreshold", 90))
    duplicate_min_occurrences = int(effective_settings.get("duplicateMinOccurrences", 3))
    hours_tolerance_factor = float(effective_settings.get("hoursToleranceFactor", 1.5))
    role = str(effective_settings.get("role", "Consultor"))
    if not profile_id:
        profile_id, _ = auto_detect_profile_from_files(file_bytes, file.filename, list(profiles.values()))
    profile_mapping = {}
    if profile_id and profile_id in profiles:
        profile_mapping = profiles[profile_id].mapping or {}

    processable: List[Tuple[int, object, str, ColumnMapping]] = []
    results_with_index: List[Tuple[int, BatchFileResult, ColumnMapping]] = []
    skipped_sheets: List[Tuple[str, List[str]]] = []

    for idx, sheet in enumerate(all_parsed_sheets):
        sheet_metadata = sheet.metadata or {}
        emp_name = sheet_metadata.get("employee")
        if not emp_name:
            skipped_sheets.append((sheet.sheet_name, [str(c) for c in list(sheet.dataframe.columns)]))
            continue
        if emp_name.lower() in ["hoja1", "sheet1", "empleado", "consultor", "hoja", "sheet"]:
            skipped_sheets.append((sheet.sheet_name, [str(c) for c in list(sheet.dataframe.columns)]))
            continue
        mapping_to_use = infer_column_mapping(sheet.dataframe, profile_mapping)
        if mapping_to_use is None:
            skipped_sheets.append((sheet.sheet_name, [str(c) for c in list(sheet.dataframe.columns)]))
            continue

        processable.append((idx, sheet, emp_name, mapping_to_use))

    def _process_sheet(
        idx: int, sheet: object, emp_name: str, mapping_to_use: ColumnMapping
    ) -> Tuple[int, BatchFileResult, ColumnMapping]:
        sheet_start = time.perf_counter()
        sheet_processor = (
            get_individual_thread_processor() if max_workers > 1 else processor
        )
        logger.info(
            "[individual] Start %s (%d/%d)",
            emp_name,
            idx + 1,
            processable_count if processable_count > 0 else 1,
        )
        try:
            result = sheet_processor.process_parsed_sheet(
                parsed_sheet=sheet,  # type: ignore[arg-type]
                mapping=mapping_to_use,
                source_name=f"{file.filename} :: {emp_name}",
                original_excel_bytes=None,
                correct_spelling=correct_spelling,
                upload_to_blob=False,
                role=role,
                project_name=mapping_to_use.project or "No especificado",
                duplicate_similarity_threshold=duplicate_similarity_threshold,
                duplicate_min_occurrences=duplicate_min_occurrences,
                hours_tolerance_factor=hours_tolerance_factor,
                client_profile_id=profile_id,
                client_profile_settings=effective_settings,
                batch_fast_mode=True,
                enable_debug_exports=False,
            )
            batch_result = BatchFileResult(
                file_name=f"{emp_name}.xlsx",
                success=True,
                result=result,
                sheet_name=emp_name,
                client_id=profile_id or "manual",
                metadata=sheet.metadata if hasattr(sheet, "metadata") else {},
            )
            logger.info(
                "[individual] Done %s in %.2fs",
                emp_name,
                time.perf_counter() - sheet_start,
            )
        except Exception as exc:
            logger.exception("[individual] Failed %s: %s", emp_name, exc)
            batch_result = BatchFileResult(
                file_name=f"{emp_name}.xlsx",
                success=False,
                error=str(exc),
                sheet_name=emp_name,
                client_id=profile_id or "manual",
                metadata=sheet.metadata if hasattr(sheet, "metadata") else {},
            )
        return idx, batch_result, mapping_to_use

    requested_workers = int(data.get("maxWorkers", 4))
    processable_count = len(processable)
    worker_cap = 4 if correct_spelling else 8
    max_workers = max(1, min(requested_workers, processable_count if processable_count > 0 else 1, worker_cap))
    logger.info(
        "[individual] Processing %d consultant(s) with %d worker(s) (IA=%s)",
        processable_count,
        max_workers,
        "on" if correct_spelling else "off",
    )
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_process_sheet, idx, sheet, emp_name, mapping_to_use): idx
            for idx, sheet, emp_name, mapping_to_use in processable
        }
        for future in as_completed(future_map):
            results_with_index.append(future.result())

    results_with_index.sort(key=lambda item: item[0])
    batch_results = [item[1] for item in results_with_index]
    mappings = [item[2] for item in results_with_index]

    if not batch_results:
        raise HTTPException(status_code=400, detail="No valid timesheet sheets detected")

    batch_id = file_store.store_batch(batch_results, source="individual")

    is_nova = False
    first_meta = (all_parsed_sheets[0].metadata or {}) if all_parsed_sheets else {}
    company_name = str(first_meta.get("company", ""))
    if "nova" in company_name.lower():
        is_nova = True
    if not is_nova and profile_id:
        profile = profiles.get(profile_id)
        if profile and "nova" in profile.name.lower():
            is_nova = True

    cliente_nombre = company_name or "Cliente"
    if is_nova:
        if area_selection == "NOVA - TI (BIT Nova)":
            cliente_nombre = "BIT Nova - TI"
        elif area_selection == "NOVA - Centro Digital":
            cliente_nombre = "NOVA - Centro Digital"
        elif area_selection:
            cliente_nombre = str(area_selection)

    consolidated = generate_consolidated_from_batch_results(
        batch_results=batch_results,
        cliente=cliente_nombre,
        output_filename=f"Consolidado_{cliente_nombre.replace(' ', '_')}_{len(batch_results)}_Consultores.xlsx",
    )
    consolidated_download_id = file_store.store_file(
        consolidated.workbook_bytes,
        consolidated.output_filename,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    results_payload = []
    for item, mapping in zip(batch_results, mappings):
        results_payload.append(
            _serialize_result(
                item,
                mapping=mapping,
                source_filename=file.filename or item.file_name,
            )
        )

    # BANINTER zip (si aplica)
    baninter_zip = None
    is_baninter_batch = any(
        is_baninter_result(r.file_name, r.metadata, r.client_id) for r in batch_results
    )
    if is_baninter_batch:
        try:
            zip_bytes = _build_baninter_zip(batch_results)
            if zip_bytes:
                baninter_zip_id = file_store.store_file(zip_bytes, "BANINTER_Individuales_BusinessIT.zip", "application/zip")
                baninter_zip = {"download_id": baninter_zip_id, "filename": "BANINTER_Individuales_BusinessIT.zip"}
        except Exception:
            baninter_zip = None

    skipped_payload = [
        {"name": name, "columns": cols} for name, cols in skipped_sheets
    ]

    return sanitize_payload({
        "batch_id": batch_id,
        "results": results_payload,
        "skipped_sheets": skipped_payload,
        "consolidated": {
            "download_id": consolidated_download_id,
            "filename": consolidated.output_filename,
            "consultores": consolidated.consultores_incluidos,
            "total_horas": consolidated.total_horas,
        },
        "baninter_zip": baninter_zip,
    })


__all__ = ["process_individual"]
