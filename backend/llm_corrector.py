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
        temperature: float = 1.0, # Modelos o1/4o a veces requieren temp=1
        enable_cache: bool = True,
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
        
        # 🟢 FIX CONCURRENCIA: Inicializamos en None, se crea bajo demanda
        self._semaphore = None
        self._concurrency_limit = max_concurrent_requests
        
        # Inicializar caché
        self.enable_cache = enable_cache
        self._cache = None
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
        # 🟢 FIX CONCURRENCIA: Crear semáforo aquí dentro del loop
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._concurrency_limit)

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
            async with self._semaphore:
                # 🟢 FIX PARAMETRO: Usamos max_completion_tokens en lugar de max_tokens
                # Si tu modelo es o1-preview/mini, temperature suele forzarse a 1
                response = await self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_completion_tokens=250, # Nuevo nombre del parámetro
                    temperature=1.0 # Default seguro
                )
            
            content = response.choices[0].message.content or ""
            result = self._parse_llm_response(content, original_text=text)
            
            if self.enable_cache and self._cache:
                self._cache.set(text, role, project, result)
            
            return result

        except OpenAIError as exc:
            # 🟢 Manejo específico si el modelo no soporta max_completion_tokens
            if "Unsupported parameter" in str(exc) and "max_completion_tokens" in str(exc):
                logger.warning("Modelo no soporta max_completion_tokens, reintentando con max_tokens...")
                try:
                    # Reintento para modelos antiguos (legacy fallback)
                    async with self._semaphore:
                        response = await self.client.chat.completions.create(
                            model=self.deployment_name,
                            messages=[
                                {"role": "system", "content": self._system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            max_tokens=250, # Fallback antiguo
                            temperature=0.3
                        )
                    content = response.choices[0].message.content or ""
                    return self._parse_llm_response(content, original_text=text)
                except Exception as e2:
                    logger.error("Fallo reintento IA: %s", e2)
            
            logger.error("Azure OpenAI request failed: %s", exc)
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
        chunk: List[str] = []

        async def process_chunk(chunk_payload: List[str]) -> None:
            tasks = [
                asyncio.create_task(self._correct_text(item, role, project))
                for item in chunk_payload
            ]
            chunk_results = await asyncio.gather(*tasks)
            for text_item, corrected_item in zip(chunk_payload, chunk_results):
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