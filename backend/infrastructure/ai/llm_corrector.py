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
        batch_size: int = 8,
        max_concurrent_requests: int = 3,
        temperature: float = 1.0, # Modelos o1/4o a veces requieren temp=1
        enable_cache: bool = True,
        request_timeout_seconds: float = 45.0,
    ) -> None:
        settings = get_settings()
        if not client:
            if not settings.azure_openai.key or not settings.azure_openai.endpoint:
                raise RuntimeError("Azure OpenAI no está configurado. Revise las variables de entorno.")
            client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai.endpoint,
                api_key=settings.azure_openai.key,
                api_version=settings.azure_openai.api_version,
                azure_deployment=settings.azure_openai.deployment,  # 🟢 IMPORTANTE: Especificar deployment
                max_retries=0,  # Evita reintentos internos cuando hay errores permanentes (404/400)
            )
        self.client = client
        self.deployment_name = deployment_name or settings.azure_openai.deployment
        # Tamaño de lote real por request (recomendado 5-10)
        self.batch_size = max(1, min(int(batch_size), 10))
        self.temperature = temperature
        self.request_timeout_seconds = max(5.0, float(request_timeout_seconds))
        
        # Concurrencia controlada por batch; dejamos semaphore opcional por compatibilidad
        self._concurrency_limit = max_concurrent_requests
        self._semaphore = None
        
        # Inicializar caché
        self.enable_cache = enable_cache
        self._cache = None
        self._llm_unavailable = False
        if enable_cache:
            try:
                from backend.llm_cache import get_llm_cache
                self._cache = get_llm_cache()
                logger.info("Caché de LLM habilitado")
            except ImportError:
                logger.warning("No se pudo importar llm_cache, caché deshabilitado")
                self.enable_cache = False
        
        # 🟢 FIX PROMPT: Instrucciones claras y ejemplos (Few-Shot)
        self._system_prompt = (
            "Eres un experto corrector de estilo y ortografía para reportes técnicos (timesheets).\n"
            "Tu objetivo es limpiar el texto para que sea profesional, manteniendo intacta la terminología técnica.\n\n"
            
            "REGLAS DE ORO:\n"
            "1. CORRIGE SIEMPRE: Acentos (tildes), errores de 'b/v', 'c/s/z', 'h', y mayúsculas iniciales.\n"
            "2. PRESERVA EXACTAMENTE: Términos en inglés (daily, deploy, commit, sprint), nombres de herramientas (Azure, Docker) y acrónimos (QA, API).\n"
            "3. NO RESUMAS: El texto corregido debe tener la misma longitud y detalle que el original.\n\n"
            
            "EJEMPLOS DE COMPORTAMIENTO ESPERADO:\n"
            "Entrada: 'reunion con el equipo de qa para ver el bug'\n"
            "Salida Correcta: 'Reunión con el equipo de QA para ver el bug'\n\n"
            
            "Entrada: 'despliegue en produccion del microservicio de pagos'\n"
            "Salida Correcta: 'Despliegue en producción del microservicio de pagos'\n\n"
            
            "Entrada: 'analisis de logs en azure monitor'\n"
            "Salida Correcta: 'Análisis de logs en Azure Monitor'\n\n"
            
            "ANALIZA Y CORRIGE EL SIGUIENTE TEXTO SIGUIENDO ESTOS PATRONES."
        )
        
        self._user_prompt_template = (
            "CONTEXTO:\n"
            "Rol: {role}\n"
            "Proyecto: {project}\n\n"
            "TEXTO ORIGINAL:\n"
            "\"{text}\"\n\n"
            "Genera una respuesta JSON estrictamente con este formato:\n"
            "{{\n"
            "  \"texto_corregido\": \"(Texto corregido)\",\n"
            "  \"cambios_realizados\": [\"lista de correcciones\"],\n"
            "  \"es_coherente_con_rol\": true,\n"
            "  \"nivel_especificidad\": 1,\n"
            "  \"sugerencia_mejora\": \"(Opcional)\",\n"
            "  \"terminologia_tecnica_detectada\": [\"termino1\", \"termino2\"]\n"
            "}}"
        )
        self._user_prompt_batch_template = (
            "CONTEXTO:\n"
            "Rol: {role}\n"
            "Proyecto: {project}\n\n"
            "TAREAS A CORREGIR (JSON):\n"
            "{items_json}\n\n"
            "Devuelve SOLO JSON válido con esta forma:\n"
            "{{\n"
            "  \"resultados\": [\n"
            "    {{\"id\": 0, \"texto_corregido\": \"...\", \"cambios_realizados\": [], "
            "\"es_coherente_con_rol\": true, \"nivel_especificidad\": 1, "
            "\"sugerencia_mejora\": null, \"terminologia_tecnica_detectada\": []}}\n"
            "  ]\n"
            "}}"
        )

    @staticmethod
    def _normalize(text: str) -> str:
        return text.strip().lower()

    @staticmethod
    def _sanitize_input(text: str, max_length: int = 500) -> str:
        if not text:
            return "No especificado"
        sanitized = " ".join(str(text).split())
        return sanitized[:max_length]

    async def _correct_text(self, text: str, role: str, project: str) -> Dict[str, object]:
        if self._llm_unavailable:
            return self._default_result(text)

    async def _correct_texts_batch(
        self, texts: List[str], role: str, project: str
    ) -> Dict[str, Dict[str, object]]:
        """Corrige un lote de textos en UNA sola llamada LLM."""
        if not texts:
            return {}

        # Resolver caché primero
        results: Dict[str, Dict[str, object]] = {}
        uncached: List[Tuple[int, str]] = []
        for idx, text in enumerate(texts):
            if self.enable_cache and self._cache:
                cached = self._cache.get(text, role, project)
                if cached is not None:
                    results[text] = cached
                    continue
            uncached.append((idx, text))

        if not uncached or self._llm_unavailable:
            for _, t in uncached:
                results[t] = self._default_result(t)
            return results

        payload_items = [
            {"id": idx, "texto": self._sanitize_input(text, max_length=500)}
            for idx, text in uncached
        ]
        user_prompt = self._user_prompt_batch_template.format(
            role=self._sanitize_input(role, max_length=50),
            project=self._sanitize_input(project, max_length=100),
            items_json=json.dumps(payload_items, ensure_ascii=False),
        )

        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=1,
                    timeout=self.request_timeout_seconds,
                ),
                timeout=self.request_timeout_seconds + 5.0,
            )
            content = response.choices[0].message.content or ""
            batch_payload = self._parse_llm_batch_response(content)

            by_id: Dict[int, Dict[str, object]] = {}
            for item in batch_payload.get("resultados", []):
                if not isinstance(item, dict):
                    continue
                try:
                    item_id = int(item.get("id"))
                except Exception:
                    continue
                by_id[item_id] = item

            for idx, original in uncached:
                parsed = by_id.get(idx) or {"texto_corregido": original}
                parsed.setdefault("texto_corregido", original)
                results[original] = parsed
                if self.enable_cache and self._cache:
                    self._cache.set(original, role, project, parsed)

            return results
        except asyncio.TimeoutError:
            logger.warning(
                "Timeout en lote LLM (%s items, %.1fs). Se aplica fallback sin bloquear.",
                len(uncached),
                self.request_timeout_seconds,
            )
            for _, original in uncached:
                results[original] = self._default_result(original)
            return results
        except Exception:
            # Fallback: si el lote falla, no bloqueamos proceso.
            for _, original in uncached:
                results[original] = self._default_result(original)
            return results

        safe_role = self._sanitize_input(role, max_length=50)
        safe_project = self._sanitize_input(project, max_length=100)
        safe_text = self._sanitize_input(text, max_length=500)
        
        if self.enable_cache and self._cache:
            cached_result = self._cache.get(text, role, project)
            if cached_result is not None:
                return cached_result
        
        user_prompt = self._user_prompt_template.format(
            role=safe_role, 
            project=safe_project, 
            text=safe_text
        )
        
        try:
            # 🟢 REMOVED: Sin semaphore - batch_size ya limita concurrencia
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=1
            )
            
            content = response.choices[0].message.content or ""
            result = self._parse_llm_response(content, original_text=text)
            
            if self.enable_cache and self._cache:
                self._cache.set(text, role, project, result)
            
            return result

        except OpenAIError as exc:
            logger.error("Azure OpenAI request failed: %s", exc)
            error_text = str(exc).lower()
            # Errores permanentes: no vale la pena seguir intentando en este procesamiento
            if (
                "resource not found" in error_text
                or "unsupported parameter" in error_text
                or "invalid_request_error" in error_text
                or "error code: 400" in error_text
                or "error code: 404" in error_text
            ):
                self._llm_unavailable = True
            return self._default_result(text)
            
        except Exception as exc:
            logger.exception("Unexpected error while calling Azure OpenAI: %s", exc)
            return self._default_result(text)

    def _default_result(self, text: str) -> Dict[str, object]:
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
            # Fix para Streamlit que ya tiene loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    async def _correct_unique_payload(
        self,
        canonical_texts: Iterable[str],
        role: str,
        project: str,
    ) -> Dict[str, Dict[str, object]]:
        results: Dict[str, Dict[str, object]] = {}
        canonical_list = list(canonical_texts)

        # Chunk dinámico: más pequeño en cargas chicas, más grande en cargas grandes
        # (6 -> 10 según volumen)
        total_items = len(canonical_list)
        if total_items >= 120:
            effective_batch_size = 10
        elif total_items >= 60:
            effective_batch_size = 8
        else:
            effective_batch_size = 6
        effective_batch_size = max(1, min(effective_batch_size, self.batch_size))

        chunks: List[List[str]] = []
        chunk: List[str] = []

        for text in canonical_list:
            chunk.append(text)
            if len(chunk) >= effective_batch_size:
                chunks.append(chunk)
                chunk = []
        if chunk:
            chunks.append(chunk)

        semaphore = asyncio.Semaphore(max(1, int(self._concurrency_limit)))

        async def process_chunk(chunk_payload: List[str]) -> Dict[str, Dict[str, object]]:
            async with semaphore:
                return await self._correct_texts_batch(chunk_payload, role, project)

        tasks = [asyncio.create_task(process_chunk(c)) for c in chunks]
        chunk_results_list = await asyncio.gather(*tasks)

        for chunk_payload, chunk_results in zip(chunks, chunk_results_list):
            for text_item in chunk_payload:
                results[text_item] = chunk_results.get(text_item, self._default_result(text_item))

        return results

    def correct_descriptions(
        self,
        rows: Sequence[Tuple[int, str]],
        *,
        role: str = "Desconocido",
        project: str = "No especificado",
    ) -> List[CorrectionResult]:
        if not rows:
            return []

        # Filtro conservador para evitar enviar filas obvias al LLM
        def _should_send(text: str) -> bool:
            if not text:
                return False
            cleaned = " ".join(str(text).split())
            if not cleaned:
                return False
            # Al menos 3 palabras
            if len(cleaned.split()) < 3:
                return False
            # Solo numérico => no enviar
            if cleaned.replace(".", "", 1).isdigit():
                return False
            # Solo mayúsculas => no enviar
            if cleaned == cleaned.upper() and any(ch.isalpha() for ch in cleaned):
                return False
            # Debe tener letras
            if not any(ch.isalpha() for ch in cleaned):
                return False
            return True

        # Límite máximo por archivo para LLM
        MAX_LLM_ROWS = 50

        canonical_map: Dict[str, str] = {}
        reverse_map: Dict[str, List[Tuple[int, str]]] = {}

        eligible_rows: List[Tuple[int, str]] = []
        for fila, text in rows:
            if _should_send(text):
                eligible_rows.append((fila, text))
        if len(eligible_rows) > MAX_LLM_ROWS:
            eligible_rows = eligible_rows[:MAX_LLM_ROWS]

        if not eligible_rows:
            return []

        for fila, text in eligible_rows:
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
            
            # Solo agregar si hubo cambios reales
            if corrected != original_text or changes or suggestion:
                for fila, source_text in items:
                    corrections.append(
                        CorrectionResult(
                            fila=fila,
                            original_text=source_text,
                            corrected_text=corrected,
                            changes=list(changes),
                            role_coherent=bool(role_coherent) if role_coherent is not None else None,
                            specificity_level=int(specificity) if isinstance(specificity, int) else None,
                            suggestion=suggestion if suggestion else None,
                            terminology_detected=list(terminology),
                        )
                    )
        
        logger.info("LLM generó %d correcciones de %d filas candidatas.", len(corrections), len(rows))
        return corrections

    @staticmethod
    def _parse_llm_response(content: str, *, original_text: str) -> Dict[str, object]:
        if not content:
            return {"texto_corregido": original_text}
        
        cleaned = content.strip()
        # Remove markdown code blocks if present
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        
        try:
            # Find the JSON object
            json_start = cleaned.find("{")
            json_end = cleaned.rfind("}") + 1
            
            if json_start != -1 and json_end != -1:
                json_str = cleaned[json_start:json_end]
                payload = json.loads(json_str)
                payload.setdefault("texto_corregido", original_text)
                return payload
            else:
                # Fallback if no JSON structure found
                return {"texto_corregido": cleaned or original_text}
                
        except Exception:
            logger.warning("Respuesta LLM no es JSON válido, se usa texto plano.")
            return {"texto_corregido": cleaned or original_text}

    @staticmethod
    def _parse_llm_batch_response(content: str) -> Dict[str, object]:
        if not content:
            return {"resultados": []}
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            json_start = cleaned.find("{")
            json_end = cleaned.rfind("}") + 1
            if json_start != -1 and json_end != -1:
                payload = json.loads(cleaned[json_start:json_end])
                if isinstance(payload, dict):
                    payload.setdefault("resultados", [])
                    return payload
        except Exception:
            pass
        return {"resultados": []}
