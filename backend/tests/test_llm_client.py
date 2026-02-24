"""
Unit Tests for LLM Client (llm_client.py)
Tests provider dispatch, model validation, error handling — using mocks.
No real API keys needed.
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import llm_client
from llm_client import call_llm, SUPPORTED_MODELS


class TestSupportedModels:
    """Validate the SUPPORTED_MODELS structure."""

    def test_all_three_providers_present(self):
        assert "openai" in SUPPORTED_MODELS
        assert "gemini" in SUPPORTED_MODELS
        assert "claude" in SUPPORTED_MODELS

    def test_openai_has_gpt52(self):
        assert "gpt-5-mini" in SUPPORTED_MODELS["openai"]

    def test_gemini_has_gemini30(self):
        assert "gemini-3.0" in SUPPORTED_MODELS["gemini"]

    def test_claude_has_sonnet_and_opus(self):
        assert "claude-sonnet-4-6" in SUPPORTED_MODELS["claude"]
        assert "claude-opus-4-5" in SUPPORTED_MODELS["claude"]

    def test_all_model_lists_are_non_empty(self):
        for provider, models in SUPPORTED_MODELS.items():
            assert len(models) > 0, f"Provider '{provider}' has no models"

    def test_model_ids_are_strings(self):
        for provider, models in SUPPORTED_MODELS.items():
            for m in models:
                assert isinstance(m, str), f"Model ID must be a string, got: {type(m)}"


class TestCallLLMValidation:
    """Test input validation in call_llm."""

    @pytest.mark.asyncio
    async def test_raises_valueerror_for_empty_api_key(self):
        with pytest.raises(ValueError, match="No API key"):
            await call_llm(provider="openai", model="gpt-5-mini", api_key="", prompt="test")

    @pytest.mark.asyncio
    async def test_raises_valueerror_for_none_api_key(self):
        with pytest.raises(ValueError, match="No API key"):
            await call_llm(provider="openai", model="gpt-5-mini", api_key=None, prompt="test")

    @pytest.mark.asyncio
    async def test_raises_valueerror_for_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            await call_llm(provider="fakeprovider", model="gpt-5-mini", api_key="sk-test", prompt="test")

    @pytest.mark.asyncio
    async def test_raises_valueerror_for_unknown_model(self):
        with pytest.raises(ValueError, match="Unknown model"):
            await call_llm(provider="openai", model="gpt-99-ultra", api_key="sk-test", prompt="test")

    @pytest.mark.asyncio
    async def test_raises_valueerror_for_mismatched_model_provider(self):
        """Claude model passed to OpenAI provider should raise."""
        with pytest.raises(ValueError, match="Unknown model"):
            await call_llm(provider="openai", model="claude-sonnet-4-6", api_key="sk-test", prompt="test")

    @pytest.mark.asyncio
    async def test_provider_normalization_uppercase(self):
        """Provider 'OpenAI' should be normalized to 'openai'."""
        with patch.object(llm_client, '_call_openai', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = '{"status": "ok"}'
            result = await call_llm(provider="OPENAI", model="gpt-5-mini", api_key="sk-test", prompt="hello")
            mock_openai.assert_called_once()
            assert result == '{"status": "ok"}'


class TestOpenAIDispatch:
    """Test OpenAI dispatch path via mocks."""

    @pytest.mark.asyncio
    async def test_calls_openai_for_openai_provider(self):
        with patch.object(llm_client, '_call_openai', new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = '{"recommendation": "BUY"}'
            result = await call_llm(
                provider="openai", model="gpt-5-mini", api_key="sk-test", prompt="Analyze RELIANCE"
            )
            mock_fn.assert_called_once()
            assert result == '{"recommendation": "BUY"}'

    @pytest.mark.asyncio
    async def test_openai_passes_image_when_provided(self):
        with patch.object(llm_client, '_call_openai', new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = '{"prediction": "UP"}'
            await call_llm(
                provider="openai", model="gpt-5-mini", api_key="sk-test",
                prompt="Analyze chart", image_b64="base64data"
            )
            call_args = mock_fn.call_args
            assert call_args[0][4] == "base64data"  # image_b64 arg


class TestGeminiDispatch:
    """Test Gemini dispatch path via mocks."""

    @pytest.mark.asyncio
    async def test_calls_gemini_for_gemini_provider(self):
        with patch.object(llm_client, '_call_gemini', new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = '{"recommendation": "HOLD"}'
            result = await call_llm(
                provider="gemini", model="gemini-3.0", api_key="AIza-test", prompt="Analyze TCS"
            )
            mock_fn.assert_called_once()
            assert result == '{"recommendation": "HOLD"}'


class TestClaudeDispatch:
    """Test Claude dispatch path via mocks."""

    @pytest.mark.asyncio
    async def test_calls_claude_for_claude_provider(self):
        with patch.object(llm_client, '_call_claude', new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = '{"recommendation": "SELL"}'
            result = await call_llm(
                provider="claude", model="claude-sonnet-4-6", api_key="sk-ant-test", prompt="Analyze INFY"
            )
            mock_fn.assert_called_once()
            assert result == '{"recommendation": "SELL"}'

    @pytest.mark.asyncio
    async def test_claude_opus_dispatches_correctly(self):
        with patch.object(llm_client, '_call_claude', new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = '{"recommendation": "BUY"}'
            result = await call_llm(
                provider="claude", model="claude-opus-4-5", api_key="sk-ant-test", prompt="Deep analysis"
            )
            mock_fn.assert_called_once()
            call_model_arg = mock_fn.call_args[0][1]  # model is 2nd positional arg
            assert call_model_arg == "claude-opus-4-5"


class TestRuntimeErrors:
    """Test that RuntimeErrors from provider calls are propagated."""

    @pytest.mark.asyncio
    async def test_openai_runtime_error_propagated(self):
        with patch.object(llm_client, '_call_openai', new_callable=AsyncMock) as mock_fn:
            mock_fn.side_effect = RuntimeError("OpenAI API returned 401 Unauthorized")
            with pytest.raises(RuntimeError, match="OpenAI"):
                await call_llm(provider="openai", model="gpt-5-mini", api_key="bad-key", prompt="test")

    @pytest.mark.asyncio
    async def test_gemini_runtime_error_propagated(self):
        with patch.object(llm_client, '_call_gemini', new_callable=AsyncMock) as mock_fn:
            mock_fn.side_effect = RuntimeError("Gemini API error")
            with pytest.raises(RuntimeError, match="Gemini"):
                await call_llm(provider="gemini", model="gemini-3.0", api_key="bad-key", prompt="test")
