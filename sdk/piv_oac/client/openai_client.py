"""
PIV/OAC SDK — OpenAIClient.

Wraps openai.AsyncOpenAI to satisfy the LLMClient protocol.
Status: EXPERIMENTAL. Requires the optional dependency:

    pip install piv-oac[openai]

If the openai package is not installed, any instantiation raises ImportError
with a clear installation hint rather than a cryptic AttributeError at call
time.

See skills/multi-provider.md §4.
"""

from __future__ import annotations

try:
    import openai as _openai_module  # type: ignore[import-untyped]

    _OPENAI_AVAILABLE = True
except ImportError:
    _openai_module = None  # type: ignore[assignment]
    _OPENAI_AVAILABLE = False


class OpenAIClient:
    """
    LLMClient implementation backed by OpenAI's Chat Completions API.

    Parameters
    ----------
    api_key:
        OpenAI API key. If None, falls back to the OPENAI_API_KEY environment
        variable (standard openai-sdk behaviour).

    Raises
    ------
    ImportError
        If the ``openai`` package is not installed.
    """

    def __init__(self, api_key: str | None = None) -> None:
        if not _OPENAI_AVAILABLE:
            raise ImportError(
                "The 'openai' package is required to use OpenAIClient. "
                "Install it with:  pip install piv-oac[openai]"
            )
        self._client = _openai_module.AsyncOpenAI(api_key=api_key)

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        max_tokens: int = 4096,
    ) -> tuple[str, int, int]:
        """
        Call the OpenAI Chat Completions API and return (text, tokens_in, tokens_out).

        Parameters
        ----------
        system_prompt:
            Mapped to a system message in the messages array.
        user_message:
            Mapped to the user message in the messages array.
        model:
            OpenAI model identifier, e.g. "gpt-4o" or "gpt-4o-mini".
        max_tokens:
            Maximum tokens in the completion response.

        Returns
        -------
        tuple[str, int, int]
            (response_text, tokens_in, tokens_out)

        Raises
        ------
        openai.OpenAIError
            On any HTTP / auth / rate-limit error from the OpenAI API.
        RuntimeError
            If the API returns an empty choices list.
        """
        response = await self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        if not response.choices:
            raise RuntimeError(
                f"OpenAI returned an empty choices list for model '{model}'."
            )

        response_text: str = response.choices[0].message.content or ""
        tokens_in: int = response.usage.prompt_tokens if response.usage else 0
        tokens_out: int = response.usage.completion_tokens if response.usage else 0

        return response_text, tokens_in, tokens_out
