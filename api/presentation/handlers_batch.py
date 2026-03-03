from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

from fastapi import Depends, File, Form, HTTPException, UploadFile

from api.serializers import sanitize_payload
from api.services import (
    auto_detect_profile_from_files,
    build_default_output_filename,
    build_mapping_from_values,
    detect_area_from_names,
    get_profile_catalog,
    infer_client_name_from_results,
    is_baninter_result,
)
from backend.application.batch.batch_processor import BatchFileRequest
from backend.domain.profiles.client_profiles import ClientProfile
from backend.application.consolidation.consolidator_integration import (
    generate_consolidated_from_batch_results,
    validate_batch_results_for_consolidation,
)
from backend.domain.parsing.excel_parser import infer_column_mapping, load_sheet_with_header
from backend.domain.models import ColumnMapping

from api.presentation.dependencies import auth_provider, batch_processor, file_store
from api.presentation.handlers_common import (
    _build_baninter_zip,
    _infer_client_id_for_file,
    _serialize_result,
)
from api.presentation.parsing import compact_metadata as _compact_metadata
from api.presentation.parsing import parse_payload as _parse_payload
from api.presentation.parsing import to_bool as _to_bool


def analyze_batch(
    files: List[UploadFile] = File(...),
    user: Optional[Dict[str, object]] = Depends(auth_provider.require_user),
) -> Dict[str, object]:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    file = files[0]
    file_bytes = file.file.read()
    profiles = list(get_profile_catalog().values())
    profile_id, metadata = auto_detect_profile_from_files(file_bytes, file.filename, profiles)
    safe_meta = _compact_metadata(metadata)

    profile_mapping = {}
    profile_settings = {}
    if profile_id:
        catalog = get_profile_catalog()
        profile = catalog.get(profile_id)
        if profile:
            profile_mapping = profile.mapping
            profile_settings = profile.settings

    return sanitize_payload({
        "auto_profile_id": profile_id,
        "profile_mapping": profile_mapping,
        "profile_settings": profile_settings,
        "metadata": safe_meta,
    })


def process_batch(
    files: List[UploadFile] = File(...),
    payload: Optional[str] = Form(None),
    user: Optional[Dict[str, object]] = Depends(auth_provider.require_user),
) -> Dict[str, object]:
    data = _parse_payload(payload)
    profile_id = data.get("profileId")
    mapping_values = data.get("mappingValues") or {}
    settings = data.get("settings") or {}
    max_workers = int(data.get("maxWorkers", 4))

    correct_spelling = _to_bool(
        settings.get("correctSpelling", settings.get("correct_spelling")),
        default=True,
    )
    duplicate_similarity_threshold = int(settings.get("duplicateSimilarityThreshold", 90))
    duplicate_min_occurrences = int(settings.get("duplicateMinOccurrences", 3))
    hours_tolerance_factor = float(settings.get("hoursToleranceFactor", 1.5))
    role = str(settings.get("role", "Consultor"))

    profiles_catalog = get_profile_catalog()
    profile_obj: Optional[ClientProfile] = profiles_catalog.get(profile_id) if profile_id else None

    if profile_obj is None:
        base_mapping = build_mapping_from_values(mapping_values)
        if base_mapping is None:
            raise HTTPException(status_code=400, detail="Missing required mapping")
        profile_settings = {}
        header_keywords = [v for v in mapping_values.values() if v]
    else:
        base_mapping = profile_obj.to_column_mapping()
        if base_mapping is None:
            raise HTTPException(status_code=400, detail="Profile missing required mapping")
        profile_settings = profile_obj.settings or {}
        header_keywords = [v for v in profile_obj.mapping.values() if v]

    duplicate_threshold = int(profile_settings.get("duplicate_similarity_threshold", duplicate_similarity_threshold))
    min_duplicates_setting = int(profile_settings.get("duplicate_min_occurrences", duplicate_min_occurrences))
    hours_tolerance = float(profile_settings.get("hours_tolerance_factor", hours_tolerance_factor))
    role_to_use = str(profile_settings.get("rol_default") or profile_settings.get("role") or role)
    # Respetar el toggle del usuario; si no viene, usar configuración del perfil o default.
    spelling_flag = _to_bool(
        settings.get("correctSpelling", settings.get("correct_spelling")),
        default=_to_bool(profile_settings.get("correct_spelling"), default=correct_spelling),
    )

    file_payloads: List[Tuple[str, bytes]] = []
    for file_obj in files:
        file_payloads.append((file_obj.filename or "reporte.xlsx", file_obj.file.read()))

    profile_mapping = profile_obj.mapping if profile_obj else {}

    def _prepare_batch_request(file_payload: Tuple[str, bytes]) -> Tuple[BatchFileRequest, ColumnMapping]:
        file_name, file_bytes = file_payload
        parsed = load_sheet_with_header(
            file_bytes,
            header_keywords=header_keywords,
        )

        effective_client_id = _infer_client_id_for_file(
            file_name, getattr(parsed, "metadata", {}) or {}, profile_id
        )

        dynamic_mapping = infer_column_mapping(
            parsed.dataframe,
            profile_mapping,
        )
        mapping_to_use = dynamic_mapping or base_mapping

        request = BatchFileRequest(
            file_name=file_name,
            file_bytes=file_bytes,
            mapping=mapping_to_use,
            client_id=effective_client_id,
            header_keywords=header_keywords,
            profile_settings=profile_settings,
            parsed_sheet=parsed,
            processor_kwargs={
                "correct_spelling": spelling_flag,
                "role": role_to_use,
                "project_name": mapping_to_use.project or "No especificado",
                "duplicate_similarity_threshold": duplicate_threshold,
                "duplicate_min_occurrences": min_duplicates_setting,
                "hours_tolerance_factor": hours_tolerance,
                "batch_fast_mode": True,
                "enable_debug_exports": False,
            },
        )
        return request, mapping_to_use

    prep_workers = max(1, min(max_workers, len(file_payloads)))
    if prep_workers == 1:
        prepared_items = [_prepare_batch_request(item) for item in file_payloads]
    else:
        with ThreadPoolExecutor(max_workers=prep_workers) as executor:
            prepared_items = list(executor.map(_prepare_batch_request, file_payloads))

    requests = [item[0] for item in prepared_items]
    mappings = [item[1] for item in prepared_items]

    results = batch_processor.process_batch(requests, max_workers=max_workers)
    batch_id = file_store.store_batch(results, source="batch")

    results_payload = []
    for item, mapping in zip(results, mappings):
        results_payload.append(
            _serialize_result(
                item,
                mapping=mapping,
                source_filename=item.file_name,
            )
        )

    is_baninter_batch = any(
        is_baninter_result(r.file_name, r.metadata, r.client_id) for r in results if r.success
    )

    profiles = get_profile_catalog()
    default_client_name = infer_client_name_from_results(results, profiles)
    names_for_area = [
        (r.metadata or {}).get("employee") or (r.metadata or {}).get("empleado") or r.file_name
        for r in results
        if r.success
    ]
    is_nova = "nova" in str(default_client_name).lower()
    auto_area = detect_area_from_names(names_for_area) if is_nova else None

    return sanitize_payload({
        "batch_id": batch_id,
        "results": results_payload,
        "is_baninter": is_baninter_batch,
        "default_client_name": default_client_name,
        "auto_area": auto_area,
    })


