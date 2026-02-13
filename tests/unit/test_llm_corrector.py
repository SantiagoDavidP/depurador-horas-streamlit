"""Tests unitarios para el módulo LLM Corrector."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.llm_corrector import LLMCorrector, CorrectionResult


class TestInputSanitization:
    """Tests para la sanitización de inputs."""
    
    def test_sanitize_removes_newlines(self):
        """Debe eliminar saltos de línea múltiples."""
        text = "Línea 1\n\n\nLínea 2\nLínea 3"
        sanitized = LLMCorrector._sanitize_input(text)
        
        assert "\n" not in sanitized
        assert "Línea 1 Línea 2 Línea 3" == sanitized
    
    def test_sanitize_limits_length(self):
        """Debe limitar la longitud del texto."""
        long_text = "A" * 500
        sanitized = LLMCorrector._sanitize_input(long_text, max_length=100)
        
        assert len(sanitized) == 100
    
    def test_sanitize_handles_empty_input(self):
        """Debe manejar entrada vacía."""
        assert LLMCorrector._sanitize_input("") == "No especificado"
        assert LLMCorrector._sanitize_input(None) == "No especificado"
    
    def test_sanitize_removes_control_characters(self):
        """Debe eliminar caracteres de control."""
        text = "Normal\ttext\rwith\x00controls"
        sanitized = LLMCorrector._sanitize_input(text)
        
        assert "\t" not in sanitized
        assert "\r" not in sanitized
        assert "\x00" not in sanitized


class TestLLMCorrectorNormalization:
    """Tests para normalización de textos."""
    
    def test_normalize_basic(self):
        """Debe normalizar texto básico."""
        text = "  Texto con ESPACIOS  "
        normalized = LLMCorrector._normalize(text)
        
        assert normalized == "texto con espacios"
    
    def test_normalize_preserves_content(self):
        """La normalización no debe cambiar el contenido significativo."""
        text = "Desarrollo de Feature X"
        normalized = LLMCorrector._normalize(text)
        
        assert "desarrollo" in normalized
        assert "feature" in normalized


class TestCorrectionDeduplication:
    """Tests para deduplicación de correcciones."""
    
    @pytest.mark.asyncio
    async def test_deduplication_reduces_llm_calls(self):
        """Textos duplicados normalizados solo deben procesarse una vez."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"texto_corregido": "test"}'
        mock_client.chat.completions.create.return_value = mock_response
        
        corrector = LLMCorrector(client=mock_client, batch_size=10)
        
        # Textos duplicados (misma normalización)
        rows = [
            (1, "  Desarrollo  "),
            (2, "desarrollo"),
            (3, "  DESARROLLO  "),
        ]
        
        with patch.object(corrector, '_parse_llm_response', return_value={'texto_corregido': 'Desarrollo'}):
            results = corrector.correct_descriptions(rows, role="Dev", project="Test")
        
        # Debe haber 3 resultados pero solo 1 llamada al LLM
        assert len(results) == 3
        # Las filas deben coincidir
        assert results[0].fila == 1
        assert results[1].fila == 2
        assert results[2].fila == 3


@pytest.mark.asyncio
async def test_llm_error_handling():
    """Debe manejar errores de LLM correctamente."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")
    
    corrector = LLMCorrector(client=mock_client)
    
    # No debe lanzar excepción, debe devolver texto original
    result = await corrector._correct_text("test", "role", "project")
    
    assert result['texto_corregido'] == "test"
    assert result['cambios_realizados'] == []
