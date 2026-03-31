"""
PIV/OAC SDK — LLMClient Protocol.

All provider implementations must satisfy this Protocol (PEP 544).
The return contract (response_text, tokens_in, tokens_out) is mandatory so that
the cost-metrics subsystem can account for tokens regardless of the provider.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """
    Provider-agnostic LLM interface.

    Implementations: AnthropicClient, OpenAIClient, OllamaClient.
    Factory: get_client(provider, **kwargs) -> LLMClient.

    See skills/multi-provider.md §3 for the full protocol specification.
    """

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        max_tokens: int = 4096,
    ) -> tuple[str, int, int]:
        """
        Send a single-turn completion request.

        Parameters
        ----------
        system_prompt:
            The agent's system prompt (role definition + output contract).
        user_message:
            The user turn content (task description, context, etc.).
        model:
            Provider-specific model identifier, e.g. "claude-sonnet-4-6".
        max_tokens:
            Maximum tokens in the completion response.

        Returns
        -------
        tuple[str, int, int]
            (response_text, tokens_in, tokens_out)
            - response_text: the model's raw text output
            - tokens_in: prompt tokens consumed
            - tokens_out: completion tokens produced
        """
        ...
