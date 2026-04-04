"""
PIV/OAC SDK — Custom exceptions.

Hierarchy:
    PIVOACError
    ├── AgentUnrecoverableError
    ├── GateRejectedError
    ├── VetoError
    └── MalformedOutputError
"""

from __future__ import annotations


class PIVOACError(Exception):
    """Base exception for all PIV/OAC SDK errors."""


class AgentUnrecoverableError(PIVOACError):
    """
    Raised when an agent exhausts its retry budget without producing a valid
    structured output.  Maps to the UNRECOVERABLE_MALFORMED state defined in
    skills/agent-contracts.md §3.3.
    """

    def __init__(self, agent_type: str, failure_type: str, detail: str) -> None:
        self.agent_type = agent_type
        self.failure_type = failure_type
        self.detail = detail
        super().__init__(
            f"[{agent_type}] unrecoverable failure ({failure_type}): {detail}"
        )


class GateRejectedError(PIVOACError):
    """
    Raised when a pipeline gate rejects the current execution (e.g. Gate-1
    coherence check returns GATE1_VERDICT: REJECTED).
    """

    def __init__(self, gate: str, findings: list[str]) -> None:
        self.gate = gate
        self.findings = findings
        findings_str = "; ".join(findings) if findings else "no details"
        super().__init__(f"Gate '{gate}' rejected execution: {findings_str}")


class VetoError(PIVOACError):
    """
    Raised when an agent emits a hard veto that halts the entire pipeline:
    - MasterOrchestrator  → VETO_INTENCION
    - SecurityAgent       → SECURITY_VETO
    """

    def __init__(self, agent_type: str, reason: str) -> None:
        self.agent_type = agent_type
        self.reason = reason
        super().__init__(f"[{agent_type}] veto: {reason}")


class MalformedOutputError(PIVOACError):
    """
    Raised when an agent's raw output is missing one or more required contract
    fields.  The caller should retry up to max_retries before escalating to
    AgentUnrecoverableError (see skills/agent-contracts.md §3.3).
    """

    def __init__(
        self, agent_type: str, raw_output: str, missing_fields: list[str]
    ) -> None:
        self.agent_type = agent_type
        self.raw_output = raw_output
        self.missing_fields = missing_fields
        fields_str = ", ".join(missing_fields)
        super().__init__(
            f"[{agent_type}] malformed output — missing fields: {fields_str}"
        )


class CircuitOpenError(PIVOACError):
    """
    Raised when a gate's circuit breaker is open — the gate has been rejected
    MAX_GATE_REJECTIONS times without a successful pass, and the pipeline must
    halt to prevent runaway LLM cost.

    The caller must either escalate to a human, apply a hotfix, or call
    GateCircuitBreaker.reset(gate) after resolving the root cause.
    """

    def __init__(self, gate: str, rejection_count: int) -> None:
        self.gate = gate
        self.rejection_count = rejection_count
        super().__init__(
            f"Gate '{gate}' circuit is OPEN after {rejection_count} rejections — "
            "pipeline halted. Resolve the root cause then call "
            "GateCircuitBreaker.reset(gate)."
        )
