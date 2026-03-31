"""
Shared pytest fixtures for the piv-oac SDK test suite.

Uses a mock LLM client so tests never hit the Anthropic API.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

import anthropic


def make_mock_client(response_text: str) -> anthropic.AsyncAnthropic:
    """
    Return a mock AsyncAnthropic client that always responds with *response_text*.
    """
    block = MagicMock()
    block.text = response_text

    message = MagicMock(spec=anthropic.types.Message)
    message.content = [block]

    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=message)
    return client
