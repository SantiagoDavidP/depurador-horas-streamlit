from __future__ import annotations

import logging
from collections import Counter
from typing import List

import pandas as pd

from backend.domain.models import ColumnMapping
from backend.domain.validation.validators import ValidationIssue

from .constants import _CRITICAL_ERROR_TYPES, _WARNING_ERROR_TYPES
from .models import ProcessorSummary

logger = logging.getLogger(__name__)


class ProcessingSummaryMixin:
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

