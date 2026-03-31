"""Tests for OllamaClient — mocks httpx to avoid real HTTP calls."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from piv_oac.client.ollama_client import OllamaClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_httpx_response(data: dict, status_code: int = 200):
    """Build a minimal mock of an httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = json.dumps(data)
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        import httpx
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    return resp


class _FakeAsyncContextManager:
    """Async context manager that returns a mock HTTP client."""

    def __init__(self, client):
        self._client = client

    async def __aenter__(self):
        return self._client

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

class TestOllamaClientInstantiation:
    def test_default_endpoint(self):
        client = OllamaClient()
        assert client._endpoint == "http://localhost:11434"

    def test_custom_endpoint(self):
        client = OllamaClient(endpoint="http://myserver:11434")
        assert client._endpoint == "http://myserver:11434"

    def test_trailing_slash_stripped(self):
        client = OllamaClient(endpoint="http://myserver:11434/")
        assert client._endpoint == "http://myserver:11434"

    def test_default_timeout(self):
        client = OllamaClient()
        assert client._timeout == 300.0

    def test_custom_timeout(self):
        client = OllamaClient(timeout=60.0)
        assert client._timeout == 60.0


# ---------------------------------------------------------------------------
# complete()
# ---------------------------------------------------------------------------

class TestOllamaClientComplete:
    def _mock_http(self, response_data: dict, status_code: int = 200):
        resp = _make_httpx_response(response_data, status_code)
        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=resp)
        return _FakeAsyncContextManager(mock_http_client), mock_http_client

    @pytest.mark.asyncio
    async def test_complete_returns_tuple(self):
        data = {"message": {"content": "Ollama says hello"}, "prompt_eval_count": 7, "eval_count": 12}
        ctx, _ = self._mock_http(data)
        with patch("piv_oac.client.ollama_client.httpx.AsyncClient", return_value=ctx):
            client = OllamaClient()
            text, tok_in, tok_out = await client.complete("sys", "usr", model="llama3.1:8b")
        assert text == "Ollama says hello"
        assert tok_in == 7
        assert tok_out == 12

    @pytest.mark.asyncio
    async def test_complete_posts_to_correct_url(self):
        data = {"message": {"content": "ok"}, "prompt_eval_count": 1, "eval_count": 1}
        ctx, mock_client = self._mock_http(data)
        with patch("piv_oac.client.ollama_client.httpx.AsyncClient", return_value=ctx):
            client = OllamaClient(endpoint="http://gpu-box:11434")
            await client.complete("sys", "usr", model="llama3.1:70b")
        mock_client.post.assert_called_once()
        url = mock_client.post.call_args.args[0]
        assert url == "http://gpu-box:11434/api/chat"

    @pytest.mark.asyncio
    async def test_complete_sends_correct_payload(self):
        data = {"message": {"content": "ok"}, "prompt_eval_count": 0, "eval_count": 0}
        ctx, mock_client = self._mock_http(data)
        with patch("piv_oac.client.ollama_client.httpx.AsyncClient", return_value=ctx):
            client = OllamaClient()
            await client.complete("System prompt", "User message", model="llama3.1:8b", max_tokens=512)
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["model"] == "llama3.1:8b"
        assert payload["stream"] is False
        assert payload["options"]["num_predict"] == 512
        assert payload["messages"][0] == {"role": "system", "content": "System prompt"}
        assert payload["messages"][1] == {"role": "user", "content": "User message"}

    @pytest.mark.asyncio
    async def test_complete_missing_token_fields_default_to_zero(self):
        data = {"message": {"content": "response"}}  # no token counts
        ctx, _ = self._mock_http(data)
        with patch("piv_oac.client.ollama_client.httpx.AsyncClient", return_value=ctx):
            client = OllamaClient()
            text, tok_in, tok_out = await client.complete("s", "u", model="llama3.1:8b")
        assert tok_in == 0
        assert tok_out == 0

    @pytest.mark.asyncio
    async def test_complete_missing_message_returns_empty_string(self):
        data = {"prompt_eval_count": 5, "eval_count": 3}  # no message field
        ctx, _ = self._mock_http(data)
        with patch("piv_oac.client.ollama_client.httpx.AsyncClient", return_value=ctx):
            client = OllamaClient()
            text, _, _ = await client.complete("s", "u", model="llama3.1:8b")
        assert text == ""

    @pytest.mark.asyncio
    async def test_complete_http_error_propagates(self):
        import httpx
        data = {}
        ctx, _ = self._mock_http(data, status_code=500)
        with patch("piv_oac.client.ollama_client.httpx.AsyncClient", return_value=ctx):
            client = OllamaClient()
            with pytest.raises(httpx.HTTPStatusError):
                await client.complete("s", "u", model="llama3.1:8b")

    @pytest.mark.asyncio
    async def test_uses_configured_timeout(self):
        data = {"message": {"content": "ok"}, "prompt_eval_count": 0, "eval_count": 0}
        ctx, _ = self._mock_http(data)
        with patch("piv_oac.client.ollama_client.httpx.AsyncClient", return_value=ctx) as mock_cls:
            client = OllamaClient(timeout=42.0)
            await client.complete("s", "u", model="llama3.1:8b")
        mock_cls.assert_called_with(timeout=42.0)
