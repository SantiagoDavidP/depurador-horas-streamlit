from __future__ import annotations

from typing import Sequence, Tuple

from backend.infrastructure.ai.llm_corrector import CorrectionResult, LLMCorrector


class LLMCorrectorAdapter:
    def __init__(self, corrector: LLMCorrector) -> None:
        self._corrector = corrector

    def correct_descriptions(
        self,
        rows: Sequence[Tuple[int, str]],
        *,
        role: str = "Desconocido",
        project: str = "No especificado",
    ) -> list[CorrectionResult]:
        return self._corrector.correct_descriptions(rows, role=role, project=project)
