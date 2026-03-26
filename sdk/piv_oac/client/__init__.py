"""
PIV/OAC SDK — client package.

Public surface
--------------
LLMClient       — Protocol that every provider implementation satisfies.
AnthropicClient — Default STABLE implementation (wraps anthropic.AsyncAnthropic).
OpenAIClient    — EXPERIMENTAL implementation (requires pip install piv-oac[openai]).
OllamaClient    — EXPERIMENTAL implementation (wraps httpx to a local Ollama server).
get_client      — Factory function: get_client(provider, **kwargs) -> LLMClient.

Usage
-----
    from piv_oac.client import get_client

    client = get_client("anthropic", api_key="sk-ant-...")
    text, tok_in, tok_out = await client.complete(
        system_prompt="You are ...",
        user_message="Analyse ...",
        model="claude-sonnet-4-6",
    )

Supported provider strings
---------------------------
    "anthropic"  — AnthropicClient (default)
    "openai"     — OpenAIClient    (requires openai package)
    "ollama"     — OllamaClient    (requires local Ollama server)

See skills/multi-provider.md for the full protocol specification.
"""

from __future__ import annotations

from .anthropic_client import AnthropicClient
from .base import LLMClient
from .ollama_client import OllamaClient
from .openai_client import OpenAIClient

__all__ = [
    "LLMClient",
    "AnthropicClient",
    "OpenAIClient",
    "OllamaClient",
    "get_client",
]

_PROVIDER_MAP: dict[str, type] = {
    "anthropic": AnthropicClient,
    "openai": OpenAIClient,
    "ollama": OllamaClient,
}


def get_client(provider: str = "anthropic", **kwargs) -> LLMClient:
    """
    Factory function — return an LLMClient for the requested provider.

    Parameters
    ----------
    provider:
        One of "anthropic", "openai", or "ollama". Case-insensitive.
    **kwargs:
        Passed directly to the provider's constructor.

        AnthropicClient: api_key (str | None)
        OpenAIClient:    api_key (str | None)
        OllamaClient:    endpoint (str), timeout (float)

    Returns
    -------
    LLMClient
        A concrete implementation that satisfies the LLMClient Protocol.

    Raises
    ------
    ValueError
        If ``provider`` is not one of the supported strings.
    ImportError
        If the provider requires an optional dependency that is not installed
        (currently only OpenAIClient raises this).

    Examples
    --------
    >>> client = get_client("anthropic")
    >>> client = get_client("openai", api_key="sk-...")
    >>> client = get_client("ollama", endpoint="http://localhost:11434")
    """
    key = provider.lower()
    cls = _PROVIDER_MAP.get(key)
    if cls is None:
        supported = ", ".join(sorted(_PROVIDER_MAP))
        raise ValueError(
            f"Unknown provider '{provider}'. Supported values: {supported}."
        )
    return cls(**kwargs)
