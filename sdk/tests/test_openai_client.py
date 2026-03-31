"""Tests for OpenAIClient — mocks openai package to avoid optional dep."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_openai_response(text: str, tokens_in: int, tokens_out: int):
    """Build a minimal mock of an openai ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = text

    usage = MagicMock()
    usage.prompt_tokens = tokens_in
    usage.completion_tokens = tokens_out

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


def _patch_openai(available: bool = True):
    """Context manager that stubs the openai module."""
    if available:
        mock_module = MagicMock()
        mock_module.AsyncOpenAI = MagicMock
        return patch.dict(sys.modules, {"openai": mock_module})
    # Simulate openai not installed
    return patch.dict(sys.modules, {"openai": None})


# ---------------------------------------------------------------------------
# Import guard
# ---------------------------------------------------------------------------

class TestOpenAIClientImportGuard:
    def test_raises_import_error_when_openai_not_installed(self, monkeypatch):
        """OpenAIClient raises ImportError with install hint when openai absent."""
        import importlib
        import piv_oac.client.openai_client as mod

        monkeypatch.setattr(mod, "_OPENAI_AVAILABLE", False)
        with pytest.raises(ImportError, match="pip install piv-oac\\[openai\\]"):
            mod.OpenAIClient()

    def test_no_error_when_openai_available(self, monkeypatch):
        """OpenAIClient instantiates without error when openai is available."""
        import piv_oac.client.openai_client as mod

        fake_async_openai = MagicMock()
        monkeypatch.setattr(mod, "_OPENAI_AVAILABLE", True)
        monkeypatch.setattr(mod, "_openai_module", MagicMock(AsyncOpenAI=fake_async_openai))
        client = mod.OpenAIClient(api_key="test-key")
        assert client is not None


# ---------------------------------------------------------------------------
# complete()
# ---------------------------------------------------------------------------

class TestOpenAIClientComplete:
    def _make_client(self, monkeypatch, response_text="hello", tokens_in=5, tokens_out=10):
        import piv_oac.client.openai_client as mod

        mock_response = _make_openai_response(response_text, tokens_in, tokens_out)
        mock_async_client = MagicMock()
        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_response)

        fake_module = MagicMock()
        fake_module.AsyncOpenAI.return_value = mock_async_client

        monkeypatch.setattr(mod, "_OPENAI_AVAILABLE", True)
        monkeypatch.setattr(mod, "_openai_module", fake_module)
        return mod.OpenAIClient(api_key="test"), mock_async_client

    @pytest.mark.asyncio
    async def test_complete_returns_tuple(self, monkeypatch):
        client, _ = self._make_client(monkeypatch, "OpenAI response", 8, 15)
        text, tok_in, tok_out = await client.complete(
            system_prompt="You are helpful",
            user_message="Hello",
            model="gpt-4o",
        )
        assert text == "OpenAI response"
        assert tok_in == 8
        assert tok_out == 15

    @pytest.mark.asyncio
    async def test_complete_passes_correct_messages(self, monkeypatch):
        client, mock_client = self._make_client(monkeypatch)
        await client.complete(
            system_prompt="System prompt here",
            user_message="User prompt here",
            model="gpt-4o-mini",
        )
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "System prompt here"}
        assert messages[1] == {"role": "user", "content": "User prompt here"}

    @pytest.mark.asyncio
    async def test_complete_passes_model(self, monkeypatch):
        client, mock_client = self._make_client(monkeypatch)
        await client.complete("sys", "usr", model="gpt-4o")
        assert mock_client.chat.completions.create.call_args.kwargs["model"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_complete_passes_max_tokens(self, monkeypatch):
        client, mock_client = self._make_client(monkeypatch)
        await client.complete("sys", "usr", model="gpt-4o", max_tokens=512)
        assert mock_client.chat.completions.create.call_args.kwargs["max_tokens"] == 512

    @pytest.mark.asyncio
    async def test_complete_empty_choices_raises_runtime_error(self, monkeypatch):
        import piv_oac.client.openai_client as mod

        mock_response = MagicMock()
        mock_response.choices = []
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        fake_module = MagicMock()
        fake_module.AsyncOpenAI.return_value = mock_client
        monkeypatch.setattr(mod, "_OPENAI_AVAILABLE", True)
        monkeypatch.setattr(mod, "_openai_module", fake_module)

        client = mod.OpenAIClient()
        with pytest.raises(RuntimeError, match="empty choices"):
            await client.complete("sys", "usr", model="gpt-4o")

    @pytest.mark.asyncio
    async def test_complete_no_usage_returns_zeros(self, monkeypatch):
        import piv_oac.client.openai_client as mod

        choice = MagicMock()
        choice.message.content = "text"
        mock_response = MagicMock()
        mock_response.choices = [choice]
        mock_response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        fake_module = MagicMock()
        fake_module.AsyncOpenAI.return_value = mock_client
        monkeypatch.setattr(mod, "_OPENAI_AVAILABLE", True)
        monkeypatch.setattr(mod, "_openai_module", fake_module)

        client = mod.OpenAIClient()
        text, tok_in, tok_out = await client.complete("sys", "usr", model="gpt-4o")
        assert tok_in == 0
        assert tok_out == 0

    @pytest.mark.asyncio
    async def test_complete_none_content_returns_empty_string(self, monkeypatch):
        import piv_oac.client.openai_client as mod

        choice = MagicMock()
        choice.message.content = None
        usage = MagicMock()
        usage.prompt_tokens = 3
        usage.completion_tokens = 0
        mock_response = MagicMock()
        mock_response.choices = [choice]
        mock_response.usage = usage
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        fake_module = MagicMock()
        fake_module.AsyncOpenAI.return_value = mock_client
        monkeypatch.setattr(mod, "_OPENAI_AVAILABLE", True)
        monkeypatch.setattr(mod, "_openai_module", fake_module)

        client = mod.OpenAIClient()
        text, _, _ = await client.complete("sys", "usr", model="gpt-4o")
        assert text == ""
