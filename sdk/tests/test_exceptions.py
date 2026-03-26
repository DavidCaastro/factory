"""Tests for the PIV/OAC exception hierarchy."""

import pytest
from piv_oac.exceptions import (
    PIVOACError,
    AgentUnrecoverableError,
    GateRejectedError,
    VetoError,
    MalformedOutputError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_piv_oac_error(self):
        for cls in (AgentUnrecoverableError, GateRejectedError, VetoError, MalformedOutputError):
            assert issubclass(cls, PIVOACError)

    def test_piv_oac_error_is_exception(self):
        assert issubclass(PIVOACError, Exception)


class TestAgentUnrecoverableError:
    def test_attributes(self):
        err = AgentUnrecoverableError(
            agent_type="SecurityAgent",
            failure_type="UNRECOVERABLE_MALFORMED",
            detail="missing VERDICT after 2 retries",
        )
        assert err.agent_type == "SecurityAgent"
        assert err.failure_type == "UNRECOVERABLE_MALFORMED"
        assert err.detail == "missing VERDICT after 2 retries"

    def test_str_includes_agent_type(self):
        err = AgentUnrecoverableError("AuditAgent", "AGENT_TIMEOUT", "timed out")
        assert "AuditAgent" in str(err)


class TestGateRejectedError:
    def test_attributes(self):
        err = GateRejectedError(gate="Gate-2-Standards", findings=["coverage below 80%"])
        assert err.gate == "Gate-2-Standards"
        assert "coverage" in err.findings[0]

    def test_empty_findings(self):
        err = GateRejectedError(gate="Gate-1", findings=[])
        assert "no details" in str(err)

    def test_multiple_findings(self):
        err = GateRejectedError(gate="Gate-2", findings=["finding A", "finding B"])
        assert "finding A" in str(err)
        assert "finding B" in str(err)


class TestVetoError:
    def test_attributes(self):
        err = VetoError(agent_type="SecurityAgent", reason="RCE detected")
        assert err.agent_type == "SecurityAgent"
        assert err.reason == "RCE detected"

    def test_str_includes_reason(self):
        err = VetoError("MasterOrchestrator", "malicious intent")
        assert "malicious intent" in str(err)


class TestMalformedOutputError:
    def test_attributes(self):
        err = MalformedOutputError(
            agent_type="CoherenceAgent",
            raw_output="some raw text",
            missing_fields=["COHERENCE_STATUS", "GATE1_VERDICT"],
        )
        assert err.agent_type == "CoherenceAgent"
        assert "COHERENCE_STATUS" in err.missing_fields
        assert err.raw_output == "some raw text"

    def test_str_includes_missing_fields(self):
        err = MalformedOutputError("AuditAgent", "", ["AUDIT_RESULT"])
        assert "AUDIT_RESULT" in str(err)
