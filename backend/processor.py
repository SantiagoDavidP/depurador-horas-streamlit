from __future__ import annotations
from collections import Counter

import logging
import time
import os
import re
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
from backend.perf import PerfCollector
from backend.role_validator import RoleActivityValidator
from backend.profile_validations import run_profile_validations
from backend.baninter_processor import prepare_baninter_dataframe
from backend.validators import (
    ValidationIssue,
    run_all_validations,
    validate_mapping,
    _coerce_hours_series,
)

logger = logging.getLogger(__name__)

_CRITICAL_ERROR_TYPES = {
    "fecha_invalida",
    "fin_semana",
    "feriado",
    "horas_incorrectas",
    "horas_excesivas",
    "horas_muy_bajas",
    "horas_faltantes",
}

_ERROR_PRIORITY = [
    "completitud",
    "fecha_fuera_periodo",
    "fecha_invalida",
    "fin_semana",
    "feriado",
    "horas_incorrectas",
    "horas_excesivas",
    "horas_muy_bajas",
    "duplicado_exacto",
    "duplicado_similar",
    "descripcion_repetida",
]
_ERROR_PRIORITY_INDEX = {t: i for i, t in enumerate(_ERROR_PRIORITY)}
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

    @staticmethod
    def _is_baninter_profile(client_profile_id: Optional[str], metadata: Dict[str, object]) -> bool:
        if client_profile_id == "cliente_talent":
            return True
        company = str(metadata.get("company", "") or "").lower()
        if "baninter" in company or "banco internacional" in company:
            return True
        return False

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

    def _group_hours_debug_df(
        self,
        df: pd.DataFrame,
        *,
        mapping: ColumnMapping,
        row_numbers: Sequence[int],
    ) -> pd.DataFrame:
        """Agrupa horas por fecha con detalle de filas y valores."""
        if df.empty or mapping.date not in df.columns or mapping.hours not in df.columns:
            return pd.DataFrame()

        parsed_dates = pd.to_datetime(df[mapping.date], errors="coerce", dayfirst=True)
        hours_raw = df[mapping.hours]
        hours_num = _coerce_hours_series(hours_raw)
        # Alinear longitudes defensivamente
        safe_len = min(len(df.index), len(row_numbers))
        if safe_len == 0:
            return pd.DataFrame()
        df = df.iloc[:safe_len].copy()
        row_numbers_series = pd.Series(list(row_numbers)[:safe_len], index=df.index)

        work = pd.DataFrame(
            {
                "Fecha": parsed_dates.dt.date,
                "Horas_Raw": hours_raw,
                "Horas_Num": hours_num,
                "Fila_Excel": row_numbers_series,
            }
        ).dropna(subset=["Fecha"], how="any")

        if work.empty:
            return pd.DataFrame()

        def _join_series(series: pd.Series) -> str:
            return " | ".join(str(x) for x in series.tolist())

        grouped = (
            work.groupby("Fecha")
            .agg(
                Filas=("Horas_Num", "size"),
                Horas_Sumadas=("Horas_Num", "sum"),
                Horas_Invalidas=("Horas_Num", lambda s: int(s.isna().sum())),
                Horas_Raw=("Horas_Raw", _join_series),
                Filas_Excel=("Fila_Excel", _join_series),
            )
            .reset_index()
        )
        return grouped

    @staticmethod
    def _merge_hours_debug(
        raw_debug: pd.DataFrame,
        clean_debug: pd.DataFrame,
        *,
        expected_hours: float,
    ) -> pd.DataFrame:
        if raw_debug.empty and clean_debug.empty:
            return pd.DataFrame()

        raw = raw_debug.rename(
            columns={
                "Filas": "Filas_Raw",
                "Horas_Sumadas": "Horas_Sumadas_Raw",
                "Horas_Invalidas": "Horas_Invalidas_Raw",
                "Horas_Raw": "Horas_Raw_Raw",
                "Filas_Excel": "Filas_Excel_Raw",
            }
        )
        clean = clean_debug.rename(
            columns={
                "Filas": "Filas_Clean",
                "Horas_Sumadas": "Horas_Sumadas_Clean",
                "Horas_Invalidas": "Horas_Invalidas_Clean",
                "Horas_Raw": "Horas_Raw_Clean",
                "Filas_Excel": "Filas_Excel_Clean",
            }
        )

        merged = raw.merge(clean, on="Fecha", how="outer").sort_values("Fecha")
        merged["Horas_Esperadas"] = expected_hours
        merged["Diferencia_Clean"] = merged["Horas_Sumadas_Clean"] - expected_hours
        return merged

    def _build_hours_debug_detail(
        self,
        *,
        df: pd.DataFrame,
        mapping: ColumnMapping,
        row_numbers: Sequence[int],
        validation_errors: Sequence[ValidationIssue],
        stage_label: str,
    ) -> pd.DataFrame:
        """Detalle por fila para fechas con horas_incorrectas."""
        if df.empty or not validation_errors:
            return pd.DataFrame()

        target_dates = sorted(
            {
                err.get("fecha")
                for err in validation_errors
                if err.get("tipo_error") == "horas_incorrectas" and err.get("fecha")
            }
        )
        if not target_dates:
            return pd.DataFrame()

        parsed_dates = pd.to_datetime(df[mapping.date], errors="coerce", dayfirst=True)
        hours_raw = df[mapping.hours]
        hours_num = _coerce_hours_series(hours_raw)
        descriptions = (
            df[mapping.description]
            if mapping.description in df.columns
            else pd.Series(index=df.index, dtype="object")
        )
        desc_series = descriptions.astype(str)
        desc_clean = desc_series.str.strip()
        empty_tokens = {"", "-", "---"}
        desc_empty = desc_series.isna() | desc_clean.isin(empty_tokens) | desc_clean.eq("")
        desc_numeric = desc_clean.str.fullmatch(r"\d+(\.\d+)?", na=False)
        hours_missing_or_zero = hours_num.isna() | (hours_num == 0)

        non_core_cols = [
            col
            for col in df.columns
            if col not in {mapping.date, mapping.hours, mapping.description}
        ]
        non_core_non_empty_count = pd.Series(0, index=df.index)
        if non_core_cols:
            for col in non_core_cols:
                series = df[col]
                non_empty = (
                    series.notna()
                    & series.astype(str).str.strip().ne("")
                    & ~series.astype(str).str.strip().isin(empty_tokens)
                )
                non_core_non_empty_count += non_empty.astype(int)

        footer_like = (
            hours_missing_or_zero
            & (desc_empty | desc_numeric)
            & (non_core_non_empty_count <= 1)
        )
        # Alinear longitudes defensivamente
        safe_len = min(len(df.index), len(row_numbers))
        if safe_len == 0:
            return pd.DataFrame()
        df = df.iloc[:safe_len].copy()
        row_numbers_series = pd.Series(list(row_numbers)[:safe_len], index=df.index)

        work = pd.DataFrame(
            {
                "Fecha": parsed_dates.dt.strftime("%Y-%m-%d"),
                "Horas_Raw": hours_raw,
                "Horas_Num": hours_num,
                "Descripcion": descriptions,
                "Fila_Excel": row_numbers_series,
                "Etapa": stage_label,
                "Desc_Vacia": desc_empty,
                "Desc_Numerica": desc_numeric,
                "Horas_Faltantes": hours_missing_or_zero,
                "Cols_NoCore": non_core_non_empty_count,
                "Footer_Like": footer_like,
            }
        )
        return work[work["Fecha"].isin(target_dates)].reset_index(drop=True)

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
        debug_hours_df: Optional[pd.DataFrame] = None,
        debug_detail_df: Optional[pd.DataFrame] = None,
    ) -> bytes:
        def _sanitize_excel_df(df: pd.DataFrame) -> pd.DataFrame:
            if df is None or df.empty:
                return df
            return df.where(pd.notna(df), None)

        corrected_df = _sanitize_excel_df(corrected_df)
        errors_df = _sanitize_excel_df(errors_df)
        if debug_hours_df is not None:
            debug_hours_df = _sanitize_excel_df(debug_hours_df)
        if debug_detail_df is not None:
            debug_detail_df = _sanitize_excel_df(debug_detail_df)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            workbook = writer.book
            self._create_executive_summary_sheet(workbook, summary)
            corrected_df.to_excel(writer, index=False, sheet_name="Datos Corregidos")
            errors_df.to_excel(writer, index=False, sheet_name="Reporte de Errores")
            if debug_hours_df is not None and not debug_hours_df.empty:
                debug_hours_df.to_excel(writer, index=False, sheet_name="Debug Horas")
            if debug_detail_df is not None and not debug_detail_df.empty:
                debug_detail_df.to_excel(writer, index=False, sheet_name="Debug Filas")
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
        batch_fast_mode: bool = False,
        enable_debug_exports: bool = True,
    ) -> ProcessorResult:
        df = parsed_sheet.dataframe.copy()
        df = self._drop_empty_columns(df)
        perf = PerfCollector()
        t_total = time.perf_counter()
        t_stage = time.perf_counter()

        # Normalizar tickets (quitar espacios) para aceptar valores alfanuméricos limpios.
        self._normalize_ticket_columns(df)
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
        raw_row_numbers = list(row_numbers)
        logger.info("TIMING: preparar metadata en %.2fs", time.perf_counter() - t_stage)
        t_stage = time.perf_counter()

        # BANINTER: tolerancia (ffill + columnas opcionales)
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

        # Completar fechas agrupadas (celdas vacías) antes de validar el mapeo
        if mapping.date in df.columns:
            if mapping.description in df.columns:
                desc_series = df[mapping.description].astype(str).str.strip()
            else:
                desc_series = pd.Series(index=df.index, dtype="object")

            if mapping.hours in df.columns:
                hours_series = pd.to_numeric(df[mapping.hours], errors="coerce")
            else:
                hours_series = pd.Series(index=df.index, dtype="float")

            has_payload = (
                desc_series.notna()
                & desc_series.ne("")
                & ~desc_series.isin({"-", "---"})
            ) | (hours_series.notna() & (hours_series != 0))
            # df.loc[has_payload, mapping.date] = df.loc[has_payload, mapping.date].ffill()

        # Remover filas de totales que se vuelven "válidas" tras ffill (evita falsos positivos)
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
            "Dataset limpio: %d registros válidos de %d totales",
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
            # Debug: consolidado por fecha para detectar por qué no suma 8h
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

        # Evitar duplicidad: si la fecha estÃ¡ fuera de periodo, no reportar fin de semana/feriado
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
        # Correcciones LLM (solo si correct_spelling está activo)
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

        # IA desactivada: no generar resumen IA
        # if summary.total_registros > 0:
        #     try:
        #         summary.ai_summary = generate_ai_summary_sync(
        #             total_records=summary.total_registros,
        #             critical_errors=summary.errores_criticos,
        #             warnings=summary.errores_advertencia,
        #             quality_score=summary.quality_score,
        #             employee_role=role if role != "Desconocido" else None,
        #         )
        #     except RuntimeError as exc:
        #         logger.warning("Resumen IA no disponible: %s", exc)
        #         summary.ai_summary = None

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

    @staticmethod
    def _sort_errors_df(errors_df: pd.DataFrame) -> pd.DataFrame:
        if errors_df is None or errors_df.empty or "tipo_error" not in errors_df.columns:
            return errors_df
        sorted_df = errors_df.copy()
        sorted_df["__severity"] = sorted_df["tipo_error"].astype(str).apply(
            lambda t: _ERROR_PRIORITY_INDEX.get(t, len(_ERROR_PRIORITY))
        )
        sorted_df["__order"] = range(len(sorted_df))
        sorted_df = sorted_df.sort_values(["__severity", "__order"])
        return sorted_df.drop(columns=["__severity", "__order"])

    @staticmethod
    def _normalize_ticket_columns(df: pd.DataFrame) -> None:
        ticket_columns = [
            col for col in df.columns if "ticket" in str(col).lower()
        ]
        if not ticket_columns:
            return

        def _normalize(value: object) -> object:
            if pd.isna(value):
                return value
            if isinstance(value, (int, float)) and not pd.isna(value):
                if isinstance(value, float) and value.is_integer():
                    return str(int(value))
                return str(value)
            text = str(value).strip()
            if not text:
                return ""
            normalized = re.sub(r"\s+", "", text)
            return normalized

        for col in ticket_columns:
            df[col] = df[col].apply(_normalize)

    @staticmethod
    def _drop_empty_columns(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        drop_cols = []
        for col in df.columns:
            series = df[col]
            if series.isna().all():
                drop_cols.append(col)
                continue
            try:
                if series.astype(str).str.strip().eq("").all():
                    drop_cols.append(col)
            except Exception:
                continue
        if drop_cols:
            logger.info("Columnas fantasma removidas: %d", len(drop_cols))
            return df.drop(columns=drop_cols)
        return df

    @staticmethod
    def _normalize_ticket_validation_errors(
        errors: List[ValidationIssue],
        df: pd.DataFrame,
        ticket_column: str,
        row_numbers: Sequence[int],
    ) -> List[ValidationIssue]:
        if not errors or ticket_column not in df.columns:
            return errors

        def _is_valid_ticket(value: object) -> bool:
            if pd.isna(value):
                return True
            if isinstance(value, (int, float)) and not pd.isna(value):
                return True
            text = str(value).strip()
            if not text:
                return True
            normalized = re.sub(r"\s+", "", text)
            token = re.sub(r"[^A-Za-z0-9]", "", normalized).upper()
            if token in {"NA", "NAN", "SN"}:
                return True
            return normalized.isalnum()

        row_lookup = {row_num: idx for idx, row_num in enumerate(row_numbers)}
        filtered: List[ValidationIssue] = []
        for issue in errors:
            tipo = str(issue.get("tipo_error") or "")
            if tipo not in {"ticket_no_numerico", "ticket_invalido"}:
                filtered.append(issue)
                continue
            row_num = issue.get("fila")
            idx = row_lookup.get(row_num)
            if idx is None or idx >= len(df):
                filtered.append(issue)
                continue
            value = df.at[df.index[idx], ticket_column]
            if _is_valid_ticket(value):
                continue
            issue["tipo_error"] = "ticket_invalido"
            issue["descripcion"] = (
                "El ticket debe ser alfanumérico o estar vacío. Evite caracteres especiales."
            )
            filtered.append(issue)

        return filtered


def _safe_string(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)
