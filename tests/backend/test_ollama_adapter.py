import pytest
from unittest.mock import patch, MagicMock
from apps.backend.adapters.ollama import OllamaAdapter
import urllib.error

@pytest.fixture
def adapter():
    return OllamaAdapter(target_model="llama3.2:1b")

@patch("urllib.request.urlopen")
def test_ollama_predict_success(mock_urlopen, adapter):
    mock_response = MagicMock()
    # Mocking standard Ollama API JSON response
    mock_response.read.return_value = b'{"response": "hello world", "eval_count": 14}'
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    result = adapter.predict("say hi")
    assert result.output_text == "hello world"
    assert result.token_usage == 14
    assert result.latency_ms >= 0

@patch("urllib.request.urlopen")
def test_ollama_predict_timeout(mock_urlopen, adapter):
    mock_urlopen.side_effect = urllib.error.URLError("Timeout")
    
    result = adapter.predict("say hi")
    assert "Error: Could not reach Ollama" in result.output_text
    assert result.token_usage == 0
    assert result.latency_ms >= 0

@patch("urllib.request.urlopen")
def test_ollama_discovery(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"models": [{"name": "llama3.2:1b", "size": 12345}]}'
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    models = OllamaAdapter.get_available_models()
    assert len(models) == 1
    assert models[0]["id"] == "ollama/llama3.2:1b"
