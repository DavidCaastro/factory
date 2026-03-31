"""Tests for ContractParser — skills/agent-contracts.md §3."""

import pytest
from piv_oac.contracts.parser import ContractParser, AGENT_REQUIRED_FIELDS
from piv_oac.exceptions import MalformedOutputError


@pytest.fixture
def parser():
    return ContractParser()


class TestParseHappyPath:
    def test_security_agent_approved(self, parser):
        raw = (
            "Some reasoning here.\n\n"
            "VERDICT: APPROVED\n"
            "RISK_LEVEL: LOW\n"
            "FINDINGS: NONE\n"
        )
        fields = parser.parse(raw, ["VERDICT", "RISK_LEVEL", "FINDINGS"], "SecurityAgent")
        assert fields["VERDICT"] == "APPROVED"
        assert fields["RISK_LEVEL"] == "LOW"
        assert fields["FINDINGS"] == "NONE"

    def test_audit_agent_pass(self, parser):
        raw = (
            "AUDIT_RESULT: PASS\n"
            "RF_COVERAGE: 5/5 RFs trazados\n"
            "SCOPE_VIOLATIONS: NONE\n"
            "ENGRAM_WRITE: engram/audit/gate_decisions.md\n"
        )
        fields = parser.parse(raw, AGENT_REQUIRED_FIELDS["AuditAgent"], "AuditAgent")
        assert fields["AUDIT_RESULT"] == "PASS"
        assert fields["RF_COVERAGE"] == "5/5 RFs trazados"
        assert fields["ENGRAM_WRITE"] == "engram/audit/gate_decisions.md"

    def test_coherence_agent_consistent(self, parser):
        raw = (
            "COHERENCE_STATUS: CONSISTENT\n"
            "GATE1_VERDICT: APPROVED\n"
            "CONFLICTS: NONE\n"
        )
        fields = parser.parse(raw, AGENT_REQUIRED_FIELDS["CoherenceAgent"], "CoherenceAgent")
        assert fields["COHERENCE_STATUS"] == "CONSISTENT"
        assert fields["GATE1_VERDICT"] == "APPROVED"

    def test_field_with_spaces_in_value(self, parser):
        raw = "PLAN: Implement the payment module with three layers\n"
        fields = parser.parse(raw, ["PLAN"], "DomainOrchestrator")
        assert fields["PLAN"] == "Implement the payment module with three layers"

    def test_extra_text_before_contract_block(self, parser):
        raw = (
            "After careful review, I determined:\n\n"
            "VERDICT: REJECTED\n"
            "RISK_LEVEL: HIGH\n"
            "FINDINGS: SQL injection in /search endpoint\n"
        )
        fields = parser.parse(raw, ["VERDICT", "RISK_LEVEL", "FINDINGS"])
        assert fields["VERDICT"] == "REJECTED"
        assert fields["RISK_LEVEL"] == "HIGH"


class TestMalformedOutput:
    def test_missing_single_field_raises(self, parser):
        raw = "VERDICT: APPROVED\nRISK_LEVEL: LOW\n"  # FINDINGS missing
        with pytest.raises(MalformedOutputError) as exc_info:
            parser.parse(raw, ["VERDICT", "RISK_LEVEL", "FINDINGS"], "SecurityAgent")
        assert "FINDINGS" in exc_info.value.missing_fields
        assert exc_info.value.agent_type == "SecurityAgent"

    def test_missing_multiple_fields_raises(self, parser):
        raw = "VERDICT: APPROVED\n"
        with pytest.raises(MalformedOutputError) as exc_info:
            parser.parse(raw, ["VERDICT", "RISK_LEVEL", "FINDINGS"])
        assert set(exc_info.value.missing_fields) == {"RISK_LEVEL", "FINDINGS"}

    def test_empty_response_raises(self, parser):
        with pytest.raises(MalformedOutputError):
            parser.parse("", ["VERDICT", "RISK_LEVEL", "FINDINGS"])

    def test_field_inside_prose_not_matched(self, parser):
        # Field embedded in a sentence should NOT be extracted (requires line-start)
        raw = "The VERDICT: APPROVED value is interesting.\nVERDICT: REJECTED\n"
        fields = parser.parse(raw, ["VERDICT"])
        # Line-start pattern — first match wins; "The VERDICT:" does NOT match
        assert fields["VERDICT"] == "REJECTED"


class TestParseForAgent:
    def test_known_agent_type(self, parser):
        raw = (
            "VERDICT: CONDITIONAL_APPROVED\n"
            "RISK_LEVEL: MEDIUM\n"
            "FINDINGS: rate limiting not configured\n"
        )
        fields = parser.parse_for_agent(raw, "SecurityAgent")
        assert fields["VERDICT"] == "CONDITIONAL_APPROVED"

    def test_unknown_agent_type_raises(self, parser):
        with pytest.raises(ValueError, match="Unknown agent_type"):
            parser.parse_for_agent("whatever", "GhostAgent")

    def test_pattern_cache_reuse(self, parser):
        # Calling parse twice with the same field should use the cached pattern
        raw = "VERDICT: APPROVED\nRISK_LEVEL: LOW\nFINDINGS: NONE\n"
        parser.parse(raw, ["VERDICT"])
        parser.parse(raw, ["VERDICT"])  # second call — hits cache
        assert "VERDICT" in ContractParser._pattern_cache
