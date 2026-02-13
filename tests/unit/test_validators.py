"""Tests unitarios para el módulo de validadores."""
import pytest
import pandas as pd
from datetime import datetime

from backend.validators import (
    validate_calendar_constraints,
    validate_daily_hours,
    validate_mapping,
    ValidationIssue,
)


class TestCalendarValidation:
    """Tests para validación de restricciones de calendario."""
    
    def test_weekend_detection(self, sample_weekend_dataframe):
        """Debe detectar registros en fin de semana."""
        issues = validate_calendar_constraints(
            sample_weekend_dataframe,
            date_column='Fecha'
        )
        
        assert len(issues) == 2
        assert all(issue['tipo_error'] == 'fin_semana' for issue in issues)
    
    def test_valid_weekday(self, sample_dataframe):
        """No debe generar errores para días laborables válidos."""
        issues = validate_calendar_constraints(
            sample_dataframe,
            date_column='Fecha'
        )
        
        # Filtramos solo errores de fin de semana
        weekend_issues = [i for i in issues if i['tipo_error'] == 'fin_semana']
        assert len(weekend_issues) == 0
    
    def test_invalid_date_format(self):
        """Debe detectar fechas con formato inválido."""
        df = pd.DataFrame({
            'Fecha': ['fecha-invalida', '99/99/9999'],
            'Horas': [8.0, 8.0]
        })
        
        issues = validate_calendar_constraints(df, date_column='Fecha')
        
        assert len(issues) >= 2
        assert all(issue['tipo_error'] == 'fecha_invalida' for issue in issues)


class TestDailyHoursValidation:
    """Tests para validación de horas diarias."""
    
    def test_correct_hours(self, sample_dataframe):
        """No debe generar errores para horas correctas (8h por día)."""
        issues = validate_daily_hours(
            sample_dataframe,
            date_column='Fecha',
            hours_column='Horas',
            expected_hours=8.0
        )
        
        assert len(issues) == 0
    
    def test_excessive_hours(self):
        """Debe detectar horas excesivas por día."""
        df = pd.DataFrame({
            'Fecha': ['2025-01-13'],
            'Horas': [15.0]
        })
        
        issues = validate_daily_hours(
            df,
            date_column='Fecha',
            hours_column='Horas',
            expected_hours=8.0
        )
        
        assert len(issues) > 0
        assert any(issue['tipo_error'] == 'horas_excesivas' for issue in issues)
    
    def test_very_low_hours(self):
        """Debe detectar horas muy bajas (menos de 1 hora)."""
        df = pd.DataFrame({
            'Fecha': ['2025-01-13'],
            'Horas': [0.5]
        })
        
        issues = validate_daily_hours(
            df,
            date_column='Fecha',
            hours_column='Horas',
            expected_hours=8.0
        )
        
        assert len(issues) > 0
        assert any(issue['tipo_error'] == 'horas_muy_bajas' for issue in issues)


class TestMappingValidation:
    """Tests para validación de mapeo de columnas."""
    
    def test_valid_mapping(self, sample_dataframe):
        """No debe lanzar excepción con mapeo válido."""
        # No debe lanzar excepción
        validate_mapping(
            sample_dataframe,
            date_col='Fecha',
            hours_col='Horas',
            description_col='Descripción'
        )
    
    def test_missing_columns(self, sample_dataframe):
        """Debe lanzar ValueError si falta alguna columna requerida."""
        with pytest.raises(ValueError, match="no contiene las columnas requeridas"):
            validate_mapping(
                sample_dataframe,
                date_col='FechaInexistente',
                hours_col='Horas',
                description_col='Descripción'
            )
    
    def test_invalid_data_ratio(self):
        """Debe lanzar ValueError si hay muy pocos datos válidos."""
        df = pd.DataFrame({
            'Fecha': [None, None, '2025-01-13'],
            'Horas': [None, None, 8.0],
            'Descripción': ['', '', 'Solo una válida']
        })
        
        with pytest.raises(ValueError, match="datos válidos según el mapeo"):
            validate_mapping(
                df,
                date_col='Fecha',
                hours_col='Horas',
                description_col='Descripción',
                minimum_valid_ratio=0.8
            )


class TestHolidayCaching:
    """Tests para verificar el caching de feriados."""
    
    def test_holiday_function_is_cached(self):
        """Verificar que _get_ec_holidays está usando lru_cache."""
        from backend.validators import _get_ec_holidays
        
        # Verificar que tiene el atributo cache_info de lru_cache
        assert hasattr(_get_ec_holidays, 'cache_info')
        
        # Limpiar caché
        _get_ec_holidays.cache_clear()
        
        # Primera llamada
        result1 = _get_ec_holidays(2025)
        info1 = _get_ec_holidays.cache_info()
        
        # Segunda llamada (debe usar caché)
        result2 = _get_ec_holidays(2025)
        info2 = _get_ec_holidays.cache_info()
        
        assert result1 == result2
        assert info2.hits > info1.hits  # Debe haber un hit de caché
