import os
from unittest.mock import MagicMock, patch

import pytest

from apps.backend.adapters.factory import AdapterFactory
from apps.backend.adapters.mock import MockModelAdapter
from apps.backend.adapters.real import RealModelAdapter
from packages.llm.exceptions import LLMError
from packages.llm.models.prompt import Prompt
from packages.llm.models.response import LLMResponse


def test_factory_returns_mock_adapter_for_mock_target():
    adapter = AdapterFactory.get_adapter("mock")
    assert isinstance(adapter, MockModelAdapter)

    adapter2 = AdapterFactory.get_adapter("mocked")
    assert isinstance(adapter2, MockModelAdapter)


def test_get_available_models_delegates_to_registry():
    models = AdapterFactory.get_available_models()
    assert isinstance(models, list)
    assert len(models) > 0

    providers = {m["provider"] for m in models}
    assert "groq" in providers
    assert "gemini" in providers

    for model in models:
        assert "provider" in model
        assert "model" in model
        assert "available" in model
        assert "status" in model


def test_get_available_models_entries_have_frontend_mapping_fields():
    models = AdapterFactory.get_available_models()
    for model in models:
        assert "display_name" in model
        assert "capabilities" in model
        assert isinstance(model["capabilities"], list)


def test_factory_returns_real_adapter_for_real_targets():
    adapter_gemini = AdapterFactory.get_adapter("gemini-2.5-flash")
    assert isinstance(adapter_gemini, RealModelAdapter)

    adapter_grok = AdapterFactory.get_adapter("grok-2")
    assert isinstance(adapter_grok, RealModelAdapter)

    adapter_mistral = AdapterFactory.get_adapter("mistral-large-latest")
    assert isinstance(adapter_mistral, RealModelAdapter)

    adapter_groq = AdapterFactory.get_adapter("groq/llama-3.3-70b-versatile")
    assert isinstance(adapter_groq, RealModelAdapter)

    adapter_nvidia = AdapterFactory.get_adapter("nvidia/meta/llama-3.1-405b-instruct")
    assert isinstance(adapter_nvidia, RealModelAdapter)


def test_missing_api_credentials_fails_clearly():
    with patch.dict(os.environ, {}, clear=True):
        adapter = RealModelAdapter(target_model="gemini-2.5-flash")
        with pytest.raises(LLMError) as exc_info:
            adapter.predict("Test prompt")
        assert "API key" in str(exc_info.value) or "unavailable" in str(exc_info.value)


def test_unknown_provider_fails_clearly():
    adapter = RealModelAdapter(target_model="unknown-provider-xyz-999")
    with pytest.raises(LLMError) as exc_info:
        adapter.predict("Test prompt")
    assert "Unable to resolve" in str(exc_info.value) or "Unsupported" in str(exc_info.value)


def test_successful_provider_response_converted_to_prediction_result():
    adapter = RealModelAdapter(target_model="gemini-2.5-flash")
    mock_response = LLMResponse(
        provider="gemini",
        model="gemini-2.5-flash",
        prompt_tokens=15,
        completion_tokens=25,
        total_tokens=40,
        latency_ms=120,
        response="Hello world from Gemini!",
        raw={"candidates": []},
        created_at="123456789",
    )

    with (
        patch.object(adapter.provider_adapter.clients["gemini"], "health", return_value=True),
        patch.object(
            adapter.provider_adapter.clients["gemini"], "generate", return_value=mock_response
        ),
    ):
        result = adapter.predict("Say hello")
        assert result.output_text == "Hello world from Gemini!"
        assert result.latency_ms == 120
        assert result.token_usage == 40
        assert result.raw_response == {"candidates": []}


def test_transient_error_retry_and_eventual_success():
    adapter = RealModelAdapter(target_model="grok-2", max_retries=2, backoff_factor=0.01)
    mock_response = LLMResponse(
        provider="grok",
        model="grok-2",
        prompt_tokens=10,
        completion_tokens=10,
        total_tokens=20,
        latency_ms=200,
        response="Success after retry",
        raw={},
        created_at="12345",
    )

    mock_client = MagicMock()
    mock_client.health.return_value = True
    mock_client.generate.side_effect = [
        LLMError("503 Server Error: Service Unavailable"),
        mock_response,
    ]

    with (
        patch.object(
            adapter.provider_adapter, "resolve_provider_and_model", return_value=("grok", "grok-2")
        ),
        patch.object(adapter.provider_adapter, "get_client", return_value=mock_client),
    ):
        result = adapter.predict("Retry prompt")
        assert result.output_text == "Success after retry"
        assert mock_client.generate.call_count == 2


def test_exceeding_max_retries_raises_llm_error():
    adapter = RealModelAdapter(
        target_model="mistral-large-latest", max_retries=1, backoff_factor=0.01
    )
    mock_client = MagicMock()
    mock_client.health.return_value = True
    mock_client.generate.side_effect = LLMError("504 Gateway Timeout")

    with (
        patch.object(
            adapter.provider_adapter,
            "resolve_provider_and_model",
            return_value=("mistral", "mistral-large-latest"),
        ),
        patch.object(adapter.provider_adapter, "get_client", return_value=mock_client),
    ):
        with pytest.raises(LLMError) as exc_info:
            adapter.predict("Timeout prompt")
        assert "Execution failed" in str(exc_info.value)
        assert mock_client.generate.call_count == 2
