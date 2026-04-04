"""
Tests for the PMIA module — message types, crypto, and bus.
"""

from __future__ import annotations

import asyncio
import pytest

from piv_oac.pmia import (
    PMIABus,
    CryptoValidator,
    MessageTampered,
    MessageExpired,
    GateVerdictMessage,
    EscalationMessage,
    CrossAlertMessage,
    CheckpointReqMessage,
    IssueEntry,
    ControlEnvironmentState,
    CROSS_ALERT_AUTHORIZED,
    MAX_TOKENS_PER_MESSAGE,
)


# ---------------------------------------------------------------------------
# Message dataclasses
# ---------------------------------------------------------------------------

class TestGateVerdictMessage:
    def test_creates_with_defaults(self):
        msg = GateVerdictMessage(gate="gate_2", verdict="APROBADO", agent_id="SecurityAgent", task_id="T-01")
        assert msg.type == "GATE_VERDICT"
        assert msg.verdict == "APROBADO"
        assert msg.timestamp != ""

    def test_serializes_to_json(self):
        msg = GateVerdictMessage(gate="gate_1", verdict="RECHAZADO", agent_id="A", task_id="T")
        j = msg.to_json()
        assert '"GATE_VERDICT"' in j
        assert '"RECHAZADO"' in j

    def test_issue_entry_enforces_50_token_limit(self):
        long_desc = " ".join(["word"] * 51)
        with pytest.raises(ValueError, match="50-token"):
            IssueEntry(id="SEC-001", severity="HIGH", description=long_desc)

    def test_issue_entry_valid(self):
        issue = IssueEntry(id="SEC-001", severity="CRITICAL", description="SQL injection in /search")
        assert issue.severity == "CRITICAL"


class TestCrossAlertMessage:
    def test_authorized_agent_can_emit(self):
        msg = CrossAlertMessage(
            from_agent="SecurityAgent",
            to_agent="AuditAgent",
            alert_type="SECURITY_FINDING",
            artifact_ref="abc123",
        )
        assert msg.from_agent == "SecurityAgent"

    def test_unauthorized_agent_raises(self):
        with pytest.raises(ValueError, match="not authorized"):
            CrossAlertMessage(from_agent="SpecialistAgent", to_agent="AuditAgent", alert_type="RF_GAP")

    def test_fragment_hint_20_token_limit(self):
        long_hint = " ".join(["w"] * 21)
        with pytest.raises(ValueError, match="20-token"):
            CrossAlertMessage(
                from_agent="SecurityAgent",
                to_agent="AuditAgent",
                alert_type="SECURITY_FINDING",
                fragment_hint=long_hint,
            )

    def test_cross_alert_authorized_set(self):
        assert "SecurityAgent" in CROSS_ALERT_AUTHORIZED
        assert "AuditAgent" in CROSS_ALERT_AUTHORIZED
        assert "SpecialistAgent" not in CROSS_ALERT_AUTHORIZED


class TestCheckpointReqMessage:
    def test_control_environment_state_defaults(self):
        state = ControlEnvironmentState()
        assert state.security_agent == "PENDIENTE"
        assert state.audit_agent == "PENDIENTE"

    def test_message_serializes(self):
        msg = CheckpointReqMessage(
            phase="FASE_2",
            objective_id="OBJ-001",
            active_gates=("gate_1",),
        )
        j = msg.to_json()
        assert "CHECKPOINT_REQ" in j
        assert "OBJ-001" in j


class TestConstants:
    def test_max_tokens(self):
        assert MAX_TOKENS_PER_MESSAGE == 300


# ---------------------------------------------------------------------------
# CryptoValidator
# ---------------------------------------------------------------------------

