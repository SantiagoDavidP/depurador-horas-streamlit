from __future__ import annotations
from collections import Counter

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd
from openpyxl.styles import Font, PatternFill
from backend.models import ColumnMapping
from backend import azure_storage
from backend.ai_insights import generate_ai_summary_sync
from backend.data_cleaner import detect_and_remove_metadata_rows
from backend.excel_parser import ParsedSheet
from backend.llm_corrector import CorrectionResult, LLMCorrector
from backend.role_validator import RoleActivityValidator
from backend.profile_validations import run_profile_validations
from backend.validators import (
    ValidationIssue,
    run_all_validations,
    validate_mapping,
)

logger = logging.getLogger(__name__)

_CRITICAL_ERROR_TYPES = {
    "fecha_invalida",
    "fin_semana",
    "feriado",
    "horas_incorrectas",
    "horas_excesivas",
    "horas_muy_bajas",
}
_WARNING_ERROR_TYPES = {
    "descripcion_calidad",
    "descripcion_repetida",
    "duplicado_exacto",
    "duplicado_similar",
    "proyecto_inconsistente",
}


@dataclass(frozen=True)
class ColumnMapping:
    """Relación entre columnas del Excel y campos lógicos."""

    date: str
    hours: str
    description: str
    project: Optional[str] = None


@dataclass
class ProcessorSummary:
    total_registros: int
    total_errores: int
    horas_totales: float
    dias_con_problemas_horas: int
    errores_por_tipo: Dict[str, int]
    metadata_removidas: int = 0
    errores_criticos: int = 0
    errores_advertencia: int = 0
    quality_score: float = 0.0
    ai_summary: Optional[Dict[str, Any]] = None
    role_coherence_score: Optional[float] = None
    role_validation_details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ProcessorResult:
    """Resultado completo del procesamiento de un archivo."""

    workbook_bytes: bytes
    output_filename: str
    validation_errors: List[ValidationIssue]
    corrections_log: List[CorrectionResult]
    summary: ProcessorSummary
    corrected_dataframe: pd.DataFrame
    errors_dataframe: pd.DataFrame
    uploaded_blob_original: Optional[str] = None
    uploaded_blob_corrected: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    client_profile_id: Optional[str] = None
    client_profile_settings: Dict[str, Any] = field(default_factory=dict)


