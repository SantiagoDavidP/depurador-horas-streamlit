from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CorrectionResult:
    """Resultado de una correccion ortografica y semantica basica."""

    fila: int
    original_text: str
    corrected_text: str
    changes: List[str] = field(default_factory=list)
    role_coherent: Optional[bool] = None
    specificity_level: Optional[int] = None
    suggestion: Optional[str] = None
    terminology_detected: List[str] = field(default_factory=list)
