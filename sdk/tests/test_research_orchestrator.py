"""
Tests for ResearchOrchestrator agent.
"""

from __future__ import annotations

import pytest

from piv_oac.agents.research_orchestrator import ResearchOrchestrator
from tests.conftest import make_mock_client


_VALID_RESPONSE = (
    "RQ_ID: RQ-01\n"
    "CONFIDENCE: ALTA\n"
    "FINDINGS: EIP-1559 reduces gas fee volatility by 87% vs legacy pricing.\n"
    "SOURCES: https://eips.ethereum.org/EIPS/eip-1559\n"
    "GAPS: Long-term mempool behaviour under sustained load not yet studied.\n"
)


def test_research_orchestrator_agent_type() -> None:
    assert ResearchOrchestrator.agent_type == "ResearchOrchestrator"


def test_research_orchestrator_required_fields() -> None:
    client = make_mock_client(_VALID_RESPONSE)
    agent = ResearchOrchestrator(client=client, model="claude-sonnet-4-6")
    fields = agent._required_output_fields()
    assert set(fields) == {"RQ_ID", "CONFIDENCE", "FINDINGS", "SOURCES", "GAPS"}


@pytest.mark.asyncio
async def test_research_orchestrator_invoke_returns_parsed_fields() -> None:
    client = make_mock_client(_VALID_RESPONSE)
    agent = ResearchOrchestrator(client=client, model="claude-sonnet-4-6")
    result = await agent.invoke("Research EIP-1559 gas fee dynamics.", objective_id="OBJ-RES-01")
    assert result["RQ_ID"] == "RQ-01"
    assert result["CONFIDENCE"] == "ALTA"
    assert "EIP-1559" in result["FINDINGS"]


@pytest.mark.asyncio
async def test_research_orchestrator_system_prompt_mentions_research() -> None:
    client = make_mock_client(_VALID_RESPONSE)
    agent = ResearchOrchestrator(client=client, model="claude-sonnet-4-6")
    prompt = agent._get_system_prompt()
    assert "ResearchOrchestrator" in prompt
    assert "ALTA" in prompt or "confidence" in prompt.lower()
