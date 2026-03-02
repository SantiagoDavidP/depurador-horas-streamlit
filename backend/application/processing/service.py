from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

from backend.excel_parser import ParsedSheet
from backend.llm_corrector import CorrectionResult, LLMCorrector
from backend.models import ColumnMapping
from backend.role_validator import RoleActivityValidator
from backend.application.ports.llm_corrector_port import LLMCorrectorPort
from backend.infrastructure.ai.llm_corrector_adapter import LLMCorrectorAdapter

from .debug_views import ProcessingDebugViewsMixin
from .excel_export import ProcessingExcelExportMixin
from .models import ProcessorResult
from .normalization import ProcessingNormalizationMixin
from .pipeline import process_parsed_sheet_impl
from .summary import ProcessingSummaryMixin

logger = logging.getLogger(__name__)


class TimeSheetProcessor(
    ProcessingNormalizationMixin,
    ProcessingDebugViewsMixin,
    ProcessingSummaryMixin,
    ProcessingExcelExportMixin,
):
    """Orquesta validaciones, limpieza, correcciones LLM y reportes."""

    def __init__(
        self,
        *,
        expected_hours_per_day: float = 8.0,
        llm_corrector: Optional[LLMCorrectorPort] = None,
        role_validator: Optional[RoleActivityValidator] = None,
    ) -> None:
        self.expected_hours = expected_hours_per_day
        base_corrector: LLMCorrectorPort = llm_corrector or LLMCorrectorAdapter(
            LLMCorrector(batch_size=20)
        )
        self.llm_corrector: LLMCorrectorPort
        self.llm_corrector = base_corrector
        self.role_validator = role_validator or self._load_role_validator()

    @staticmethod
    def _load_role_validator() -> Optional[RoleActivityValidator]:
        taxonomy_path = Path(__file__).resolve().parents[3] / "config" / "role_taxonomy.json"
        if not taxonomy_path.exists():
            logger.warning("No se encontro role_taxonomy.json, se omite validacion de rol.")
            return None
        try:
            return RoleActivityValidator.from_json(taxonomy_path)
        except Exception as exc:
            logger.warning("No se pudo cargar la taxonomia de roles: %s", exc)
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
        return process_parsed_sheet_impl(
            self,
            parsed_sheet=parsed_sheet,
            mapping=mapping,
            source_name=source_name,
            original_excel_bytes=original_excel_bytes,
            correct_spelling=correct_spelling,
            upload_to_blob=upload_to_blob,
            blob_name_original=blob_name_original,
            blob_name_corrected=blob_name_corrected,
            role=role,
            project_name=project_name,
            duplicate_similarity_threshold=duplicate_similarity_threshold,
            duplicate_min_occurrences=duplicate_min_occurrences,
            hours_tolerance_factor=hours_tolerance_factor,
            client_profile_id=client_profile_id,
            client_profile_settings=client_profile_settings,
            batch_fast_mode=batch_fast_mode,
            enable_debug_exports=enable_debug_exports,
        )
