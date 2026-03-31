"""
PIV/OAC SDK — OllamaClient.

Wraps httpx.AsyncClient to call a local Ollama server via its REST API
(/api/chat endpoint). Status: EXPERIMENTAL.

Default endpoint: http://localhost:11434
Override via the ``endpoint`` constructor argument or the project_spec.md
provider.endpoint field.

See skills/multi-provider.md §4.
"""

from __future__ import annotations

import json

import httpx

_DEFAULT_ENDPOINT = "http://localhost:11434"


class OllamaClient:
    """
    LLMClient implementation backed by a local Ollama server.

    Parameters
    ----------
    endpoint:
        Base URL of the Ollama server, without trailing slash.
        Defaults to ``http://localhost:11434``.
    timeout:
        HTTP request timeout in seconds. Ollama with large models can be slow
        on first inference; defaults to 300 s.
    """

    def __init__(
        self,
        endpoint: str = _DEFAULT_ENDPOINT,
        timeout: float = 300.0,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._timeout = timeout

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        max_tokens: int = 4096,
    ) -> tuple[str, int, int]:
        """
        Call the Ollama /api/chat endpoint and return (text, tokens_in, tokens_out).

        Uses the non-streaming mode (``stream: false``) so that usage stats are
        available in the single response object.

        Parameters
        ----------
        system_prompt:
            Mapped to a system message in the messages array.
        user_message:
            Mapped to the user message in the messages array.
        model:
            Ollama model tag, e.g. "llama3.1:70b" or "llama3.1:8b".
        max_tokens:
            Passed as ``options.num_predict`` in the Ollama request body.

        Returns
        -------
        tuple[str, int, int]
            (response_text, tokens_in, tokens_out)
            NOTE: Ollama reports ``prompt_eval_count`` (tokens_in) and
            ``eval_count`` (tokens_out). If the server omits these fields the
            values default to 0.

        Raises
        ------
        httpx.HTTPStatusError
            On any non-2xx response from the Ollama server.
        httpx.ConnectError
            If the Ollama server is not reachable at the configured endpoint.
        json.JSONDecodeError
            If the response body is not valid JSON.
        """
        url = f"{self._endpoint}/api/chat"
        payload = {
            "model": model,
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }

        async with httpx.AsyncClient(timeout=self._timeout) as http:
            resp = await http.post(url, json=payload)
            resp.raise_for_status()

        data: dict = json.loads(resp.text)

        response_text: str = data.get("message", {}).get("content", "")
        tokens_in: int = data.get("prompt_eval_count", 0)
        tokens_out: int = data.get("eval_count", 0)

        return response_text, tokens_in, tokens_out
