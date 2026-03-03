from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Actividades válidas para todos los roles (daily, reuniones, etc.)
UNIVERSAL_ACTIVITIES: Dict[str, List[str]] = {
    "daily": ["daily", "standup", "stand-up", "daily meeting", "daily scrum"],
    "meetings": ["reunión", "meeting", "reunion", "junta", "sync", "alineación"],
    "planning": ["planning", "planificación", "sprint planning", "estimación"],
    "retrospective": ["retrospective", "retrospectiva", "retro"],
}


@dataclass(frozen=True)
class RoleValidationResult:
    """Resultado final para una actividad analizada."""

    is_valid: bool
    confidence_score: float
    rol_detectado: str
    reasoning: str


class RoleActivityValidator:
    """Validador de coherencia entre rol declarado y actividades reportadas."""

    # Umbral mínimo para marcar como coherente después de aplicar el scoring.
    CONFIDENCE_THRESHOLD = 0.40

    STRONG_KEYWORDS: Dict[str, List[str]] = {
        "developer": [
            "código",
            "codigo",
            "commit",
            "merge",
            "pull request",
            "pr",
            "branch",
            "versionamiento",
            "repositorio",
            "script",
            "query",
            "sql",
            "database",
            "base de datos",
            "api",
            "endpoint",
            "desarrollo",
            "feature",
            "módulo",
            "modulo",
            "componente",
            "bug fix",
            "debugging",
            "refactor",
            "optimización de código",
            "optimización",
        ],
        "qa": [
            "testing",
            "test case",
            "casos de prueba",
            "regression",
            "smoke test",
            "automatización",
            "automation",
            "selenium",
            "defect tracking",
            "bug report",
            "quality assurance",
            "certificación",
            "certificacion",
            "plan de pruebas",
        ],
        "devops": [
            "deploy",
            "deployment",
            "pipeline",
            "docker",
            "kubernetes",
            "monitoring",
            "monitoreo",
            "infraestructura",
            "ci/cd",
            "terraform",
            "jenkins",
            "ansible",
            "release",
            "environment",
            "backup",
        ],
    }

    WEAK_KEYWORDS: Dict[str, List[str]] = {
        "developer": ["análisis", "analisis", "revisión", "revision", "documentación", "documentacion", "integración", "integracion"],
        "qa": ["validación", "validacion", "verificación", "verificacion"],
        "devops": ["configuración", "configuracion", "optimización", "optimizacion", "soporte infraestructura"],
    }

    FORBIDDEN_KEYWORDS: Dict[str, List[str]] = {
        "developer": [
            "testing manual exclusivo",
            "casos de prueba manuales",
            "plan de pruebas completo",
            "monitoreo de infraestructura",
            "configuración de servidores",
        ],
        "qa": [
            "deploy a producción",
            "pipeline",
            "automatización de infraestructura",
        ],
        "devops": [
            "maquetación",
            "diseño visual",
            "casos de prueba manuales",
        ],
    }

    def __init__(
        self,
        role_taxonomy: Dict[str, Dict[str, List[str]]],
        *,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.role_keywords: Dict[str, List[str]] = {}
        self._load_keywords(role_taxonomy)

    @classmethod
    def from_json(
        cls,
        json_path: Path,
        *,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> RoleActivityValidator:
        """Crea el validador a partir del archivo JSON de taxonomía."""
        try:
            with json_path.open("r", encoding="utf-8") as handle:
                taxonomy = json.load(handle)
        except Exception as exc:
            logger.exception("No se pudo cargar la taxonomía de roles: %s", exc)
            raise
        return cls(taxonomy, confidence_threshold=confidence_threshold)

    def validate_activity_for_role(
        self,
        activity: str,
        declared_role: str,
    ) -> RoleValidationResult:
        """Valida una sola actividad contra el rol declarado."""
        normalized_role = (declared_role or "").strip()
        if not normalized_role:
            normalized_role = "Desconocido"

        # 1. Actividades universales: Daily, reuniones, etc.
        is_universal, activity_type = self._is_universal_activity(activity)
        if is_universal:
            reasoning = (
                f"Actividad universal '{activity_type}' válida para cualquier rol. "
                "Marcada como coherente automáticamente."
            )
            return RoleValidationResult(
                is_valid=True,
                confidence_score=0.95,
                rol_detectado=normalized_role,
                reasoning=reasoning,
            )

        # 2. Determinar rol predominante y puntaje.
        detected_role, score, matches, reasoning = self._score_activity(activity, normalized_role)

        # 3. Ajuste por umbral y coincidencia de rol.
        is_known_role = normalized_role in self.role_keywords
        is_valid = (
            is_known_role
            and detected_role == normalized_role
            and score >= self.confidence_threshold
        )

        # Si el rol declarado no está en la taxonomía, marcamos inconsistente.
        if not is_known_role:
            return RoleValidationResult(
                is_valid=False,
                confidence_score=score,
                rol_detectado=detected_role,
                reasoning="El rol declarado no existe en la taxonomía configurada.",
            )

        if matches:
            reasoning = f"{reasoning} Coincidencias: {', '.join(matches)}."

        return RoleValidationResult(
            is_valid=is_valid,
            confidence_score=score,
            rol_detectado=detected_role,
            reasoning=reasoning,
        )

    def detect_role_from_activity(self, activity: str) -> str:
        """Devuelve el rol más probable según el texto de la actividad."""
        detected_role, _, _, _ = self._score_activity(activity, "")
        return detected_role

    def batch_validate(
        self,
        activities: List[str],
        declared_role: str,
    ) -> List[RoleValidationResult]:
        """Evalúa un listado de actividades contra un mismo rol."""
        results: List[RoleValidationResult] = []
        for activity in activities:
            try:
                results.append(self.validate_activity_for_role(activity, declared_role))
            except Exception as exc:
                logger.exception("Error validando actividad '%s': %s", activity, exc)
                results.append(
                    RoleValidationResult(
                        is_valid=False,
                        confidence_score=0.0,
                        rol_detectado="Error",
                        reasoning=f"Excepción durante la validación: {exc}",
                    )
                )
        return results

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _load_keywords(self, role_taxonomy: Dict[str, Dict[str, List[str]]]) -> None:
        """Combina keywords de la taxonomía con los sets adicionales."""
        for role, payload in role_taxonomy.items():
            keywords: List[str] = []
            for values in payload.values():
                keywords.extend(values)
            # Añadimos sets predefinidos (fuertes/débiles) para reforzar.
            keywords.extend(self.STRONG_KEYWORDS.get(role.lower(), []))
            keywords.extend(self.WEAK_KEYWORDS.get(role.lower(), []))
            normalized = sorted({kw.lower().strip() for kw in keywords if kw})
            if normalized:
                self.role_keywords[role] = normalized
        if not self.role_keywords:
            raise ValueError("La taxonomía de roles está vacía o mal formada.")

    @staticmethod
    def _is_universal_activity(description: str) -> Tuple[bool, Optional[str]]:
        """Detecta si la actividad es universal (válida para cualquier rol)."""
        desc_lower = description.lower()
        for activity_type, keywords in UNIVERSAL_ACTIVITIES.items():
            if any(keyword in desc_lower for keyword in keywords):
                return True, activity_type
        return False, None

    def _score_activity(
        self,
        description: str,
        declared_role: str,
    ) -> Tuple[str, float, List[str], str]:
        """Calcula puntaje para cada rol y devuelve el rol más probable."""
        desc_lower = description.lower()
        best_role = "Desconocido"
        best_score = 0.0
        best_matches: List[str] = []
        best_reasoning = "No se encontraron coincidencias relevantes."

        for role in self.role_keywords.keys():
            score, matches, reasoning = self._calculate_confidence_score(
                desc_lower,
                role.lower(),
                declared_role=declared_role.lower(),
            )
            if score > best_score:
                best_role = role
                best_score = score
                best_matches = matches
                best_reasoning = reasoning

        return best_role, best_score, best_matches, best_reasoning

    def _calculate_confidence_score(
        self,
        desc_lower: str,
        role: str,
        *,
        declared_role: str,
    ) -> Tuple[float, List[str], str]:
        """Implementa el nuevo sistema de scoring con contexto."""
        score = 0.0
        matches: List[str] = []
        reasoning_parts: List[str] = []

        strong = self.STRONG_KEYWORDS.get(role, [])
        weak = self.WEAK_KEYWORDS.get(role, [])
        forbidden = self.FORBIDDEN_KEYWORDS.get(role, [])

        # Keywords fuertes (+0.30). Bonus de contexto técnico (+0.10).
        for kw in strong:
            if kw in desc_lower:
                score += 0.30
                matches.append(kw)
                if any(token in desc_lower for token in ["error", "problema", "implementa", "ejecut", "deploy", "despliegue"]):
                    score += 0.10
                    reasoning_parts.append(f"Keyword fuerte '{kw}' con contexto técnico.")
                else:
                    reasoning_parts.append(f"Keyword fuerte '{kw}' detectada.")

        # Keywords débiles (+0.15).
        for kw in weak:
            if kw in desc_lower:
                score += 0.15
                matches.append(f"{kw} (contexto)")
                reasoning_parts.append(f"Keyword contextual '{kw}' detectada.")

        # Descripción suficientemente detallada (+0.10).
        if len(desc_lower) > 50:
            score += 0.10
            reasoning_parts.append("Descripción amplia (>50 caracteres).")

        # Penalización por keywords prohibidas (-0.30).
        if any(forbidden_kw in desc_lower for forbidden_kw in forbidden):
            score -= 0.30
            reasoning_parts.append("Se detectaron keywords asociadas a otros roles.")

        # Análisis contextual adicional (ej. developer haciendo pruebas).
        if declared_role == "developer":
            context_result = self._analyze_developer_context(desc_lower)
            if context_result["is_appropriate"]:
                score += context_result["confidence_adjustment"]
                reasoning_parts.append(context_result["reason"])
            elif context_result["confidence_adjustment"] < 0:
                score += context_result["confidence_adjustment"]
                reasoning_parts.append(context_result["reason"])

        score = min(max(score, 0.0), 1.0)  # Normaliza a [0, 1]
        if not reasoning_parts:
            reasoning_parts.append("Pocas coincidencias relevantes para cualquier rol.")

        return score, matches, " ".join(reasoning_parts)

    @staticmethod
    def _analyze_developer_context(desc_lower: str) -> Dict[str, Any]:
        """Mejora confianza cuando un developer menciona pruebas/QA en contexto válido."""
        developer_testing_patterns = [
            r"desarroll.{0,8}\spruebas",
            r"pruebas?\s+de\s+(integración|integracion|unidad|unitarias)",
            r"testing\s+de\s+(mi|su|el)\s+c[oó]digo",
            r"para\s+pasar\s+a\s+qa",
            r"solicita\s+a\s+qa",
            r"reunión\s+con\s+qa",
            r"certificaci[oó]n\s+con\s+qa",
        ]

        if "prueba" in desc_lower or "testing" in desc_lower or "qa" in desc_lower:
            for pattern in developer_testing_patterns:
                if re.search(pattern, desc_lower):
                    return {
                        "is_appropriate": True,
                        "confidence_adjustment": 0.20,
                        "reason": "Developer realizando/practicando pruebas propias o coordinando con QA.",
                    }

        return {
            "is_appropriate": False,
            "confidence_adjustment": -0.20 if "qa" in desc_lower else 0.0,
            "reason": "La mención de QA podría indicar actividad de otro rol.",
        }