def consolidate_batch(
    payload: Dict[str, object],
    user: Optional[Dict[str, object]] = Depends(auth_provider.require_user),
) -> Dict[str, object]:
    batch_id = payload.get("batchId")
    if not batch_id:
        raise HTTPException(status_code=400, detail="batchId required")
    stored = file_store.get_batch(str(batch_id))
    if not stored:
        raise HTTPException(status_code=404, detail="Batch not found")

    results = stored.results
    profiles = get_profile_catalog()
    default_client_name = infer_client_name_from_results(results, profiles)

    cliente_nombre = payload.get("clientName") or default_client_name
    output_filename = payload.get("outputFilename") or build_default_output_filename(
        default_client_name, results
    )

    is_valid, warnings = validate_batch_results_for_consolidation(list(results))
    if not is_valid:
        raise HTTPException(status_code=400, detail="Batch results not valid for consolidation")

    consolidated = generate_consolidated_from_batch_results(
        batch_results=list(results),
        cliente=str(cliente_nombre),
        output_filename=str(output_filename),
    )

    download_id = file_store.store_file(
        consolidated.workbook_bytes,
        consolidated.output_filename,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    return sanitize_payload({
        "download_id": download_id,
        "filename": consolidated.output_filename,
        "consultores": consolidated.consultores_incluidos,
        "total_horas": consolidated.total_horas,
        "warnings": warnings,
    })


def baninter_zip(
    payload: Dict[str, object],
    user: Optional[Dict[str, object]] = Depends(auth_provider.require_user),
) -> Dict[str, object]:
    batch_id = payload.get("batchId")
    if not batch_id:
        raise HTTPException(status_code=400, detail="batchId required")
    stored = file_store.get_batch(str(batch_id))
    if not stored:
        raise HTTPException(status_code=404, detail="Batch not found")

    zip_bytes = _build_baninter_zip(list(stored.results))
    if not zip_bytes:
        raise HTTPException(status_code=400, detail="No BANINTER results available")

    download_id = file_store.store_file(zip_bytes, "BANINTER_Individuales_BusinessIT.zip", "application/zip")
    return sanitize_payload({"download_id": download_id, "filename": "BANINTER_Individuales_BusinessIT.zip"})


__all__ = ["analyze_batch", "process_batch", "consolidate_batch", "baninter_zip"]
