from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from backend.application.tabular.table_data import TableData


@dataclass
class ConsultorMetrics:
    """Métricas calculadas para un consultor."""

    nombre: str
    cargo: str
    dias_laborados: int
    total_horas_normales: float
    total_horas_extras: float
    valor_tarifa: float
    valor_dia: float
    total_facturar: float
    valor_hora_extra: float
    total_horas_extras_facturar: float
    dataframe: TableData
    metadata: Dict[str, object]


@dataclass
class ConsolidatedReport:
    """Resultado del proceso de consolidación."""

    workbook_bytes: bytes
    output_filename: str
    consultores_incluidos: int
    total_facturar: float
    total_horas: float
    periodo: str
    dias_laborables: int

__all__ = ["ConsultorMetrics", "ConsolidatedReport"]
