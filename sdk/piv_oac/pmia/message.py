"""
PMIA — Protocolo de Mensaje Inter-Agente.

Dataclasses for all message types defined in skills/inter-agent-protocol.md.
Each message is immutable, JSON-serializable, and carries an HMAC-SHA256
signature produced by CryptoValidator.

Hard limits (§3):
    MAX_TOKENS_PER_MESSAGE = 300
    Chain-of-thought: PROHIBITED
    Artefacts: by artifact_ref only (SHA-256 digest)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Literal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_TOKENS_PER_MESSAGE = 300

GateId = Literal["gate_1", "gate_2", "gate_2b", "gate_3"]
Verdict = Literal["APROBADO", "RECHAZADO", "APROBADO_CON_CONDICIONES"]
EscalationTarget = Literal["MasterOrchestrator", "DomainOrchestrator", "Human"]
EscalationReason = Literal[
    "PROTOCOL_DEVIATION", "SECURITY_VIOLATION", "SCOPE_EXCEEDED", "MAX_REJECTIONS"
]
AlertType = Literal["SECURITY_FINDING", "COHERENCE_ISSUE", "RF_GAP", "QUALITY_ISSUE"]
AgentStatus = Literal["APROBADO", "EN_EJECUCION", "PENDIENTE"]

# Agents authorized to emit CROSS_ALERT (§2)
CROSS_ALERT_AUTHORIZED: frozenset[str] = frozenset(
    ["SecurityAgent", "AuditAgent", "CoherenceAgent", "StandardsAgent"]
)


# ---------------------------------------------------------------------------
# Sub-structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IssueEntry:
    id: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM"]
    description: str  # max 50 tokens

    def __post_init__(self) -> None:
        words = self.description.split()
        if len(words) > 50:
            raise ValueError(
                f"IssueEntry.description exceeds 50-token limit ({len(words)} words)"
            )


@dataclass(frozen=True)
class ControlEnvironmentState:
    security_agent: AgentStatus = "PENDIENTE"
    audit_agent: AgentStatus = "PENDIENTE"
    coherence_agent: AgentStatus = "PENDIENTE"
    standards_agent: AgentStatus = "PENDIENTE"


# ---------------------------------------------------------------------------
# Message dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GateVerdictMessage:
    """Emitted by control agents on completing a gate review (§2 GATE_VERDICT)."""

    type: Literal["GATE_VERDICT"] = field(default="GATE_VERDICT", init=False)
    gate: GateId = "gate_1"
    verdict: Verdict = "APROBADO"
    agent_id: str = ""
    task_id: str = ""
    issues: tuple[IssueEntry, ...] = field(default_factory=tuple)
    artifact_ref: str = ""          # SHA-256 of reviewed artefact
    timestamp: str = field(default_factory=lambda: _now_iso())
    signature: str = ""             # filled by CryptoValidator.sign()

    def to_json(self) -> str:
        d = asdict(self)
        d["issues"] = [asdict(i) for i in self.issues]
        return json.dumps(d, ensure_ascii=False)


@dataclass(frozen=True)
class EscalationMessage:
    """Emitted by any agent when outside its scope or capacity (§2 ESCALATION)."""

    type: Literal["ESCALATION"] = field(default="ESCALATION", init=False)
    from_agent: str = ""
    to: EscalationTarget = "MasterOrchestrator"
    reason_code: EscalationReason = "PROTOCOL_DEVIATION"
    task_id: str = ""
    context_snapshot_ref: str = ""  # ref in StateStore
    timestamp: str = field(default_factory=lambda: _now_iso())
    signature: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass(frozen=True)
class CrossAlertMessage:
    """Lateral channel between control agents only (§2 CROSS_ALERT)."""

    type: Literal["CROSS_ALERT"] = field(default="CROSS_ALERT", init=False)
    from_agent: str = ""
    to_agent: str = ""
    alert_type: AlertType = "SECURITY_FINDING"
    artifact_ref: str = ""
    fragment_hint: str = ""         # max 20 tokens for context filtering
    timestamp: str = field(default_factory=lambda: _now_iso())
    signature: str = ""

    def __post_init__(self) -> None:
        if self.from_agent not in CROSS_ALERT_AUTHORIZED:
            raise ValueError(
                f"Agent '{self.from_agent}' is not authorized to emit CROSS_ALERT. "
                f"Authorized: {sorted(CROSS_ALERT_AUTHORIZED)}"
            )
        words = self.fragment_hint.split()
        if len(words) > 20:
            raise ValueError(
                f"CrossAlertMessage.fragment_hint exceeds 20-token limit ({len(words)} words)"
            )

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass(frozen=True)
class CheckpointReqMessage:
    """Emitted by orchestrators to trigger a preventive checkpoint (§2 CHECKPOINT_REQ)."""

    type: Literal["CHECKPOINT_REQ"] = field(default="CHECKPOINT_REQ", init=False)
    phase: Literal["FASE_2", "FASE_4", "FASE_6", "FASE_7"] = "FASE_2"
    objective_id: str = ""
    control_environment_state: ControlEnvironmentState = field(
        default_factory=ControlEnvironmentState
    )
    active_gates: tuple[str, ...] = field(default_factory=tuple)
    timestamp: str = field(default_factory=lambda: _now_iso())
    signature: str = ""

    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d, ensure_ascii=False)


@dataclass(frozen=True)
class MalformedMessageResponse:
    """Returned by the bus when a received message fails validation (§4)."""

    type: Literal["MALFORMED_MESSAGE"] = field(default="MALFORMED_MESSAGE", init=False)
    error: str = ""
    expected_schema: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


# Union type for type hints
PMIAMessage = (
    GateVerdictMessage
    | EscalationMessage
    | CrossAlertMessage
    | CheckpointReqMessage
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
