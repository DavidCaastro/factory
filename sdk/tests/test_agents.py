"""
Tests for all concrete agent classes.

Uses mock LLM client — no real API calls.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from piv_oac.agents.security import SecurityAgent
from piv_oac.agents.audit import AuditAgent
from piv_oac.agents.coherence import CoherenceAgent
from piv_oac.agents.standards import StandardsAgent
from piv_oac.agents.compliance import ComplianceAgent, COMPLIANCE_DISCLAIMER
from piv_oac.agents.domain_orchestrator import DomainOrchestrator
from piv_oac.agents.specialist import SpecialistAgent
from piv_oac.exceptions import (
    AgentUnrecoverableError,
    GateRejectedError,
    VetoError,
    MalformedOutputError,
)
from tests.conftest import make_mock_client


# ---------------------------------------------------------------------------
# SecurityAgent
# ---------------------------------------------------------------------------

class TestSecurityAgent:
    @pytest.mark.asyncio
    async def test_approved_response(self):
        raw = "VERDICT: APPROVED\nRISK_LEVEL: LOW\nFINDINGS: NONE\n"
        agent = SecurityAgent(client=make_mock_client(raw))
        fields = await agent.invoke("Review this task")
        assert fields["VERDICT"] == "APPROVED"
        assert fields["RISK_LEVEL"] == "LOW"

    @pytest.mark.asyncio
    async def test_rejected_response(self):
        raw = "VERDICT: REJECTED\nRISK_LEVEL: HIGH\nFINDINGS: SQL injection in /search\n"
        agent = SecurityAgent(client=make_mock_client(raw))
        fields = await agent.invoke("Review this task")
        assert fields["VERDICT"] == "REJECTED"

    @pytest.mark.asyncio
    async def test_veto_detection(self):
        raw = (
            "VERDICT: REJECTED\nRISK_LEVEL: CRITICAL\nFINDINGS: RCE via admin endpoint\n"
            "SECURITY_VETO: Unauthenticated RCE endpoint; pipeline halted\n"
        )
        agent = SecurityAgent(client=make_mock_client(raw))
        # invoke() itself does not raise VetoError — check_veto() does
        fields = await agent.invoke("Review")
        with pytest.raises(VetoError) as exc_info:
            SecurityAgent.check_veto(raw)
        assert "RCE" in exc_info.value.reason

    @pytest.mark.asyncio
    async def test_malformed_exhausts_retries(self):
        raw = "Nothing useful here"
        agent = SecurityAgent(client=make_mock_client(raw))
        with pytest.raises(AgentUnrecoverableError):
            await agent.invoke("Review", max_retries=1)


# ---------------------------------------------------------------------------
# AuditAgent
# ---------------------------------------------------------------------------

class TestAuditAgent:
    @pytest.mark.asyncio
    async def test_pass_response(self):
        raw = (
            "AUDIT_RESULT: PASS\n"
            "RF_COVERAGE: 3/3 RFs trazados\n"
            "SCOPE_VIOLATIONS: NONE\n"
            "ENGRAM_WRITE: NONE\n"
        )
        agent = AuditAgent(client=make_mock_client(raw))
        fields = await agent.invoke("Audit this")
        assert fields["AUDIT_RESULT"] == "PASS"
        assert fields["SCOPE_VIOLATIONS"] == "NONE"

    @pytest.mark.asyncio
    async def test_fail_response(self):
        raw = (
            "AUDIT_RESULT: FAIL\n"
            "RF_COVERAGE: 2/3 RFs trazados\n"
            "SCOPE_VIOLATIONS: auth/middleware.py modified outside scope\n"
            "ENGRAM_WRITE: NONE\n"
        )
        agent = AuditAgent(client=make_mock_client(raw))
        fields = await agent.invoke("Audit this")
        assert fields["AUDIT_RESULT"] == "FAIL"
        assert "middleware" in fields["SCOPE_VIOLATIONS"]


# ---------------------------------------------------------------------------
# CoherenceAgent
# ---------------------------------------------------------------------------

class TestCoherenceAgent:
    @pytest.mark.asyncio
    async def test_consistent_response(self):
        raw = (
            "COHERENCE_STATUS: CONSISTENT\n"
            "GATE1_VERDICT: APPROVED\n"
            "CONFLICTS: NONE\n"
        )
        agent = CoherenceAgent(client=make_mock_client(raw))
        fields = await agent.invoke("Check coherence")
        assert fields["GATE1_VERDICT"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_conflict_raises_gate_rejected(self):
        raw = (
            "COHERENCE_STATUS: CONFLICT_DETECTED\n"
            "GATE1_VERDICT: REJECTED\n"
            "CONFLICTS: definidos a continuación\n"
            "CONFLICT: expert_a=BackendDO expert_b=FrontendDO "
            "conflict_type=schema_mismatch resolution=use BackendDO schema\n"
        )
        agent = CoherenceAgent(client=make_mock_client(raw))
        with pytest.raises(GateRejectedError) as exc_info:
            await agent.invoke("Check coherence")
        assert exc_info.value.gate == "Gate-1"

    def test_parse_conflicts(self):
        raw = (
            "CONFLICT: expert_a=BackendDO expert_b=FrontendDO "
            "conflict_type=schema_mismatch resolution=adopt snake_case\n"
        )
        conflicts = CoherenceAgent.parse_conflicts(raw)
        assert len(conflicts) == 1
        assert conflicts[0]["expert_a"] == "BackendDO"
        assert conflicts[0]["conflict_type"] == "schema_mismatch"


# ---------------------------------------------------------------------------
# StandardsAgent
# ---------------------------------------------------------------------------

class TestStandardsAgent:
    @pytest.mark.asyncio
    async def test_approved_response(self):
        raw = (
            "STANDARDS_VERDICT: APPROVED\n"
            "COVERAGE_REPORTED: 92\n"
            "DIMENSIONS_REJECTED: NONE\n"
            "SKILLS_PROPOSAL: NONE\n"
        )
        agent = StandardsAgent(client=make_mock_client(raw))
        fields = await agent.invoke("Review code quality")
        assert fields["STANDARDS_VERDICT"] == "APPROVED"
        assert fields["COVERAGE_REPORTED"] == "92"

    @pytest.mark.asyncio
    async def test_rejected_raises_gate_rejected(self):
        raw = (
            "STANDARDS_VERDICT: REJECTED\n"
            "COVERAGE_REPORTED: 61\n"
            "DIMENSIONS_REJECTED: coverage below threshold, missing docstrings\n"
            "SKILLS_PROPOSAL: NONE\n"
        )
        agent = StandardsAgent(client=make_mock_client(raw), coverage_threshold=80)
        with pytest.raises(GateRejectedError) as exc_info:
            await agent.invoke("Review")
        assert exc_info.value.gate == "Gate-2-Standards"

    @pytest.mark.asyncio
    async def test_unknown_coverage_passes_through(self):
        raw = (
            "STANDARDS_VERDICT: APPROVED\n"
            "COVERAGE_REPORTED: UNKNOWN\n"
            "DIMENSIONS_REJECTED: NONE\n"
            "SKILLS_PROPOSAL: NONE\n"
        )
        agent = StandardsAgent(client=make_mock_client(raw))
        fields = await agent.invoke("Review")
        assert fields["COVERAGE_REPORTED"] == "UNKNOWN"


# ---------------------------------------------------------------------------
# ComplianceAgent
# ---------------------------------------------------------------------------

class TestComplianceAgent:
    def test_cannot_instantiate_with_scope_none(self):
        import anthropic
        from unittest.mock import MagicMock
        client = MagicMock(spec=anthropic.AsyncAnthropic)
        with pytest.raises(ValueError, match="compliance_scope is NONE"):
            ComplianceAgent(client=client, compliance_scope="NONE")

    @pytest.mark.asyncio
    async def test_approved_response(self):
        raw = (
            "COMPLIANCE_VERDICT: APPROVED\n"
            "RISK_CATEGORIES: NONE\n"
            "MITIGATION_REQUIRED: NO\n"
            "DISCLAIMER: HUMAN_REVIEW_REQUIRED\n"
        )
        agent = ComplianceAgent(client=make_mock_client(raw), compliance_scope="MINIMAL")
        fields = await agent.invoke("Evaluate compliance")
        assert fields["COMPLIANCE_VERDICT"] == "APPROVED"
        assert fields["DISCLAIMER"] == "HUMAN_REVIEW_REQUIRED"

    @pytest.mark.asyncio
    async def test_rejected_raises_gate_rejected(self):
        raw = (
            "COMPLIANCE_VERDICT: REJECTED\n"
            "RISK_CATEGORIES: GDPR Article 6 — no lawful basis for processing\n"
            "MITIGATION_REQUIRED: YES\n"
            "DISCLAIMER: HUMAN_REVIEW_REQUIRED\n"
        )
        agent = ComplianceAgent(client=make_mock_client(raw), compliance_scope="FULL")
        with pytest.raises(GateRejectedError) as exc_info:
            await agent.invoke("Evaluate")
        assert exc_info.value.gate == "Gate-3-Compliance"

    @pytest.mark.asyncio
    async def test_mitigation_required_does_not_raise(self):
        raw = (
            "COMPLIANCE_VERDICT: MITIGATION_REQUIRED\n"
            "RISK_CATEGORIES: GDPR consent mechanism missing\n"
            "MITIGATION_REQUIRED: YES\n"
            "DISCLAIMER: HUMAN_REVIEW_REQUIRED\n"
        )
        agent = ComplianceAgent(client=make_mock_client(raw))
        fields = await agent.invoke("Evaluate")
        # MITIGATION_REQUIRED verdict does NOT raise — caller handles it
        assert fields["COMPLIANCE_VERDICT"] == "MITIGATION_REQUIRED"
        assert fields["MITIGATION_REQUIRED"] == "YES"

    def test_disclaimer_property(self):
        import anthropic
        from unittest.mock import MagicMock
        client = MagicMock(spec=anthropic.AsyncAnthropic)
        agent = ComplianceAgent(client=client)
        assert "NOT constitute legal advice" in agent.disclaimer
        assert COMPLIANCE_DISCLAIMER == agent.disclaimer


# ---------------------------------------------------------------------------
# DomainOrchestrator
# ---------------------------------------------------------------------------

class TestDomainOrchestrator:
    @pytest.mark.asyncio
    async def test_plan_response(self):
        raw = (
            "DO_TYPE: BackendDO\n"
            "PLAN: Implement payment module with three layers\n"
            "DEPENDENCIES: task_adapter->task_business, task_persistence->task_business\n"
            "WORKTREE: task=Implement PaymentAdapter expert=SpecialistAgent base_branch=feature/payments\n"
            "WORKTREE: task=Implement PaymentRepository expert=SpecialistAgent base_branch=feature/payments\n"
        )
        agent = DomainOrchestrator(client=make_mock_client(raw), domain="backend")
        fields = await agent.invoke("Plan the backend tasks")
        assert fields["DO_TYPE"] == "BackendDO"
        assert fields["DEPENDENCIES"] == "task_adapter->task_business, task_persistence->task_business"

    def test_parse_worktrees(self):
        raw = (
            "WORKTREE: task=Implement PaymentAdapter expert=SpecialistAgent base_branch=feature/payments\n"
            "WORKTREE: task=Write unit tests expert=SpecialistAgent base_branch=feature/payments-tests\n"
        )
        specs = DomainOrchestrator.parse_worktrees(raw)
        assert len(specs) == 2
        assert specs[0].task == "Implement PaymentAdapter"
        assert specs[0].expert == "SpecialistAgent"
        assert specs[1].base_branch == "feature/payments-tests"

    def test_parse_worktrees_empty(self):
        assert DomainOrchestrator.parse_worktrees("No worktrees here") == []


# ---------------------------------------------------------------------------
# SpecialistAgent
# ---------------------------------------------------------------------------

class TestSpecialistAgent:
    @pytest.mark.asyncio
    async def test_implementation_response(self):
        raw = (
            "IMPLEMENTATION: Implemented PaymentGatewayAdapter with Stripe support\n"
            "FILES_CHANGED: src/payments/adapter.py, tests/test_adapter.py\n"
            "TESTS_ADDED: 5\n"
            "RF_ADDRESSED: RF-08, RF-09\n"
        )
        agent = SpecialistAgent(client=make_mock_client(raw), specialization="backend")
        fields = await agent.invoke("Implement the payment adapter")
        assert fields["TESTS_ADDED"] == "5"
        assert "RF-08" in fields["RF_ADDRESSED"]

    @pytest.mark.asyncio
    async def test_no_rfs_addressed(self):
        raw = (
            "IMPLEMENTATION: Fixed typo in README\n"
            "FILES_CHANGED: README.md\n"
            "TESTS_ADDED: 0\n"
            "RF_ADDRESSED: NONE\n"
        )
        agent = SpecialistAgent(client=make_mock_client(raw))
        fields = await agent.invoke("Fix typo")
        assert fields["RF_ADDRESSED"] == "NONE"


# ---------------------------------------------------------------------------
# Retry loop (AgentBase)
# ---------------------------------------------------------------------------

class TestRetryLoop:
    @pytest.mark.asyncio
    async def test_retries_on_malformed_then_succeeds(self):
        """First response is malformed; second is valid."""
        import anthropic
        from unittest.mock import AsyncMock, MagicMock

        malformed_block = MagicMock()
        malformed_block.text = "VERDICT: APPROVED\n"  # missing RISK_LEVEL and FINDINGS

        valid_block = MagicMock()
        valid_block.text = "VERDICT: APPROVED\nRISK_LEVEL: LOW\nFINDINGS: NONE\n"

        malformed_msg = MagicMock(spec=anthropic.types.Message)
        malformed_msg.content = [malformed_block]

        valid_msg = MagicMock(spec=anthropic.types.Message)
        valid_msg.content = [valid_block]

        client = MagicMock(spec=anthropic.AsyncAnthropic)
        client.messages = MagicMock()
        client.messages.create = AsyncMock(side_effect=[malformed_msg, valid_msg])

        agent = SecurityAgent(client=client)
        fields = await agent.invoke("Review", max_retries=2)
        assert fields["VERDICT"] == "APPROVED"
        assert client.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises_unrecoverable(self):
        raw = "no contract fields at all"
        agent = SecurityAgent(client=make_mock_client(raw))
        with pytest.raises(AgentUnrecoverableError) as exc_info:
            await agent.invoke("Review", max_retries=2)
        assert exc_info.value.agent_type == "SecurityAgent"
        assert "UNRECOVERABLE_MALFORMED" in exc_info.value.failure_type


# ---------------------------------------------------------------------------
# Timeout enforcement (AgentBase)
# ---------------------------------------------------------------------------

class TestTimeoutEnforcement:
    @pytest.mark.asyncio
    async def test_timeout_raises_asyncio_timeout_error(self):
        """invoke() raises asyncio.TimeoutError when timeout_seconds exceeded."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock
        import anthropic

        async def slow_create(**kwargs):
            await asyncio.sleep(10)  # much longer than timeout
            msg = MagicMock(spec=anthropic.types.Message)
            block = MagicMock()
            block.text = "VERDICT: APPROVED\nRISK_LEVEL: LOW\nFINDINGS: NONE\n"
            msg.content = [block]
            return msg

        client = MagicMock(spec=anthropic.AsyncAnthropic)
        client.messages = MagicMock()
        client.messages.create = slow_create

        agent = SecurityAgent(client=client)
        with pytest.raises(asyncio.TimeoutError):
            await agent.invoke("Review", timeout_seconds=0.01)

    @pytest.mark.asyncio
    async def test_no_timeout_completes_normally(self):
        """invoke() succeeds when timeout_seconds is None (default)."""
        raw = "VERDICT: APPROVED\nRISK_LEVEL: LOW\nFINDINGS: NONE\n"
        agent = SecurityAgent(client=make_mock_client(raw))
        fields = await agent.invoke("Review", timeout_seconds=None)
        assert fields["VERDICT"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_timeout_applies_to_all_attempts(self):
        """The timeout covers the full invocation including retries."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock
        import anthropic

        call_count = 0

        async def delayed_create(**kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(1)  # each attempt takes 1 s
            msg = MagicMock(spec=anthropic.types.Message)
            block = MagicMock()
            block.text = ""  # malformed — triggers retry
            msg.content = [block]
            return msg

        client = MagicMock(spec=anthropic.AsyncAnthropic)
        client.messages = MagicMock()
        client.messages.create = delayed_create

        agent = SecurityAgent(client=client)
        with pytest.raises(asyncio.TimeoutError):
            await agent.invoke("Review", max_retries=5, timeout_seconds=0.05)
        # Should time out before all retries complete
        assert call_count < 5