class TestCryptoValidator:
    def test_sign_and_verify(self):
        cv = CryptoValidator(secret="test-secret")
        msg = GateVerdictMessage(gate="gate_1", verdict="APROBADO", agent_id="A", task_id="T")
        signed = cv.sign_message(msg.to_json())
        import json
        data = json.loads(signed)
        # Should not raise
        cv.verify(signed, data["signature"])

    def test_tampered_message_raises(self):
        cv = CryptoValidator(secret="test-secret")
        msg = GateVerdictMessage(gate="gate_1", verdict="APROBADO", agent_id="A", task_id="T")
        signed = cv.sign_message(msg.to_json())
        with pytest.raises(MessageTampered):
            cv.verify(signed, "invalid_signature_here")

    def test_different_secrets_fail(self):
        cv1 = CryptoValidator(secret="secret-1")
        cv2 = CryptoValidator(secret="secret-2")
        msg = GateVerdictMessage(gate="gate_1", verdict="APROBADO", agent_id="A", task_id="T")
        signed = cv1.sign_message(msg.to_json())
        import json
        data = json.loads(signed)
        with pytest.raises(MessageTampered):
            cv2.verify(signed, data["signature"])

    def test_canonical_payload_excludes_signature(self):
        cv = CryptoValidator(secret="s")
        payload = '{"type": "X", "signature": "abc", "data": "hello"}'
        canonical = cv._canonical_payload(payload)
        assert "signature" not in canonical
        assert "hello" in canonical

    def test_expired_message_raises(self):
        from datetime import datetime, timezone, timedelta
        import json
        cv = CryptoValidator(secret="test", ttl_seconds=1)
        msg = GateVerdictMessage(gate="gate_1", verdict="APROBADO", agent_id="A", task_id="T")
        import dataclasses
        old_ts = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        # Manually build JSON with old timestamp
        d = dataclasses.asdict(msg)
        d["timestamp"] = old_ts
        d.pop("signature", None)
        import json
        raw = json.dumps(d)
        sig = cv.sign(cv._canonical_payload(raw))
        d["signature"] = sig
        signed = json.dumps(d)
        with pytest.raises(MessageExpired):
            cv.verify(signed, sig)


# ---------------------------------------------------------------------------
# PMIABus
# ---------------------------------------------------------------------------

class TestPMIABus:
    @pytest.mark.asyncio
    async def test_gate_verdict_delivered_to_master_orchestrator(self):
        bus = PMIABus()
        received = []
        bus.subscribe("MasterOrchestrator", lambda m: received.append(m) or asyncio.sleep(0))

        msg = GateVerdictMessage(gate="gate_1", verdict="APROBADO", agent_id="SecurityAgent", task_id="T-01")
        await bus.publish(msg, from_agent="SecurityAgent")
        assert len(received) == 1
        assert received[0].verdict == "APROBADO"

    @pytest.mark.asyncio
    async def test_cross_alert_routed_to_target_agent(self):
        bus = PMIABus()
        received = []
        bus.subscribe("AuditAgent", lambda m: received.append(m) or asyncio.sleep(0))

        msg = CrossAlertMessage(
            from_agent="SecurityAgent",
            to_agent="AuditAgent",
            alert_type="SECURITY_FINDING",
            artifact_ref="sha256abc",
        )
        await bus.publish(msg, from_agent="SecurityAgent")
        assert len(received) == 1
        assert received[0].alert_type == "SECURITY_FINDING"

    @pytest.mark.asyncio
    async def test_unauthorized_cross_alert_escalates(self):
        bus = PMIABus()
        escalations = []
        bus.subscribe("MasterOrchestrator", lambda m: escalations.append(m) or asyncio.sleep(0))

        with pytest.raises(ValueError, match="not authorized"):
            CrossAlertMessage(from_agent="SpecialistAgent", to_agent="AuditAgent", alert_type="RF_GAP")

    @pytest.mark.asyncio
    async def test_metrics_increment(self):
        bus = PMIABus()
        bus.subscribe("MasterOrchestrator", lambda m: asyncio.sleep(0))
        msg = GateVerdictMessage(gate="gate_1", verdict="APROBADO", agent_id="A", task_id="T")
        await bus.publish(msg, from_agent="SecurityAgent")
        assert bus.metrics["pmia_messages_total"] == 1

    @pytest.mark.asyncio
    async def test_no_handlers_does_not_raise(self):
        bus = PMIABus()
        msg = GateVerdictMessage(gate="gate_2", verdict="RECHAZADO", agent_id="A", task_id="T")
        # Should complete silently with no registered handlers
        await bus.publish(msg, from_agent="SecurityAgent")
        assert bus.metrics["pmia_messages_total"] == 1

    @pytest.mark.asyncio
    async def test_escalation_message_routed(self):
        bus = PMIABus()
        received = []
        bus.subscribe("MasterOrchestrator", lambda m: received.append(m) or asyncio.sleep(0))

        msg = EscalationMessage(
            from_agent="CoherenceAgent",
            to="MasterOrchestrator",
            reason_code="MAX_REJECTIONS",
            task_id="T-02",
        )
        await bus.publish(msg, from_agent="CoherenceAgent")
        assert len(received) == 1

    def test_pmia_retry_rate_zero_on_empty(self):
        bus = PMIABus()
        assert bus.metrics["pmia_retry_rate"] == 0.0
