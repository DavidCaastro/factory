"""
Tests for LogisticsAgent, ExecutionAuditor, and DocumentationAgent.
Uses mock LLM client — no real API calls.
"""

from __future__ import annotations

import pytest

from piv_oac.agents.logistics import LogisticsAgent, TOKEN_CAPS
from piv_oac.agents.execution_auditor import ExecutionAuditor, IRREGULARITY_SEVERITIES
from piv_oac.agents.documentation import DocumentationAgent
from piv_oac.exceptions import AgentUnrecoverableError
from tests.conftest import make_mock_client


# ---------------------------------------------------------------------------
# LogisticsAgent
# ---------------------------------------------------------------------------

class TestLogisticsAgent:
    @pytest.mark.asyncio
    async def test_budget_report_no_warnings(self):
        raw = (
            "TOTAL_ESTIMATED_TOKENS: 45000\n"
            "TOTAL_ESTIMATED_COST_USD: 0.0135\n"
            "FRAGMENTATION_RECOMMENDED: NONE\n"
            "WARNINGS: NONE\n"
        )
        agent = LogisticsAgent(client=make_mock_client(raw), nivel="nivel_2_standard")
        fields = await agent.invoke("Estimate budget for DAG: task_a → task_b → task_c")
        assert fields["TOTAL_ESTIMATED_TOKENS"] == "45000"
        assert fields["FRAGMENTATION_RECOMMENDED"] == "NONE"
        assert fields["WARNINGS"] == "NONE"

    @pytest.mark.asyncio
    async def test_budget_report_with_fragmentation(self):
        raw = (
            "TOTAL_ESTIMATED_TOKENS: 320000\n"
            "TOTAL_ESTIMATED_COST_USD: 0.096\n"
            "FRAGMENTATION_RECOMMENDED: task_c, task_d\n"
            "WARNINGS: WARNING_ANOMALOUS_ESTIMATE: task_c exceeds cap of 100000\n"
        )
        agent = LogisticsAgent(client=make_mock_client(raw))
        fields = await agent.invoke("Estimate budget for large DAG")
        assert "task_c" in fields["FRAGMENTATION_RECOMMENDED"]
        assert "WARNING_ANOMALOUS_ESTIMATE" in fields["WARNINGS"]

    @pytest.mark.asyncio
    async def test_malformed_exhausts_retries(self):
        agent = LogisticsAgent(client=make_mock_client("no contract here"))
        with pytest.raises(AgentUnrecoverableError):
            await agent.invoke("Estimate", max_retries=1)

    def test_token_caps_defined(self):
        assert TOKEN_CAPS["nivel_1"] == 8_000
        assert TOKEN_CAPS["nivel_2_small"] == 40_000
        assert TOKEN_CAPS["nivel_2_standard"] == 100_000
        assert TOKEN_CAPS["nivel_2_large"] == 200_000

    def test_cap_applied_on_init(self):
        agent = LogisticsAgent(client=make_mock_client(""), nivel="nivel_2_small")
        assert agent._cap == 40_000

    def test_unknown_nivel_defaults_to_standard(self):
        agent = LogisticsAgent(client=make_mock_client(""), nivel="unknown_level")
        assert agent._cap == TOKEN_CAPS["nivel_2_standard"]

    def test_estimate_cost(self):
        cost = LogisticsAgent.estimate_cost(100_000)
        assert cost > 0.0
        assert isinstance(cost, float)


# ---------------------------------------------------------------------------
# ExecutionAuditor
# ---------------------------------------------------------------------------

