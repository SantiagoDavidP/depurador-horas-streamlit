from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from backend.baninter_processor import prepare_baninter_dataframe
from backend.data_cleaner import detect_and_remove_metadata_rows
from backend.excel_parser import ParsedSheet
from backend.models import ColumnMapping
from backend.perf import PerfCollector
from backend.profile_validations import run_profile_validations
from backend.validators import ValidationIssue, run_all_validations, validate_mapping
from backend.infrastructure.storage.azure_blob_storage_adapter import AzureBlobStorageAdapter

from .models import ProcessorResult

logger = logging.getLogger(__name__)


def process_parsed_sheet_impl(
    self,
    *,
    parsed_sheet: ParsedSheet,
    mapping: ColumnMapping,
    source_name: str,
    original_excel_bytes: Optional[bytes] = None,
    correct_spelling: bool = True,
    upload_to_blob: bool = False,
    blob_name_original: Optional[str] = None,
    blob_name_corrected: Optional[str] = None,
    role: str = "Desconocido",
    project_name: str = "No especificado",
    duplicate_similarity_threshold: int = 90,
    duplicate_min_occurrences: int = 3,
    hours_tolerance_factor: float = 1.5,
    client_profile_id: Optional[str] = None,
    client_profile_settings: Optional[Dict[str, Any]] = None,
    batch_fast_mode: bool = False,
    enable_debug_exports: bool = True,
) -> ProcessorResult:
    df = parsed_sheet.dataframe.copy()
    df = self._drop_empty_columns(df)
    perf = PerfCollector()
    t_total = time.perf_counter()
    t_stage = time.perf_counter()

    self._normalize_ticket_columns(df)
    if mapping.date in df.columns:
        df[mapping.date] = pd.to_datetime(
            df[mapping.date],
            errors="coerce"
        ).dt.date

    metadata = dict(getattr(parsed_sheet, "metadata", {}) or {})
    profile_settings = dict(client_profile_settings or {})
    metadata.setdefault("source_name", source_name)
    expected_hours = float(profile_settings.get("horas_esperadas_dia", self.expected_hours))
    row_numbers = self._get_row_numbers(parsed_sheet)
    raw_row_numbers = list(row_numbers)
    logger.info("TIMING: preparar metadata en %.2fs", time.perf_counter() - t_stage)
    t_stage = time.perf_counter()

    is_baninter = self._is_baninter_profile(client_profile_id, metadata)
    baninter_ignore_columns: List[str] = []
    if is_baninter:
        df, baninter_report = prepare_baninter_dataframe(df, mapping)
        metadata["baninter_report"] = baninter_report
        resolved_mapping = baninter_report.get("resolved_mapping") or {}
        mapping = ColumnMapping(
            date=resolved_mapping.get("date", mapping.date),
            hours=resolved_mapping.get("hours", mapping.hours),
            description=resolved_mapping.get("description", mapping.description),
            project=resolved_mapping.get("project", mapping.project),
        )
        for optional_col in (resolved_mapping.get("phase"), resolved_mapping.get("id")):
            if optional_col:
                baninter_ignore_columns.append(optional_col)
    logger.info("TIMING: baninter_preparacion en %.2fs", time.perf_counter() - t_stage)
    t_stage = time.perf_counter()

    filled_grouped_dates = self._fill_grouped_dates_for_payload(
        df,
        date_column=mapping.date,
        hours_column=mapping.hours,
        description_column=mapping.description if mapping.description in df.columns else None,
    )
    if filled_grouped_dates > 0:
        logger.info("Fechas agrupadas imputadas: %d", filled_grouped_dates)

    if mapping.description in df.columns and mapping.hours in df.columns:
        desc_series = df[mapping.description].astype(str).str.strip().str.lower()
        hours_numeric = pd.to_numeric(df[mapping.hours], errors="coerce")
        total_mask = desc_series.eq("total") & hours_numeric.notna()
        df = df.loc[~total_mask].copy()

    if is_baninter:
        validate_mapping(
            df,
            date_col=mapping.date,
            hours_col=mapping.hours,
            description_col=mapping.description,
            minimum_valid_ratio=0.0,
        )
    else:
        validate_mapping(
            df,
            date_col=mapping.date,
            hours_col=mapping.hours,
            description_col=mapping.description,
        )
    logger.info("TIMING: validate_mapping en %.2fs", time.perf_counter() - t_stage)
    t_stage = time.perf_counter()

    df_clean, cleaned_rows, removed_count = detect_and_remove_metadata_rows(
        df,
        date_column=mapping.date,
        hours_column=mapping.hours,
        description_column=mapping.description,
        row_numbers=row_numbers,
        used_range=metadata.get("used_range") if isinstance(metadata, dict) else None,
        perf=perf,
    )
    if cleaned_rows is not None:
        row_numbers = cleaned_rows
    else:
        row_numbers = row_numbers[: len(df_clean)]

    if df_clean.empty:
        logger.warning("No quedan registros tras limpiar metadata.")
    logger.info(
        "Dataset limpio: %d registros validos de %d totales",
        len(df_clean),
        len(df),
    )
    logger.info("TIMING: limpiar_metadata en %.2fs", time.perf_counter() - t_stage)
    t_stage = time.perf_counter()

    ticket_column = next(
        (col for col in df_clean.columns if "ticket" in str(col).lower()), None
    )
    precomputed_validation = {
        "parsed_dates": pd.to_datetime(df_clean[mapping.date], errors="coerce", dayfirst=True),
        "numeric_hours": pd.to_numeric(df_clean[mapping.hours], errors="coerce"),
        "normalized_description": (
            df_clean[mapping.description].fillna("").astype(str).str.lower().str.strip()
            if mapping.description in df_clean.columns
            else pd.Series(index=df_clean.index, dtype="object")
        ),
    }

    debug_hours_df = None
    debug_detail_df = None
    if enable_debug_exports and not batch_fast_mode:
        raw_debug = self._group_hours_debug_df(
            df,
            mapping=mapping,
            row_numbers=raw_row_numbers,
        )
        clean_debug = self._group_hours_debug_df(
            df_clean,
            mapping=mapping,
            row_numbers=row_numbers,
        )
        debug_hours_df = self._merge_hours_debug(
            raw_debug,
            clean_debug,
            expected_hours=expected_hours,
        )

    t_validations = time.perf_counter()
    validation_errors = run_all_validations(
        df_clean,
        date_column=mapping.date,
        hours_column=mapping.hours,
        expected_hours=expected_hours,
        row_numbers=row_numbers,
        description_column=mapping.description,
        project_column=mapping.project,
        ticket_column=ticket_column,
        duplicate_similarity_threshold=duplicate_similarity_threshold,
        duplicate_min_occurrences=duplicate_min_occurrences,
        hours_tolerance_factor=hours_tolerance_factor,
        precomputed=precomputed_validation,
        missing_fields_ignore_columns=baninter_ignore_columns if is_baninter else None,
        duplicate_fuzzy_enabled=not batch_fast_mode,
        perf=perf,
    )
    perf.add("processor.validations_total", time.perf_counter() - t_validations)
    logger.info("TIMING: validaciones en %.2fs", time.perf_counter() - t_stage)
    t_stage = time.perf_counter()
    profile_specific = run_profile_validations(
        client_profile_id,
        df_clean,
        metadata,
        row_numbers,
        profile_settings,
    )
    if profile_specific:
        validation_errors.extend(profile_specific)

    out_of_period_dates = {
        err.get("fecha")
        for err in validation_errors
        if err.get("tipo_error") == "fecha_fuera_periodo" and err.get("fecha")
    }
    if out_of_period_dates:
        validation_errors = [
            err
            for err in validation_errors
            if not (
                err.get("tipo_error") in {"fin_semana", "feriado"}
                and err.get("fecha") in out_of_period_dates
            )
        ]

    if ticket_column:
        validation_errors = self._normalize_ticket_validation_errors(
            validation_errors, df_clean, ticket_column, row_numbers
        )

    self._apply_validation_corrections(df_clean, mapping, row_numbers, validation_errors)
    if not correct_spelling:
        logger.info("LLM desactivado para %s", source_name)
    corrections = self._apply_corrections(
        df_clean,
        mapping=mapping,
        row_numbers=row_numbers,
        enable_llm=correct_spelling,
        role=role,
        project=project_name,
    )
    metadata["llm_enabled"] = bool(correct_spelling)
    metadata["llm_corrections_count"] = len(corrections)

    role_analysis = self._analyze_role(df_clean, mapping, role, row_numbers)

    summary = self._create_summary(
        df_clean,
        validation_errors,
        mapping,
        metadata_removed=removed_count,
    )
    summary.role_coherence_score = role_analysis["score"]
    summary.role_validation_details = role_analysis["details"]

    errors_df = (
        pd.DataFrame(validation_errors)
        if validation_errors
        else pd.DataFrame(columns=list(ValidationIssue.__annotations__.keys()))
    )
    errors_df = self._sort_errors_df(errors_df)
    if enable_debug_exports and not batch_fast_mode:
        debug_detail_df = self._build_hours_debug_detail(
            df=df,
            mapping=mapping,
            row_numbers=raw_row_numbers,
            validation_errors=validation_errors,
            stage_label="RAW",
        )
        debug_detail_clean = self._build_hours_debug_detail(
            df=df_clean,
            mapping=mapping,
            row_numbers=row_numbers,
            validation_errors=validation_errors,
            stage_label="CLEAN",
        )
        if debug_detail_df is not None and debug_detail_clean is not None:
            debug_detail_df = pd.concat([debug_detail_df, debug_detail_clean], ignore_index=True)

    workbook_bytes = self._export_workbook(
        df_clean,
        errors_df,
        summary,
        debug_hours_df=debug_hours_df,
        debug_detail_df=debug_detail_df,
    )
    logger.info("TIMING: export_excel en %.2fs", time.perf_counter() - t_stage)
    output_filename = self._build_output_filename(source_name)

    uploaded_original = None
    uploaded_corrected = None
    if upload_to_blob:
        blob_storage = AzureBlobStorageAdapter()
        if original_excel_bytes and blob_name_original:
            try:
                blob_storage.upload_bytes_to_blob(
                    blob_name_original, original_excel_bytes, overwrite=True
                )
                uploaded_original = blob_name_original
            except Exception as exc:
                logger.exception("Error subiendo archivo original a Blob Storage: %s", exc)
                raise
        if blob_name_corrected:
            try:
                blob_storage.upload_bytes_to_blob(
                    blob_name_corrected, workbook_bytes, overwrite=True
                )
                uploaded_corrected = blob_name_corrected
            except Exception as exc:
                logger.exception("Error subiendo archivo corregido a Blob Storage: %s", exc)
                raise

    for key, value in profile_settings.items():
        metadata.setdefault(key, value)

    corrected_snapshot = df_clean.copy(deep=True)

    perf.add("processor.total", time.perf_counter() - t_total)
    top = perf.top(10)
    if top:
        formatted = ", ".join([f"{name}={duration:.3f}s" for name, duration in top])
        logger.info("PROFILE TOP10: %s", formatted)

    return ProcessorResult(
        workbook_bytes=workbook_bytes,
        output_filename=output_filename,
        validation_errors=validation_errors,
        corrections_log=corrections,
        summary=summary,
        corrected_dataframe=corrected_snapshot,
        errors_dataframe=errors_df,
        uploaded_blob_original=uploaded_original,
        uploaded_blob_corrected=uploaded_corrected,
        metadata=metadata,
        client_profile_id=client_profile_id,
        client_profile_settings=profile_settings,
    )
