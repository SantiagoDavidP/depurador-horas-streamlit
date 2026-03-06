from __future__ import annotations

from typing import Protocol, Sequence, Tuple

from backend.application.processing.correction_result import CorrectionResult


class LLMCorrectorPort(Protocol):
    def correct_descriptions(
        self,
        rows: Sequence[Tuple[int, str]],
        *,
        role: str = "Desconocido",
        project: str = "No especificado",
    ) -> list[CorrectionResult]: ...
