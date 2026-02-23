from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from api.auth import require_user
from api.serializers import (
    build_holiday_info,
    dataframe_to_records,
    sanitize_payload,
    sort_errors_dataframe,
    summary_to_dict,
)
from api.services import (
    auto_detect_profile_from_files,
    build_default_output_filename,
    build_mapping_from_values,
    detect_area_from_names,
    get_profile_catalog,
    infer_client_name_from_results,
    is_baninter_result,
    resolve_employee,
)
from api.storage import get_batch, get_file, store_batch, store_file
from backend.batch_processor import BatchFileRequest, BatchFileResult, BatchProcessor
from backend.client_profiles import ClientProfile
from backend.consolidator_integration import (
    generate_consolidated_from_batch_results,
    generate_individual_business_it_excel,
    validate_batch_results_for_consolidation,
)
from backend.excel_parser import infer_column_mapping, load_multiple_sheets, load_sheet_with_header
from backend.models import ColumnMapping
from backend.processor import TimeSheetProcessor

logger = logging.getLogger(__name__)

app = FastAPI(title="Nova Timesheet API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

processor = TimeSheetProcessor()
batch_processor = BatchProcessor(processor)


def _parse_payload(payload: Optional[str]) -> Dict[str, object]:
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc


_SAFE_META_KEYS = (
    "company",
    "employee",
    "empleado",
    "period_start",
    "period_end",
    "month_name",
    "year",
    "report_date",
    "period_source",
    "metadata_warning",
    "baninter_report",
)


def _compact_metadata(raw_meta: Optional[Dict[str, object]]) -> Dict[str, object]:
    meta = raw_meta or {}
    compact = {key: meta.get(key) for key in _SAFE_META_KEYS if key in meta}
    return sanitize_payload(compact)


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

    download_id = store_file(
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
        }
    )

    if is_baninter_result(result.file_name, result.metadata, result.client_id):
        try:
            business_bytes, business_name = generate_individual_business_it_excel(
                result, cliente="BANINTER"
            )
            business_id = store_file(
                business_bytes,
                business_name,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            base["baninter_business_id"] = business_id
            base["baninter_business_filename"] = business_name
        except Exception:
            pass
    return base


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/profiles")
def list_profiles(user: Optional[Dict[str, object]] = Depends(require_user)) -> Dict[str, object]:
    profiles = get_profile_catalog()
    payload = []
    for profile in profiles.values():
        payload.append(
            {
                "client_id": profile.client_id,
                "name": profile.name,
                "mapping": profile.mapping,
                "settings": profile.settings,
                "keywords": profile.keywords,
                "company_aliases": profile.company_aliases,
            }
        )
    return sanitize_payload({"profiles": payload})


@app.get("/api/me")
def get_me(user: Optional[Dict[str, object]] = Depends(require_user)) -> Dict[str, object]:
    return sanitize_payload({"user": user})


@app.post("/api/batch/analyze")
async def analyze_batch(
    files: List[UploadFile] = File(...),
    user: Optional[Dict[str, object]] = Depends(require_user),
) -> Dict[str, object]:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    file = files[0]
    file_bytes = await file.read()
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


@app.post("/api/individual/analyze")
async def analyze_individual(
    file: UploadFile = File(...),
    user: Optional[Dict[str, object]] = Depends(require_user),
) -> Dict[str, object]:
    file_bytes = await file.read()
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
        df = sheet.dataframe
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


@app.post("/api/individual/process")
async def process_individual(
    file: UploadFile = File(...),
    payload: Optional[str] = Form(None),
    user: Optional[Dict[str, object]] = Depends(require_user),
) -> Dict[str, object]:
    file_bytes = await file.read()
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

    correct_spelling = bool(effective_settings.get("correctSpelling", True))
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
        try:
            result = processor.process_parsed_sheet(
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
        except Exception as exc:
            batch_result = BatchFileResult(
                file_name=f"{emp_name}.xlsx",
                success=False,
                error=str(exc),
                sheet_name=emp_name,
                client_id=profile_id or "manual",
                metadata=sheet.metadata if hasattr(sheet, "metadata") else {},
            )
        return idx, batch_result, mapping_to_use

    max_workers = int(data.get("maxWorkers", 4))
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

    batch_id = store_batch(batch_results, source="individual")

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
    consolidated_download_id = store_file(
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
                baninter_zip_id = store_file(zip_bytes, "BANINTER_Individuales_BusinessIT.zip", "application/zip")
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
            business_bytes, business_name = generate_individual_business_it_excel(
                res, cliente="BANINTER"
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


@app.post("/api/batch/process")
async def process_batch(
    files: List[UploadFile] = File(...),
    payload: Optional[str] = Form(None),
    user: Optional[Dict[str, object]] = Depends(require_user),
) -> Dict[str, object]:
    data = _parse_payload(payload)
    profile_id = data.get("profileId")
    mapping_values = data.get("mappingValues") or {}
    settings = data.get("settings") or {}
    max_workers = int(data.get("maxWorkers", 4))

    correct_spelling = bool(settings.get("correctSpelling", True))
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
    spelling_flag = bool(settings.get("correctSpelling", profile_settings.get("correct_spelling", correct_spelling)))

    requests: List[BatchFileRequest] = []
    mappings: List[ColumnMapping] = []
    for file_obj in files:
        file_bytes = await file_obj.read()
        parsed = load_sheet_with_header(
            file_bytes,
            header_keywords=header_keywords,
        )

        effective_client_id = _infer_client_id_for_file(
            file_obj.filename, getattr(parsed, "metadata", {}) or {}, profile_id
        )

        dynamic_mapping = infer_column_mapping(
            parsed.dataframe,
            profile_obj.mapping if profile_obj else {},
        )

        mapping_to_use = dynamic_mapping or base_mapping
        mappings.append(mapping_to_use)

        requests.append(
            BatchFileRequest(
                file_name=file_obj.filename or "reporte.xlsx",
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
        )

    results = batch_processor.process_batch(requests, max_workers=max_workers)
    batch_id = store_batch(results, source="batch")

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


@app.post("/api/batch/consolidate")
def consolidate_batch(
    payload: Dict[str, object],
    user: Optional[Dict[str, object]] = Depends(require_user),
) -> Dict[str, object]:
    batch_id = payload.get("batchId")
    if not batch_id:
        raise HTTPException(status_code=400, detail="batchId required")
    stored = get_batch(str(batch_id))
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

    download_id = store_file(
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


@app.post("/api/batch/baninter-zip")
def baninter_zip(
    payload: Dict[str, object],
    user: Optional[Dict[str, object]] = Depends(require_user),
) -> Dict[str, object]:
    batch_id = payload.get("batchId")
    if not batch_id:
        raise HTTPException(status_code=400, detail="batchId required")
    stored = get_batch(str(batch_id))
    if not stored:
        raise HTTPException(status_code=404, detail="Batch not found")

    zip_bytes = _build_baninter_zip(list(stored.results))
    if not zip_bytes:
        raise HTTPException(status_code=400, detail="No BANINTER results available")

    download_id = store_file(zip_bytes, "BANINTER_Individuales_BusinessIT.zip", "application/zip")
    return sanitize_payload({"download_id": download_id, "filename": "BANINTER_Individuales_BusinessIT.zip"})


@app.get("/api/download/{file_id}")
def download(file_id: str, user: Optional[Dict[str, object]] = Depends(require_user)) -> Response:
    stored = get_file(file_id)
    if not stored:
        raise HTTPException(status_code=404, detail="File not found")
    headers = {"Content-Disposition": f"attachment; filename={stored.filename}"}
    return Response(content=stored.data, media_type=stored.content_type, headers=headers)


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
