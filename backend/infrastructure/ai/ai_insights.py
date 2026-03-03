from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from openai import AsyncAzureOpenAI, OpenAIError

from config.settings import get_settings

logger = logging.getLogger(__name__)

_CLIENT: Optional[AsyncAzureOpenAI] = None


def _get_client() -> AsyncAzureOpenAI:
    """Devuelve un cliente AsyncAzureOpenAI configurado con las credenciales actuales."""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT

    settings = get_settings()
    if not settings.azure_openai.key or not settings.azure_openai.endpoint:
        raise RuntimeError("Azure OpenAI no está configurado para generar resúmenes.")

    _CLIENT = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai.endpoint,
        api_key=settings.azure_openai.key,
        api_version=settings.azure_openai.api_version,
        azure_deployment=settings.azure_openai.deployment,  # 🟢 IMPORTANTE: Especificar deployment
        max_retries=0,  # Evita esperas extra cuando hay error permanente de configuración
    )
    return _CLIENT


async def generate_ai_summary(
    *,
    total_records: int,
    critical_errors: int,
    warnings: int,
    quality_score: float,
    employee_role: Optional[str] = None,
    max_attempts: int = 3,
    initial_delay: float = 0.6,
) -> Dict[str, Any]:
    """Produce un resumen ejecutivo en español; reintenta en caso de fallos temporales."""
    role_snippet = f"- Rol del empleado: {employee_role}\n" if employee_role else ""
    prompt = f"""
Eres un Project Manager senior que redacta resúmenes ejecutivos de timesheets.

DATOS:
- Registros totales: {total_records}
- Errores críticos: {critical_errors}
- Advertencias: {warnings}
- Score de calidad: {quality_score:.0f}/100
{role_snippet}

DEVUELVE un JSON EXACTO con las claves:
{{
  "diagnostico": "Texto con 2-3 frases que resuma hallazgos (usa emojis clave y resalta métricas en **negritas**).",
  "acciones": ["Acción concreta 1", "Acción concreta 2", "Acción concreta 3"],
  "tiempo_estimado": "Ej: 30 minutos"
}}

Reglas:
- Usa tono profesional pero cercano.
- Incluye al menos un emoji por frase en 'diagnostico'.
- En 'acciones' da recomendaciones accionables, breves y específicas.
- Mantén la salida estrictamente en JSON válido.
    """.strip()

    settings = get_settings()

    for attempt in range(1, max_attempts + 1):
        try:
            client = _get_client()
            settings = get_settings()
            response = await client.chat.completions.create(
                model=settings.azure_openai.deployment,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=1,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except (OpenAIError, RuntimeError, json.JSONDecodeError, TypeError) as exc:
            logger.warning(
                "Intento %d/%d falló generando resumen IA: %s",
                attempt,
                max_attempts,
                exc,
            )
            error_text = str(exc).lower()
            if (
                "resource not found" in error_text
                or "unsupported parameter" in error_text
                or "invalid_request_error" in error_text
                or "error code: 400" in error_text
                or "error code: 404" in error_text
            ):
                # Error permanente de configuración/modelo: salir sin reintentar
                break
            if attempt == max_attempts:
                break
            await asyncio.sleep(initial_delay * attempt)

    logger.warning("No fue posible generar el resumen IA tras %d intentos.", max_attempts)
    return {
        "diagnostico": "No se pudo generar el resumen inteligente. Revise manualmente el reporte.",
        "acciones": [
            "Revisar los errores críticos detectados en el reporte.",
            "Ajustar horas y fechas incoherentes antes de reenviar el timesheet.",
            "Reintentar la generación cuando Azure OpenAI esté disponible.",
        ],
        "tiempo_estimado": "No disponible",
    }


def generate_ai_summary_sync(
    *,
    total_records: int,
    critical_errors: int,
    warnings: int,
    quality_score: float,
    employee_role: Optional[str] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Wrapper síncrono para generar el resumen desde contextos sin loop activo."""
    coro = generate_ai_summary(
        total_records=total_records,
        critical_errors=critical_errors,
        warnings=warnings,
        quality_score=quality_score,
        employee_role=employee_role,
    )
    try:
        return asyncio.run(asyncio.wait_for(coro, timeout=timeout))
    except asyncio.TimeoutError:
        logger.warning("Timeout generando resumen IA tras %.1f segundos", timeout)
        return {
            "diagnostico": "⏱️ Timeout generando resumen inteligente. Revise manualmente el reporte.",
            "acciones": [
                "El servidor IA no respondió a tiempo.",
                "Revisar los errores críticos en el reporte.",
                "Reintentar más tarde.",
            ],
            "tiempo_estimado": "No disponible",
        }
    except RuntimeError as exc:
        if "already running" not in str(exc):
            raise
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
        except asyncio.TimeoutError:
            logger.warning("Timeout generando resumen IA tras %.1f segundos", timeout)
            return {
                "diagnostico": "⏱️ Timeout generando resumen inteligente. Revise manualmente el reporte.",
                "acciones": [
                    "El servidor IA no respondió a tiempo.",
                    "Revisar los errores críticos en el reporte.",
                    "Reintentar más tarde.",
                ],
                "tiempo_estimado": "No disponible",
            }
        finally:
            asyncio.set_event_loop(None)
            loop.close()