class TimeSheetProcessor:
    """Orquesta validaciones, limpieza, correcciones LLM y reportes."""

    def __init__(
        self,
        *,
        expected_hours_per_day: float = 8.0,
        llm_corrector: Optional[LLMCorrector] = None,
        role_validator: Optional[RoleActivityValidator] = None,
    ) -> None:
        self.expected_hours = expected_hours_per_day
        self.llm_corrector = llm_corrector or LLMCorrector(batch_size=20)
        self.role_validator = role_validator or self._load_role_validator()

    @staticmethod
    def _load_role_validator() -> Optional[RoleActivityValidator]:
        taxonomy_path = (
            Path(__file__).resolve().parent.parent / "config" / "role_taxonomy.json"
        )
        if not taxonomy_path.exists():
            logger.warning("No se encontró role_taxonomy.json, se omite validación de rol.")
            return None
        try:
            return RoleActivityValidator.from_json(taxonomy_path)
        except Exception as exc:
            logger.warning("No se pudo cargar la taxonomía de roles: %s", exc)
            return None

    def _analyze_role(
        self,
        df: pd.DataFrame,
        mapping: ColumnMapping,
        declared_role: str,
        row_numbers: Sequence[int],
    ) -> Dict[str, Any]:
        if not declared_role or declared_role in {"Desconocido", "Otro"}:
            return {"score": None, "details": []}
        if self.role_validator is None:
            return {"score": None, "details": []}

        descriptions = df[mapping.description].fillna("").astype(str).tolist()
        results = self.role_validator.batch_validate(descriptions, declared_role)

        total = 0
        valid = 0
        details: List[Dict[str, Any]] = []
        for idx, (desc, result) in enumerate(zip(descriptions, results)):
            if not desc.strip():
                continue
            total += 1
            if result.is_valid:
                valid += 1
            details.append(
                {
                    "fila": row_numbers[idx],
                    "actividad": desc,
                    "rol_detectado": result.rol_detectado,
                    "es_coherente": result.is_valid,
                    "confianza": round(result.confidence_score, 2),
                    "razon": result.reasoning,
                }
            )

        score = (valid / total * 100.0) if total else None
        return {"score": score, "details": details}

    @staticmethod
    def _build_output_filename(source_name: str) -> str:
        stem, ext = os.path.splitext(source_name or "reporte.xlsx")
        ext = ext or ".xlsx"
        return f"{stem}_CORREGIDO{ext}"

    @staticmethod
    def _get_row_numbers(parsed_sheet: ParsedSheet) -> List[int]:
        row_numbers = parsed_sheet.dataframe.attrs.get("original_row_numbers")
        if isinstance(row_numbers, Sequence):
            return list(map(int, row_numbers))
        start = parsed_sheet.header_row + 2
        return [start + idx for idx in range(len(parsed_sheet.dataframe))]

    def _apply_corrections(
        self,
        df: pd.DataFrame,
        mapping: ColumnMapping,
        row_numbers: Sequence[int],
        enable_llm: bool,
        *,
        role: str,
        project: str,
    ) -> List[CorrectionResult]:
        if not enable_llm or mapping.description not in df.columns:
            return []

        texts = df[mapping.description].fillna("").astype(str)
        payload = [
            (row_numbers[idx], value) for idx, value in enumerate(texts) if value.strip()
        ]
        if not payload:
            return []

        corrections = self.llm_corrector.correct_descriptions(
            payload,
            role=role,
            project=project,
        )
        row_lookup = {row_numbers[idx]: idx for idx in range(len(row_numbers))}
        for correction in corrections:
            row_idx = row_lookup.get(correction.fila)
            if row_idx is not None:
                df.at[row_idx, mapping.description] = correction.corrected_text
        return corrections

    def _create_summary(
        self,
        df: pd.DataFrame,
        errors: List[ValidationIssue],
        mapping: ColumnMapping,
        metadata_removed: int,
    ) -> ProcessorSummary:
        errors_df = (
            pd.DataFrame(errors)
            if errors
            else pd.DataFrame(columns=list(ValidationIssue.__annotations__.keys()))
        )
        horas_series = pd.to_numeric(df[mapping.hours], errors="coerce")
        horas_totales = float(horas_series.fillna(0).sum())

        dias_con_problemas = 0
        if not errors_df.empty:
            dias_con_problemas = (
                errors_df.loc[errors_df["tipo_error"] == "horas_incorrectas", "fecha"]
                .dropna()
                .nunique()
            )

        # ============================
        # NUEVA LÓGICA DE SCORING (INDIVIDUAL)
        # ============================
        critical_count = sum(
            1 for err in errors if err["tipo_error"] in _CRITICAL_ERROR_TYPES
        )

        warning_types = [
            err["tipo_error"] for err in errors
            if err["tipo_error"] in _WARNING_ERROR_TYPES
        ]

        counter = Counter(warning_types)

        penalty = 0


        if any(e["tipo_error"] == "completitud" for e in errors):
            penalty += 20
            logger.info("📉 Penalización por días faltantes aplicada (-20 puntos)")

        # 🔴 Errores críticos: SIEMPRE estrictos
        penalty += critical_count * 10

        # 🧠 Duplicidad: penalizar POR PATRÓN, no por fila
        if counter.get("duplicado_exacto", 0) > 0:
            penalty += 10   # copy-paste fuerte

        if counter.get("duplicado_similar", 0) > 0:
            penalty += 6

        if counter.get("descripcion_repetida", 0) > 0:
            penalty += 6

        # ✍️ Calidad de descripción: leve y progresivo
        penalty += min(counter.get("descripcion_calidad", 0), 10)

        # 📦 Otros warnings
        penalty += counter.get("proyecto_inconsistente", 0) * 2

        quality_score = max(0.0, min(100.0, 100.0 - penalty))

        warning_count = sum(counter.values())


        return ProcessorSummary(
            total_registros=len(df),
            total_errores=len(errors),
            horas_totales=horas_totales,
            dias_con_problemas_horas=dias_con_problemas,
            errores_por_tipo=(
                errors_df["tipo_error"].value_counts().astype(int).to_dict()
                if not errors_df.empty
                else {}
            ),
            metadata_removidas=metadata_removed,
            errores_criticos=critical_count,
            errores_advertencia=warning_count,
            quality_score=quality_score,
        )

    def _create_executive_summary_sheet(
        self,
        workbook,
        summary: ProcessorSummary,
    ) -> None:
        if workbook.sheetnames:
            ws = workbook[workbook.sheetnames[0]]
            ws.title = "Resumen Ejecutivo"
            ws.delete_rows(1, ws.max_row)
        else:
            ws = workbook.create_sheet("Resumen Ejecutivo", 0)

        header_font = Font(size=14, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
        success_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
        danger_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")

        ws["A1"] = "Reporte de Validación de Timesheet"
        ws["A1"].font = Font(size=18, bold=True, color="1E3A8A")
        ws.merge_cells("A1:E1")

        ws["A2"] = f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ws.merge_cells("A2:E2")

        row = 4
        ws[f"A{row}"] = "Métricas clave"
        ws[f"A{row}"].font = header_font
        ws[f"A{row}"].fill = header_fill
        ws.merge_cells(f"A{row}:E{row}")
        row += 1

        metrics = [
            (
                "Score de Calidad",
                f"{summary.quality_score:.0f}/100",
                "🟢 Excelente" if summary.quality_score >= 90 else
                "🟡 Bueno" if summary.quality_score >= 70 else
                "🔴 Atención",
            ),
            ("Registros procesados", summary.total_registros, f"{summary.metadata_removidas} metadata removidas"),
            ("Horas totales", f"{summary.horas_totales:.1f}h", f"{summary.horas_totales / 8:.1f} días"),
            ("Errores críticos", summary.errores_criticos, "Bloquean aprobación" if summary.errores_criticos else "Ninguno"),
        ]

        for label, value, detail in metrics:
            ws[f"A{row}"] = label
            ws[f"A{row}"].font = Font(bold=True)
            ws[f"B{row}"] = value
            ws[f"C{row}"] = detail
            row += 1

        row += 1
        ws[f"A{row}"] = "Distribución de errores"
        ws[f"A{row}"].font = header_font
        ws[f"A{row}"].fill = header_fill
        ws.merge_cells(f"A{row}:C{row}")
        row += 1

        ws[f"A{row}"] = "Tipo de error"
        ws[f"B{row}"] = "Cantidad"
        ws[f"C{row}"] = "Severidad"
        for col in ("A", "B", "C"):
            ws[f"{col}{row}"].font = Font(bold=True)
            ws[f"{col}{row}"].fill = PatternFill(start_color="E5E7EB", end_color="E5E7EB", fill_type="solid")
        row += 1

        if summary.errores_por_tipo:
            for tipo, cantidad in summary.errores_por_tipo.items():
                ws[f"A{row}"] = tipo.replace("_", " ").title()
                ws[f"B{row}"] = cantidad
                ws[f"C{row}"] = "Crítico" if tipo in _CRITICAL_ERROR_TYPES else "Advertencia"
                row += 1
        else:
            ws[f"A{row}"] = "Sin errores registrados"
            ws.merge_cells(f"A{row}:C{row}")
            row += 1

        row += 1
        ws[f"A{row}"] = "Decisión"
        ws[f"A{row}"].font = header_font
        ws[f"A{row}"].fill = header_fill
        ws.merge_cells(f"A{row}:C{row}")
        row += 1

        ws[f"A{row}"] = (
            "✅ Timesheet aprobable" if summary.errores_criticos == 0 else
            f"🚫 Requiere {summary.errores_criticos} correcciones críticas"
        )
        ws[f"A{row}"].font = Font(size=14, bold=True, color="047857" if summary.errores_criticos == 0 else "991B1B")
        ws[f"A{row}"].fill = success_fill if summary.errores_criticos == 0 else danger_fill
        ws.merge_cells(f"A{row}:C{row}")
        row += 2

        if summary.ai_summary:
            ws[f"A{row}"] = "Análisis inteligente"
            ws[f"A{row}"].font = header_font
            ws[f"A{row}"].fill = PatternFill(start_color="059669", end_color="059669", fill_type="solid")
            ws.merge_cells(f"A{row}:C{row}")
            row += 1

            ws[f"A{row}"] = "Diagnóstico:"
            ws[f"A{row}"].font = Font(bold=True)
            ws[f"B{row}"] = summary.ai_summary.get("diagnostico", "")
            ws.merge_cells(f"B{row}:C{row}")
            row += 1

            acciones = summary.ai_summary.get("acciones") or []
            if acciones:
                ws[f"A{row}"] = "Acciones recomendadas:"
                ws[f"A{row}"].font = Font(bold=True)
                row += 1
                for idx, accion in enumerate(acciones, 1):
                    ws[f"A{row}"] = f"{idx}. {accion}"
                    ws.merge_cells(f"A{row}:C{row}")
                    row += 1

            tiempo = summary.ai_summary.get("tiempo_estimado")
            if tiempo:
                ws[f"A{row}"] = "Tiempo estimado:"
                ws[f"A{row}"].font = Font(bold=True)
                ws[f"B{row}"] = tiempo
                ws.merge_cells(f"B{row}:C{row}")

        ws.column_dimensions["A"].width = 40
        ws.column_dimensions["B"].width = 25
        ws.column_dimensions["C"].width = 30

    def _export_workbook(
        self,
        corrected_df: pd.DataFrame,
        errors_df: pd.DataFrame,
        summary: ProcessorSummary,
    ) -> bytes:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            workbook = writer.book
            self._create_executive_summary_sheet(workbook, summary)
            corrected_df.to_excel(writer, index=False, sheet_name="Datos Corregidos")
            errors_df.to_excel(writer, index=False, sheet_name="Reporte de Errores")
        buffer.seek(0)
        return buffer.getvalue()

    def process_parsed_sheet(
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
    ) -> ProcessorResult:
        df = parsed_sheet.dataframe.copy()
        # 🧹 Normalizar columna de fecha (quitar hora)
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

        # Completar fechas agrupadas (celdas vacías) antes de validar el mapeo
        if mapping.date in df.columns:
            df[mapping.date] = df[mapping.date].ffill()

        # Remover filas de totales que se vuelven "válidas" tras ffill (evita falsos positivos)
        if mapping.description in df.columns and mapping.hours in df.columns:
            desc_series = df[mapping.description].astype(str).str.strip().str.lower()
            hours_numeric = pd.to_numeric(df[mapping.hours], errors="coerce")
            total_mask = desc_series.eq("total") & hours_numeric.notna()
            df = df.loc[~total_mask].copy()

        validate_mapping(
            df,
            date_col=mapping.date,
            hours_col=mapping.hours,
            description_col=mapping.description,
        )

        df_clean, cleaned_rows, removed_count = detect_and_remove_metadata_rows(
            df,
            date_column=mapping.date,
            hours_column=mapping.hours,
            description_column=mapping.description,
            row_numbers=row_numbers,
        )
        if cleaned_rows is not None:
            row_numbers = cleaned_rows
        else:
            row_numbers = row_numbers[: len(df_clean)]

        if df_clean.empty:
            logger.warning("No quedan registros tras limpiar metadata.")
        logger.info(
            "Dataset limpio: %d registros válidos de %d totales",
            len(df_clean),
            len(df),
        )

        validation_errors = run_all_validations(
            df_clean,
            date_column=mapping.date,
            hours_column=mapping.hours,
            expected_hours=expected_hours,
            row_numbers=row_numbers,
            description_column=mapping.description,
            project_column=mapping.project,
            duplicate_similarity_threshold=duplicate_similarity_threshold,
            duplicate_min_occurrences=duplicate_min_occurrences,
            hours_tolerance_factor=hours_tolerance_factor,
        )
        profile_specific = run_profile_validations(
            client_profile_id,
            df_clean,
            metadata,
            row_numbers,
            profile_settings,
        )
        if profile_specific:
            validation_errors.extend(profile_specific)

        self._apply_validation_corrections(df_clean, mapping, row_numbers, validation_errors)
        corrections = self._apply_corrections(
            df_clean,
            mapping=mapping,
            row_numbers=row_numbers,
            enable_llm=correct_spelling,
            role=role,
            project=project_name,
        )

        role_analysis = self._analyze_role(df_clean, mapping, role, row_numbers)

        summary = self._create_summary(
            df_clean,
            validation_errors,
            mapping,
            metadata_removed=removed_count,
        )
        summary.role_coherence_score = role_analysis["score"]
        summary.role_validation_details = role_analysis["details"]

        if summary.total_registros > 0:
            try:
                summary.ai_summary = generate_ai_summary_sync(
                    total_records=summary.total_registros,
                    critical_errors=summary.errores_criticos,
                    warnings=summary.errores_advertencia,
                    quality_score=summary.quality_score,
                    employee_role=role if role != "Desconocido" else None,
                )
            except RuntimeError as exc:
                logger.warning("Resumen IA no disponible: %s", exc)
                summary.ai_summary = None

        errors_df = (
            pd.DataFrame(validation_errors)
            if validation_errors
            else pd.DataFrame(columns=list(ValidationIssue.__annotations__.keys()))
        )
        workbook_bytes = self._export_workbook(df_clean, errors_df, summary)
        output_filename = self._build_output_filename(source_name)

        uploaded_original = None
        uploaded_corrected = None
        if upload_to_blob:
            if original_excel_bytes and blob_name_original:
                try:
                    azure_storage.upload_bytes_to_blob(
                        blob_name_original, original_excel_bytes, overwrite=True
                    )
                    uploaded_original = blob_name_original
                except Exception as exc:
                    logger.exception("Error subiendo archivo original a Blob Storage: %s", exc)
                    raise
            if blob_name_corrected:
                try:
                    azure_storage.upload_bytes_to_blob(
                        blob_name_corrected, workbook_bytes, overwrite=True
                    )
                    uploaded_corrected = blob_name_corrected
                except Exception as exc:
                    logger.exception("Error subiendo archivo corregido a Blob Storage: %s", exc)
                    raise

        for key, value in profile_settings.items():
            metadata.setdefault(key, value)

        corrected_snapshot = df_clean.copy(deep=True)

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

    @staticmethod
    def _apply_validation_corrections(
        df: pd.DataFrame,
        mapping: ColumnMapping,
        row_numbers: Sequence[int],
        validation_errors: Sequence[ValidationIssue],
    ) -> None:
        """Apply safe, suggested corrections to the in-memory dataframe."""
        if not row_numbers:
            return

        row_lookup = {row_num: idx for idx, row_num in enumerate(row_numbers)}
        for issue in validation_errors:
            correction = str(issue.get("valor_corregido") or "").strip()
            if not correction:
                continue

            row_idx = row_lookup.get(issue.get("fila"))
            if row_idx is None or row_idx >= len(df):
                continue

            tipo = issue.get("tipo_error")
            if tipo == "descripcion_calidad" and mapping.description in df.columns:
                df.at[df.index[row_idx], mapping.description] = correction
            # Importantly, do NOT overwrite hours here; only apply safe text fixes.


def _safe_string(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)
