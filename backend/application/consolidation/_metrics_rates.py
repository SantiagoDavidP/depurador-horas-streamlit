from __future__ import annotations

import io
import logging
import re
from copy import copy
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from openpyxl import Workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.drawing.image import Image
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.utils import get_column_letter, column_index_from_string
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.worksheet import Worksheet

from backend.domain.rates.collaborator_rates import get_collaborator_rates_manager

from .models import ConsultorMetrics, ConsolidatedReport
from .styles import *

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None  # type: ignore

logger = logging.getLogger(__name__)



class MetricsRatesMixin:
    def _inferir_cargo(self, nombre: str, metadata: Dict[str, object]) -> str:
        """
        Infiere el cargo del consultor de forma automática.
        
        Prioridad:
        1. Buscar en collaborator_rates.json (si existe el colaborador)
        2. Metadata del archivo (campo "cargo" o "role")
        3. Metadata de rol detectado desde actividades
        4. Default "Junior" (conservador)

        Args:
            nombre: Nombre del consultor
            metadata: Metadata del archivo

        Returns:
            Cargo: Senior, Semisenior o Junior
        """
        # 1. PRIMERO: Intentar obtener desde collaborator_rates.json
        rates_manager = get_collaborator_rates_manager()
        collab = rates_manager.find_collaborator(nombre)
        
        if collab:
            # Encontrado en JSON - usar su seniority
            if collab.cargo:
                logger.info(f"Cargo de {nombre} obtenido de collaborator_rates: {collab.cargo}")
                return collab.cargo
            logger.info(f"Seniority de {nombre} obtenido de collaborator_rates: {collab.seniority}")
            return collab.seniority
        
        # 2. Buscar en metadata del archivo
        if "cargo" in metadata:
            cargo = str(metadata["cargo"]).strip()
            logger.info(f"Seniority de {nombre} obtenido de metadata 'cargo': {cargo}")
            return cargo
            
        if "role" in metadata:
            role = str(metadata["role"]).strip()
            logger.info(f"Seniority de {nombre} obtenido de metadata 'role': {role}")
            return role
        
        if "seniority" in metadata:
            seniority = str(metadata["seniority"]).strip()
            logger.info(f"Seniority de {nombre} obtenido de metadata 'seniority': {seniority}")
            return seniority
        
        # 3. Intentar inferir desde rol detectado en validaciones (si existe)
        if "detected_role" in metadata:
            detected_role = str(metadata["detected_role"]).strip().lower()
            # Mapeo básico de roles a seniority
            role_to_seniority = {
                "senior developer": "Senior",
                "lead developer": "Senior",
                "architect": "Senior",
                "developer": "Semisenior",
                "qa engineer": "Semisenior",
                "devops": "Semisenior",
                "junior developer": "Junior",
                "qa junior": "Junior",
                "intern": "Junior",
            }
            for role_key, seniority_value in role_to_seniority.items():
                if role_key in detected_role:
                    logger.info(f"Seniority de {nombre} inferido de rol detectado: {seniority_value}")
                    return seniority_value
        
        # 4. DEFAULT: Usar Junior como opción conservadora
        logger.warning(
            f"No se pudo determinar seniority para '{nombre}'. "
            f"Usando default 'Junior'. Considera agregarlo a collaborator_rates.json"
        )
        return "Junior"

    def _calcular_dias_laborables(
        self, year: Optional[int], month_name: Optional[str]
    ) -> int:
        """
        Calcula días laborables del mes (L-V, excluyendo feriados).

        Args:
            year: Año
            month_name: Nombre del mes en inglés

        Returns:
            Número de días laborables
        """
        if not year or not month_name:
            return 22  # Valor por defecto

        try:
            # Convertir nombre del mes a número
            month = datetime.strptime(month_name, "%B").month
        except ValueError:
            return 22

        # Importar función de validators
        from backend.domain.validation.validators import get_working_days_in_period

        working_days = get_working_days_in_period(year, month)
        return len(working_days)

    def _get_sorted_metrics(
        self, metrics_list: Optional[List["ConsultorMetrics"]] = None
    ) -> List["ConsultorMetrics"]:
        """Ordena consultores por cargo (Senior -> Semisenior -> Junior) y nombre."""
        metrics_list = metrics_list or self.consultores_metrics

        def _normalize_seniority(value: object) -> str:
            text = str(value or "").strip().lower()
            if "semi" in text:
                return "Semisenior"
            if "senior" in text:
                return "Senior"
            if "junior" in text:
                return "Junior"
            return str(value or "").strip() or "Junior"

        seniority_order = {"Senior": 1, "Semisenior": 2, "Junior": 3}
        return sorted(
            metrics_list,
            key=lambda m: (seniority_order.get(_normalize_seniority(m.cargo), 4), m.nombre),
        )
