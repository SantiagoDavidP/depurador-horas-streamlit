import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.infrastructure.ai.llm_corrector import LLMCorrector


@pytest.mark.unit
def test_sanitize_input_normalizes_whitespace_and_limits_length():
    text = "Linea 1\n\nLinea 2\t\tLinea 3"
    sanitized = LLMCorrector._sanitize_input(text, max_length=12)
    assert "\n" not in sanitized
    assert "\t" not in sanitized
    assert len(sanitized) == 12


@pytest.mark.unit
def test_sanitize_input_handles_empty():
    assert LLMCorrector._sanitize_input("") == "No especificado"
    assert LLMCorrector._sanitize_input(None) == "No especificado"


@pytest.mark.unit
def test_parse_llm_response_supports_json_in_markdown():
    content = """```json
    {"texto_corregido":"Texto final","cambios_realizados":["tilde"]}
    ```"""
    parsed = LLMCorrector._parse_llm_response(content, original_text="Texto original")
    assert parsed["texto_corregido"] == "Texto final"
    assert parsed["cambios_realizados"] == ["tilde"]


@pytest.mark.unit
def test_parse_llm_response_falls_back_to_original_text():
    parsed = LLMCorrector._parse_llm_response("", original_text="Original")
    assert parsed["texto_corregido"] == "Original"


@pytest.mark.unit
def test_correct_text_returns_default_result_when_llm_fails():
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("boom")
    corrector = LLMCorrector(client=mock_client, enable_cache=False)
    result = asyncio.run(corrector._correct_texts_batch(["texto"], "Dev", "Proyecto"))
    parsed = result["texto"]
    assert parsed["texto_corregido"] == "texto"
    assert parsed["cambios_realizados"] == []


@pytest.mark.unit
def test_correct_descriptions_deduplicates_by_normalized_text():
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = (
        '{"resultados":[{"id":0,"texto_corregido":"Desarrollo base","cambios_realizados":["capitalizacion"]}]}'
    )
    mock_client.chat.completions.create.return_value = mock_response
    corrector = LLMCorrector(client=mock_client, enable_cache=False, batch_size=10)

    rows = [(1, "desarrollo base modulo"), (2, "desarrollo base modulo")]

    with patch.object(
        corrector,
        "_parse_llm_batch_response",
        return_value={
            "resultados": [
                {
                    "id": 0,
                    "texto_corregido": "Desarrollo base modulo",
                    "cambios_realizados": ["capitalizacion"],
                }
            ]
        },
    ):
        result = corrector.correct_descriptions(rows, role="Dev", project="Core")

    assert len(result) == 2
    assert result[0].corrected_text == "Desarrollo base modulo"
    assert result[1].corrected_text == "Desarrollo base modulo"
