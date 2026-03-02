from __future__ import annotations

_CRITICAL_ERROR_TYPES = {
    "fecha_invalida",
    "fin_semana",
    "feriado",
    "horas_incorrectas",
    "horas_excesivas",
    "horas_muy_bajas",
    "horas_faltantes",
}

_ERROR_PRIORITY = [
    "completitud",
    "fecha_fuera_periodo",
    "fecha_invalida",
    "fin_semana",
    "feriado",
    "horas_incorrectas",
    "horas_excesivas",
    "horas_muy_bajas",
    "duplicado_exacto",
    "duplicado_similar",
    "descripcion_repetida",
]
_ERROR_PRIORITY_INDEX = {t: i for i, t in enumerate(_ERROR_PRIORITY)}
_WARNING_ERROR_TYPES = {
    "descripcion_calidad",
    "descripcion_repetida",
    "duplicado_exacto",
    "duplicado_similar",
    "proyecto_inconsistente",
}
