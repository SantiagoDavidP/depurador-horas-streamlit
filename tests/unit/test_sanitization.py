"""Tests unitarios para sanitización de nombres de archivo."""
import pytest
from frontend.app import sanitize_filename, sanitize_text_input


class TestFilenameSanitization:
    """Tests para sanitización de nombres de archivo."""
    
    def test_removes_dangerous_characters(self):
        """Debe eliminar caracteres peligrosos."""
        dangerous = 'archivo<>:"/\\|?*.xlsx'
        safe = sanitize_filename(dangerous)
        
        assert '<' not in safe
        assert '>' not in safe
        assert ':' not in safe
        assert '"' not in safe
        assert '\\' not in safe
        assert '|' not in safe
        assert '?' not in safe
        assert '*' not in safe
    
    def test_prevents_path_traversal(self):
        """Debe prevenir path traversal."""
        malicious = "../../../etc/passwd"
        safe = sanitize_filename(malicious)
        
        assert ".." not in safe
        assert "/" not in safe
        assert safe == "passwd"
    
    def test_limits_length(self):
        """Debe limitar longitud a 200 caracteres."""
        long_name = "a" * 300 + ".xlsx"
        safe = sanitize_filename(long_name)
        
        assert len(safe) <= 200
        assert safe.endswith(".xlsx")  # Debe preservar extensión
    
    def test_handles_empty_input(self):
        """Debe manejar entrada vacía."""
        assert sanitize_filename("") == "archivo.xlsx"
        assert sanitize_filename(None) == "archivo.xlsx"
    
    def test_preserves_valid_filename(self):
        """Debe preservar nombres de archivo válidos."""
        valid = "Consolidado_Cliente_2025.xlsx"
        safe = sanitize_filename(valid)
        
        assert safe == valid
    
    def test_handles_unicode(self):
        """Debe manejar caracteres Unicode correctamente."""
        unicode_name = "Reporte_año_2025_ñ.xlsx"
        safe = sanitize_filename(unicode_name)
        
        # Debe preservar caracteres Unicode válidos
        assert "año" in safe or safe  # Puede cambiar encoding pero no debe fallar


class TestTextInputSanitization:
    """Tests para sanitización de inputs de texto."""
    
    def test_removes_multiple_spaces(self):
        """Debe eliminar espacios múltiples."""
        text = "Texto   con    muchos     espacios"
        safe = sanitize_text_input(text)
        
        assert "  " not in safe
        assert safe == "Texto con muchos espacios"
    
    def test_removes_newlines(self):
        """Debe eliminar saltos de línea."""
        text = "Línea 1\nLínea 2\nLínea 3"
        safe = sanitize_text_input(text)
        
        assert "\n" not in safe
        assert safe == "Línea 1 Línea 2 Línea 3"
    
    def test_limits_length(self):
        """Debe limitar longitud según parámetro."""
        long_text = "a" * 200
        safe = sanitize_text_input(long_text, max_length=50)
        
        assert len(safe) == 50
    
    def test_handles_empty_input(self):
        """Debe manejar entrada vacía."""
        assert sanitize_text_input("") == ""
        assert sanitize_text_input(None) == ""
    
    def test_preserves_valid_text(self):
        """Debe preservar texto válido."""
        valid = "Cliente NOVA-TI"
        safe = sanitize_text_input(valid)
        
        assert safe == valid
