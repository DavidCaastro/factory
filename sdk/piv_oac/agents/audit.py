"""
PIV/OAC AuditAgent — verifies RF coverage and writes engram atoms.

Contract (skills/agent-contracts.md §1.3):

    AUDIT_RESULT: PASS | FAIL
    RF_COVERAGE: <X>/<Y> RFs trazados
    SCOPE_VIOLATIONS: <comma-separated violations, or NONE if PASS>
    ENGRAM_WRITE: <atom_path> | NONE
"""

from __future__ import annotations

import anthropic

from .base import AgentBase


class AuditAgent(AgentBase):
    """
    Agent responsible for auditing specialist work against RF (Requerimiento
    Funcional) coverage and scope constraints.

    Only AuditAgent is authorised to write engram atoms (enforced in
    EngramStore.write_atom).
    """

    agent_type = "AuditAgent"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-haiku-4-5-20251001",
    ) -> None:
        super().__init__(client, model)

    def _get_system_prompt(self) -> str:
        return (
            "You are an AuditAgent operating within the PIV/OAC framework. "
            "Your role is to verify that specialist agents have addressed all "
            "required Functional Requirements (RFs) and have not modified files "
            "or modules outside their assigned scope.\n\n"
            "After completing your analysis you MUST emit the following structured "
            "contract block. Each field must appear on its own line:\n\n"
            "AUDIT_RESULT: PASS | FAIL\n"
            "RF_COVERAGE: <X>/<Y> RFs trazados\n"
            "SCOPE_VIOLATIONS: <comma-separated list of violations, or NONE if PASS>\n"
            "ENGRAM_WRITE: <atom_path> | NONE\n\n"
            "Set ENGRAM_WRITE to the path of the engram atom you are persisting "
            "for this audit, or NONE if no atom is written. "
            "All field names and enumeration values must be in English."
        )

    def _required_output_fields(self) -> list[str]:
        return ["AUDIT_RESULT", "RF_COVERAGE", "SCOPE_VIOLATIONS", "ENGRAM_WRITE"]
