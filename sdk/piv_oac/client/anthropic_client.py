"""
PIV/OAC SDK — AnthropicClient.

Wraps anthropic.AsyncAnthropic to satisfy the LLMClient protocol.
This is the default STABLE provider. See skills/multi-provider.md §4.
"""

from __future__ import annotations

import anthropic


class AnthropicClient:
    """
    LLMClient implementation backed by Anthropic's Messages API.

    Parameters
    ----------
    api_key:
        Anthropic API key. If None, falls back to the ANTHROPIC_API_KEY
        environment variable (standard anthropic-sdk behaviour).
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        max_tokens: int = 4096,
    ) -> tuple[str, int, int]:
        """
        Call the Anthropic Messages API and return (text, tokens_in, tokens_out).

        Raises
        ------
        anthropic.APIError
            On any HTTP / auth / rate-limit error from the Anthropic API.
        """
        message = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text: str = message.content[0].text
        tokens_in: int = message.usage.input_tokens
        tokens_out: int = message.usage.output_tokens

        return response_text, tokens_in, tokens_out
