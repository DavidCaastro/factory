"""Tests for client factory and AnthropicClient."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from piv_oac.client import get_client, LLMClient, AnthropicClient


class TestGetClient:
    def test_returns_anthropic_by_default(self):
        client = get_client("anthropic")
        assert isinstance(client, AnthropicClient)

    def test_case_insensitive(self):
        client = get_client("Anthropic")
        assert isinstance(client, AnthropicClient)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_client("unknown_provider")

    def test_error_lists_supported_providers(self):
        with pytest.raises(ValueError) as exc_info:
            get_client("magic")
        assert "anthropic" in str(exc_info.value)

    def test_returns_llm_client_protocol(self):
        client = get_client("anthropic")
        assert isinstance(client, LLMClient)


class TestAnthropicClient:
    @pytest.mark.asyncio
    async def test_complete_returns_tuple(self):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="response text")]
        mock_message.usage.input_tokens = 10
        mock_message.usage.output_tokens = 20

        with patch("anthropic.AsyncAnthropic") as mock_cls:
            instance = MagicMock()
            instance.messages.create = AsyncMock(return_value=mock_message)
            mock_cls.return_value = instance

            client = AnthropicClient(api_key="test-key")
            text, tok_in, tok_out = await client.complete(
                system_prompt="You are helpful",
                user_message="Hello",
                model="claude-sonnet-4-6",
            )

        assert text == "response text"
        assert tok_in == 10
        assert tok_out == 20

    def test_instantiation_with_none_api_key(self):
        # Should not raise — falls back to env var
        with patch("anthropic.AsyncAnthropic"):
            client = AnthropicClient(api_key=None)
            assert client is not None
