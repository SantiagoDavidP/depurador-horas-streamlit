from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from openai import AsyncAzureOpenAI, OpenAIError

from config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CorrectionResult:
    """Resultado de una corrección ortográfica y semántica básica."""

    fila: int
    original_text: str
    corrected_text: str
    changes: List[str] = field(default_factory=list)
    role_coherent: Optional[bool] = None
    specificity_level: Optional[int] = None
    suggestion: Optional[str] = None
    terminology_detected: List[str] = field(default_factory=list)


class LLMCorrector:
    """Integración con Azure OpenAI para corrección ortográfica contextual."""

    def __init__(
        self,
        *,
        client: Optional[AsyncAzureOpenAI] = None,
        deployment_name: Optional[str] = None,
        batch_size: int = 20,
        max_concurrent_requests: int = 3,
        temperature: float = 0.1,
    ) -> None:
        settings = get_settings()
        if not client:
            if not settings.azure_openai.key or not settings.azure_openai.endpoint:
                raise RuntimeError("Azure OpenAI no está configurado. Revise las variables de entorno.")
            client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai.endpoint,
                api_key=settings.azure_openai.key,
                api_version=settings.azure_openai.api_version,
            )
        self.client = client
        self.deployment_name = deployment_name or settings.azure_openai.deployment
        self.batch_size = max(1, batch_size)
        self.temperature = temperature
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._system_prompt = (
            "Eres un corrector ortográfico especializado en timesheets de proyectos tecnológicos.\n\n"
            "REGLAS ESTRICTAS:\n\n"
            "PRESERVA términos técnicos en inglés:\n\n"
            "Metodologías: daily, standup, sprint, scrum, retrospective\n\n"
            "Git: merge, commit, pull request, push, branch, rebase\n\n"
            "DevOps: deployment, pipeline, docker, kubernetes, jenkins\n\n"
            "Testing: testing, smoke test, regression, unit test\n\n"
            "General: debugging, refactoring, code review, bug fixing\n\n"
            "PRESERVA nombres de tecnologías:\n\n"
            "Azure, AWS, GCP, Docker, Kubernetes, Jenkins, Git, GitHub\n\n"
            "Python, Java, JavaScript, TypeScript, React, Angular\n\n"
            "Terraform, Ansible, Prometheus, Grafana\n\n"
            "PRESERVA siglas y acrónimos:\n\n"
            "CI/CD, API, REST, QA, DevOps, UI/UX, ETL, SQL\n\n"
            "CORRIGE SOLO:\n\n"
            "Errores ortográficos evidentes en español\n"
            "Errores de acentuación\n"
            "Errores gramaticales básicos\n\n"
            "NO CAMBIES el significado técnico ni la estructura."
        )
        self._user_prompt_template = (
            "CONTEXTO:\n\n"
            "Rol: {role}\n\n"
            "Proyecto: {project}\n\n"
            "ACTIVIDAD A REVISAR:\n"
            "{text}\n\n"
            "RESPONDE EN JSON:\n"
            '{{\n'
            '  "texto_corregido": "...",\n'
            '  "cambios_realizados": ["cambio1", "cambio2"],\n'
            '  "es_coherente_con_rol": true,\n'
            '  "nivel_especificidad": 1,\n'
            '  "sugerencia_mejora": "...",\n'
            '  "terminologia_tecnica_detectada": ["termino1", "termino2"]\n'
            '}}\n'
        )

    @staticmethod
    def _normalize(text: str) -> str:
        return text.strip().lower()

    async def _correct_text(self, text: str, role: str, project: str) -> Dict[str, object]:
        user_prompt = self._user_prompt_template.format(role=role, project=project, text=text)
        try:
            async with self._semaphore:
                response = await self.client.chat.completions.create(
                    model=self.deployment_name,
                    temperature=self.temperature,
                    messages=[
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
            content = response.choices[0].message.content or ""
            return self._parse_llm_response(content, original_text=text)
        except OpenAIError as exc:
            logger.exception("Azure OpenAI request failed: %s", exc)
            return {
                "texto_corregido": text,
                "cambios_realizados": [],
                "es_coherente_con_rol": None,
                "nivel_especificidad": None,
                "sugerencia_mejora": None,
                "terminologia_tecnica_detectada": [],
            }
        except Exception as exc:  # pragma: no cover
            logger.exception("Unexpected error while calling Azure OpenAI: %s", exc)
            return {
                "texto_corregido": text,
                "cambios_realizados": [],
                "es_coherente_con_rol": None,
                "nivel_especificidad": None,
                "sugerencia_mejora": None,
                "terminologia_tecnica_detectada": [],
            }

    def _run_async(self, coro: asyncio.Future) -> Dict[str, Dict[str, object]]:
        try:
            return asyncio.run(coro)
        except RuntimeError as exc:
            if "already running" not in str(exc):
                raise
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                return new_loop.run_until_complete(coro)
            finally:
                asyncio.set_event_loop(None)
                new_loop.close()

    async def _correct_unique_payload(
        self,
        canonical_texts: Iterable[str],
        role: str,
        project: str,
    ) -> Dict[str, Dict[str, object]]:
        results: Dict[str, Dict[str, object]] = {}
        chunk: List[str] = []

        async def process_chunk(chunk_payload: List[str]) -> None:
            tasks = [
                asyncio.create_task(self._correct_text(item, role, project))
                for item in chunk_payload
            ]
            chunk_results = await asyncio.gather(*tasks)
            for text_item, corrected_item in zip(chunk_payload, chunk_results, strict=False):
                results[text_item] = corrected_item

        for text in canonical_texts:
            chunk.append(text)
            if len(chunk) >= self.batch_size:
                await process_chunk(chunk)
                chunk = []
        if chunk:
            await process_chunk(chunk)

        return results

    def correct_descriptions(
        self,
        rows: Sequence[Tuple[int, str]],
        *,
        role: str = "Desconocido",
        project: str = "No especificado",
    ) -> List[CorrectionResult]:
        """Corrige descripciones y devuelve metadatos enriquecidos."""
        if not rows:
            return []

        canonical_map: Dict[str, str] = {}
        reverse_map: Dict[str, List[Tuple[int, str]]] = {}

        for fila, text in rows:
            normalized = self._normalize(text)
            if not normalized:
                continue
            canonical_map.setdefault(normalized, text)
            reverse_map.setdefault(normalized, []).append((fila, text))

        if not canonical_map:
            return []

        canonical_texts = list(canonical_map.values())
        corrected_map = self._run_async(
            self._correct_unique_payload(canonical_texts, role, project)
        )

        corrections: List[CorrectionResult] = []
        for normalized, items in reverse_map.items():
            original_text = canonical_map[normalized]
            payload = corrected_map.get(original_text, {})
            corrected = payload.get("texto_corregido", original_text)
            changes = payload.get("cambios_realizados") or []
            role_coherent = payload.get("es_coherente_con_rol")
            specificity = payload.get("nivel_especificidad")
            suggestion = payload.get("sugerencia_mejora")
            terminology = payload.get("terminologia_tecnica_detectada") or []
            for fila, source_text in items:
                if corrected != source_text or changes or suggestion:
                    corrections.append(
                        CorrectionResult(
                            fila=fila,
                            original_text=source_text,
                            corrected_text=corrected,
                            changes=list(changes),
                            role_coherent=role_coherent if isinstance(role_coherent, bool) else None,
                            specificity_level=int(specificity) if isinstance(specificity, int) else None,
                            suggestion=suggestion if suggestion else None,
                            terminology_detected=list(terminology),
                        )
                    )
        logger.info("LLM generó %d correcciones de %d filas candidatas.", len(corrections), len(rows))
        return corrections

    @staticmethod
    def _parse_llm_response(content: str, *, original_text: str) -> Dict[str, object]:
        """Extrae JSON del LLM, tolerando envoltorios en markdown."""
        if not content:
            return {"texto_corregido": original_text}
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            json_start = cleaned.index("{")
            json_end = cleaned.rindex("}") + 1
            payload = json.loads(cleaned[json_start:json_end])
            payload.setdefault("texto_corregido", original_text)
            return payload
        except Exception:
            logger.warning("Respuesta LLM no es JSON válido, se usa texto plano.")
            return {"texto_corregido": cleaned or original_text}