class TestExecutionAuditor:
    @pytest.mark.asyncio
    async def test_clean_execution_report(self):
        raw = (
            "TOTAL_EVENTS: 42\n"
            "TOTAL_IRREGULARITIES: 0\n"
            "GATE_COMPLIANCE_RATE: 1.0\n"
            "PMIA_RETRIES: 1\n"
            "AUDIT_SUMMARY: Execution completed without irregularities.\n"
        )
        agent = ExecutionAuditor(
            client=make_mock_client(raw), objective_id="OBJ-005"
        )
        fields = await agent.invoke("Audit execution events")
        assert fields["TOTAL_IRREGULARITIES"] == "0"
        assert fields["GATE_COMPLIANCE_RATE"] == "1.0"

    @pytest.mark.asyncio
    async def test_report_with_critical_irregularities(self):
        raw = (
            "TOTAL_EVENTS: 38\n"
            "TOTAL_IRREGULARITIES: 2\n"
            "GATE_COMPLIANCE_RATE: 0.75\n"
            "PMIA_RETRIES: 0\n"
            "AUDIT_SUMMARY: 2 critical irregularities: GATE_SKIPPED in FASE 4.\n"
        )
        agent = ExecutionAuditor(client=make_mock_client(raw))
        fields = await agent.invoke("Audit events with violations")
        assert fields["TOTAL_IRREGULARITIES"] == "2"
        assert float(fields["GATE_COMPLIANCE_RATE"]) < 1.0

    @pytest.mark.asyncio
    async def test_generate_report_returns_partial_on_failure(self):
        """generate_report() never raises — returns partial report with error key."""
        agent = ExecutionAuditor(
            client=make_mock_client("completely malformed"),
            objective_id="OBJ-ERR",
        )
        result = await agent.generate_report("some events", max_retries=1)
        assert "error" in result
        assert result["TOTAL_EVENTS"] == "0"
        assert "OBJ-ERR" in result["AUDIT_SUMMARY"] or "error" in result

    @pytest.mark.asyncio
    async def test_generate_report_success(self):
        raw = (
            "TOTAL_EVENTS: 10\n"
            "TOTAL_IRREGULARITIES: 0\n"
            "GATE_COMPLIANCE_RATE: 1.0\n"
            "PMIA_RETRIES: 0\n"
            "AUDIT_SUMMARY: No issues detected.\n"
        )
        agent = ExecutionAuditor(
            client=make_mock_client(raw), objective_id="OBJ-006"
        )
        result = await agent.generate_report("event_log content")
        assert "error" not in result
        assert result["TOTAL_EVENTS"] == "10"

    def test_irregularity_severities_defined(self):
        assert IRREGULARITY_SEVERITIES["GATE_SKIPPED"] == "CRITICAL"
        assert IRREGULARITY_SEVERITIES["GATE_BYPASSED"] == "CRITICAL"
        assert IRREGULARITY_SEVERITIES["UNAUTHORIZED_INSTANTIATION"] == "CRITICAL"
        assert IRREGULARITY_SEVERITIES["PROTOCOL_DEVIATION"] == "HIGH"
        assert IRREGULARITY_SEVERITIES["TOKEN_OVERRUN"] == "WARNING"
        assert IRREGULARITY_SEVERITIES["CONTEXT_SATURATION"] == "WARNING"

    @pytest.mark.asyncio
    async def test_objective_id_stored(self):
        agent = ExecutionAuditor(
            client=make_mock_client(""), objective_id="OBJ-TEST"
        )
        assert agent._objective_id == "OBJ-TEST"


# ---------------------------------------------------------------------------
# DocumentationAgent
# ---------------------------------------------------------------------------

class TestDocumentationAgent:
    @pytest.mark.asyncio
    async def test_completado_status(self):
        raw = (
            "DOCS_STATUS: COMPLETADO\n"
            "FILES_GENERATED: README.md, docs/deployment.md\n"
            "MISSING_DATA: NONE\n"
        )
        agent = DocumentationAgent(
            client=make_mock_client(raw),
            missing_deliverables=["README.md — missing Installation section"],
        )
        fields = await agent.invoke("Generate missing docs")
        assert fields["DOCS_STATUS"] == "COMPLETADO"
        assert "README.md" in fields["FILES_GENERATED"]
        assert fields["MISSING_DATA"] == "NONE"

    @pytest.mark.asyncio
    async def test_partial_status_with_missing_data(self):
        raw = (
            "DOCS_STATUS: PARTIAL\n"
            "FILES_GENERATED: README.md\n"
            "MISSING_DATA: deployment target not specified in specs/active/architecture.md\n"
        )
        agent = DocumentationAgent(client=make_mock_client(raw))
        fields = await agent.invoke("Generate docs with incomplete specs")
        assert fields["DOCS_STATUS"] == "PARTIAL"
        assert "deployment" in fields["MISSING_DATA"]

    @pytest.mark.asyncio
    async def test_no_deliverables_uses_prompt(self):
        raw = (
            "DOCS_STATUS: COMPLETADO\n"
            "FILES_GENERATED: NONE\n"
            "MISSING_DATA: NONE\n"
        )
        agent = DocumentationAgent(client=make_mock_client(raw))
        fields = await agent.invoke("No specific deliverables listed")
        assert fields["DOCS_STATUS"] == "COMPLETADO"

    @pytest.mark.asyncio
    async def test_malformed_exhausts_retries(self):
        agent = DocumentationAgent(client=make_mock_client("not a contract"))
        with pytest.raises(AgentUnrecoverableError):
            await agent.invoke("Generate docs", max_retries=1)

    def test_missing_deliverables_stored(self):
        deliverables = ["README.md — missing Usage section", "docs/deployment.md"]
        agent = DocumentationAgent(
            client=make_mock_client(""), missing_deliverables=deliverables
        )
        assert agent._missing_deliverables == deliverables

    def test_empty_deliverables_defaults(self):
        agent = DocumentationAgent(client=make_mock_client(""))
        assert agent._missing_deliverables == []
