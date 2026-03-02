from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .individual_sheet import IndividualSheetMixin
from .logo_ops import LogoOpsMixin
from .metrics import MetricsMixin
from .models import ConsultorMetrics
from .postprocess import PostprocessMixin
from .summary_sheet import SummarySheetMixin


class TimeSheetConsolidator(
    LogoOpsMixin,
    MetricsMixin,
    SummarySheetMixin,
    IndividualSheetMixin,
    PostprocessMixin,
):
    """
    Consolidador de reportes de actividades de multiples consultores.

    Toma los resultados procesados del BatchProcessor y genera un archivo
    Excel profesional con resumen ejecutivo y hojas individuales.
    """

    TARIFAS = {
        "Senior": {"mensual": 2770, "hora_extra": 25},
        "Semisenior": {"mensual": 2320, "hora_extra": 22},
        "Junior": {"mensual": 1670, "hora_extra": 20},
    }

    def __init__(self, cliente: str = "NOVA - TI", logo_path: Optional[Path] = None):
        """
        Inicializa el consolidador.

        Args:
            cliente: Nombre del cliente para el encabezado
            logo_path: Ruta al logo (PNG). Si None, busca en frontend/logo.png
        """
        self.cliente = cliente
        self.consultores_metrics: List[ConsultorMetrics] = []
        self.logo_path = self._resolve_logo_path(logo_path)
        self.client_logo_path = self._resolve_client_logo_path()


__all__ = ["TimeSheetConsolidator"]
