from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from backend.infrastructure.ai.llm_corrector import CorrectionResult
from backend.domain.validation.validators import ValidationIssue


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


