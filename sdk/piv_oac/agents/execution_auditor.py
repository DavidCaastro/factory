"""
PIV/OAC ExecutionAuditor — passive out-of-band observer FASE 2→8.

Observes the execution pipeline and records irregularities without
intervening in any gate. Generates ExecutionAuditReport at FASE 8
as input for the AuditAgent. Never substitutes AuditAgent.

Key distinction from AuditAgent (registry/execution_auditor.md §2):
- AuditAgent: superagent — emits gate verdicts, writes logs_veracidad/
- ExecutionAuditor: passive observer — records only, no verdicts

Contract emitted (registry/execution_auditor.md §4):

    TOTAL_EVENTS: <integer>
    TOTAL_IRREGULARITIES: <integer>
    GATE_COMPLIANCE_RATE: <float 0.0–1.0>
    PMIA_RETRIES: <integer>
    AUDIT_SUMMARY: <narrative under 100 tokens>

Irregularity types monitored (registry/execution_auditor.md §3):
    GATE_SKIPPED              — CRITICAL
    GATE_BYPASSED             — CRITICAL
    PROTOCOL_DEVIATION        — HIGH
    TOKEN_OVERRUN             — WARNING
    CONTEXT_SATURATION        — WARNING
    UNAUTHORIZED_INSTANTIATION — CRITICAL
"""

from __future__ import annotations

import anthropic

from .base import AgentBase

IRREGULARITY_SEVERITIES: dict[str, str] = {
    "GATE_SKIPPED": "CRITICAL",
    "GATE_BYPASSED": "CRITICAL",
    "UNAUTHORIZED_INSTANTIATION": "CRITICAL",
    "PROTOCOL_DEVIATION": "HIGH",
    "TOKEN_OVERRUN": "WARNING",
    "CONTEXT_SATURATION": "WARNING",
}


class ExecutionAuditor(AgentBase):
    """
    Out-of-band observer active from FASE 2 to FASE 8.

    ExecutionAuditor has its own fixed budget of 5 000 tokens, isolated
    from the objective pool. It never raises GateRejectedError or VetoError.
    If an internal error occurs it emits a partial report — it never
    propagates exceptions to the pipeline.

    Parameters
    ----------
    client:
        Async Anthropic client.
    model:
        Model to use (default: claude-haiku-4-5 per registry assignment).
    objective_id:
        ID of the objective being audited. Used to scope the audit log.
    """

    agent_type = "ExecutionAuditor"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-haiku-4-5-20251001",
        objective_id: str = "unknown",
    ) -> None:
        super().__init__(client, model)
        self._objective_id = objective_id

    def _get_system_prompt(self) -> str:
        return (
            "You are an ExecutionAuditor operating within the PIV/OAC framework. "
            "You observe execution events passively and record irregularities. "
            f"Current objective: {self._objective_id}\n\n"
            "CRITICAL RULES:\n"
            "- You NEVER intervene in gates or emit gate verdicts.\n"
            "- You NEVER escalate directly to the user — report only to AuditAgent.\n"
            "- You NEVER modify logs_veracidad/ or metrics/sessions.md.\n"
            "- You ALWAYS generate a report, even on partial data or internal error.\n\n"
            "Irregularity types you monitor:\n"
            "  GATE_SKIPPED (CRITICAL) — merge without prior gate in StateStore\n"
            "  GATE_BYPASSED (CRITICAL) — gate executed without all responsible agents\n"
            "  PROTOCOL_DEVIATION (HIGH) — action outside the defined phase sequence\n"
            "  TOKEN_OVERRUN (WARNING) — agent exceeded budget by more than 20%\n"
            "  CONTEXT_SATURATION (WARNING) — VETO_SATURACION emitted by any agent\n"
            "  UNAUTHORIZED_INSTANTIATION (CRITICAL) — agent created outside AgentFactory\n\n"
            "After your analysis you MUST emit the following structured contract block. "
            "Each field must appear on its own line:\n\n"
            "TOTAL_EVENTS: <integer — total events observed>\n"
            "TOTAL_IRREGULARITIES: <integer — count of irregularities detected>\n"
            "GATE_COMPLIANCE_RATE: <float 0.0–1.0 — fraction of gates with no irregularities>\n"
            "PMIA_RETRIES: <integer — messages that required retry due to malformed output>\n"
            "AUDIT_SUMMARY: <narrative under 100 tokens>\n\n"
            "All field names must be in English."
        )

    def _required_output_fields(self) -> list[str]:
        return [
            "TOTAL_EVENTS",
            "TOTAL_IRREGULARITIES",
            "GATE_COMPLIANCE_RATE",
            "PMIA_RETRIES",
            "AUDIT_SUMMARY",
        ]

    async def generate_report(self, events_log: str, max_retries: int = 2) -> dict[str, str]:
        """
        Generate the ExecutionAuditReport from an events log.

        This is the primary interface for FASE 8. On any internal error,
        returns a partial report dict with an ``error`` key rather than
        raising, to guarantee the pipeline is never blocked by the auditor.

        Parameters
        ----------
        events_log:
            JSONL or structured text of observed execution events.
        max_retries:
            Retry budget for malformed output.

        Returns
        -------
        dict[str, str]
            Parsed contract fields, possibly including an ``error`` key
            if parsing partially failed.
        """
        prompt = (
            f"Generate the ExecutionAuditReport for objective '{self._objective_id}' "
            f"based on the following execution events:\n\n{events_log}"
        )
        try:
            return await self.invoke(prompt, max_retries=max_retries)
        except Exception as exc:
            return {
                "TOTAL_EVENTS": "0",
                "TOTAL_IRREGULARITIES": "0",
                "GATE_COMPLIANCE_RATE": "0.0",
                "PMIA_RETRIES": "0",
                "AUDIT_SUMMARY": f"Partial report — internal error: {exc}",
                "error": str(exc),
            }
