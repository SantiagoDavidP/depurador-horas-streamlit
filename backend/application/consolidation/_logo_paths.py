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



class LogoPathsMixin:
    def _resolve_logo_path(self, logo_path: Optional[Path]) -> Optional[Path]:
        """
        Resuelve la ruta del logo.

        Args:
            logo_path: Ruta proporcionada o None

        Returns:
            Path al logo si existe, None en caso contrario
        """
        if logo_path and logo_path.exists():
            return logo_path

        # Buscar en ubicaciones estándar
        module_dir = Path(__file__).resolve().parents[2]
        project_root = module_dir.parent

        # Regresar al comportamiento base: logo principal Business IT (logobit)
        preferred_names = ["logobit.png", "Logo.png", "logo.png"]
        for name in preferred_names:
            for candidate in (
                module_dir / name,
                module_dir / "application" / name,
                project_root / "frontend" / name,
                project_root / name,
            ):
                if candidate.exists():
                    logger.info("Logo principal encontrado en: %s", candidate)
                    return candidate

        # Ubicaciones posibles
        possible_paths = [
            module_dir / "logobit.png",
            module_dir / "application" / "logobit.png",
            project_root / "frontend" / "logo.png",
            project_root / "assets" / "logo.png",
            project_root / "logo.png",
        ]

        for path in possible_paths:
            if path.exists():
                logger.info("Logo encontrado en: %s", path)
                return path

        logger.warning("No se encontró logo.png en ubicaciones estándar")
        return None

    def _resolve_client_logo_path(self) -> Optional[Path]:
        """Resuelve logo secundario por cliente (NOVA/BANINTER)."""
        module_dir = Path(__file__).resolve().parents[2]
        project_root = module_dir.parent
        cliente_lower = (self.cliente or "").lower()

        if any(k in cliente_lower for k in ["baninter", "banco internacional"]):
            names = ["BANINTER.png", "baninter.png"]
        else:
            names = ["NOVA.png", "nova.png"]

        for name in names:
            for candidate in (project_root / name, module_dir / name, project_root / "frontend" / name):
                if candidate.exists():
                    logger.info("Logo secundario encontrado en: %s", candidate)
                    return candidate
        return None

    def _add_logo(
        self,
        ws: Worksheet,
        anchor: str = "A1",
        max_width: int = 140,
        max_height: Optional[int] = None,
        logo_path: Optional[Path] = None,
        width_cm: Optional[float] = None,
        height_cm: Optional[float] = None,
    ) -> None:
        """Agrega logo al worksheet si existe uno configurado."""
        path = logo_path or self.logo_path
        if not path or not path.exists():
            return
        try:
            img = Image(str(path))
            if not img.width or not img.height:
                return

            if width_cm and height_cm and width_cm > 0 and height_cm > 0:
                # openpyxl usa pixeles en Image.width/height
                img.width = int(round(width_cm * 37.795))
                img.height = int(round(height_cm * 37.795))
            else:
                width_scale = max_width / float(img.width)
                height_scale = (
                    (max_height / float(img.height))
                    if max_height and max_height > 0
                    else width_scale
                )
                scale = min(width_scale, height_scale)
                img.width = int(img.width * scale)
                img.height = int(img.height * scale)
            img.anchor = anchor
            ws.add_image(img)
        except Exception as exc:
            logger.warning("No se pudo agregar logo (%s): %s", path, exc)
