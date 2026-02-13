"""Configuración de fixtures compartidas para pytest."""
import sys
from pathlib import Path

import pytest
import pandas as pd

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def sample_dataframe():
    """DataFrame de ejemplo para tests."""
    return pd.DataFrame({
        'Fecha': ['2025-01-13', '2025-01-14', '2025-01-15'],
        'Horas': [8.0, 8.0, 8.0],
        'Descripción': ['Desarrollo feature X', 'Code review', 'Testing módulo Y'],
        'Proyecto': ['Proyecto A', 'Proyecto A', 'Proyecto A']
    })


@pytest.fixture
def sample_weekend_dataframe():
    """DataFrame con fechas de fin de semana para tests."""
    return pd.DataFrame({
        'Fecha': ['2025-01-11', '2025-01-12'],  # Sábado y Domingo
        'Horas': [8.0, 8.0],
        'Descripción': ['Trabajo fin de semana', 'Trabajo domingo']
    })


@pytest.fixture
def sample_invalid_hours_dataframe():
    """DataFrame con horas inválidas para tests."""
    return pd.DataFrame({
        'Fecha': ['2025-01-13', '2025-01-14', '2025-01-15'],
        'Horas': [15.0, -2.0, 0.5],  # Horas excesivas, negativas, muy bajas
        'Descripción': ['Trabajo excesivo', 'Error negativo', 'Muy poco tiempo']
    })
