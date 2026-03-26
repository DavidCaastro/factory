"""
PIV/OAC CoherenceAgent — Gate-1 coherence check across Domain Orchestrators.

Contract (skills/agent-contracts.md §1.4):

    COHERENCE_STATUS: CONSISTENT | CONFLICT_DETECTED | SCOPE_OVERLAP
    GATE1_VERDICT: APPROVED | REJECTED
    CONFLICTS: <see format below, or NONE if CONSISTENT>

Each conflict occupies one line immediately after CONFLICTS:

    CONFLICT: expert_a=<name> expert_b=<name> conflict_type=<type> resolution=<resolution>

When GATE1_VERDICT is REJECTED, callers should raise GateRejectedError.
"""

from __future__ import annotations

import re

import anthropic

from piv_oac.exceptions import GateRejectedError

from .base import AgentBase

_CONFLICT_PATTERN = re.compile(
    r"^CONFLICT:\s+expert_a=(\S+)\s+expert_b=(\S+)\s+conflict_type=(\S+)\s+resolution=(.+)$",
    re.MULTILINE,
)


class CoherenceAgent(AgentBase):
    """
    Agent responsible for Gate-1 coherence checks — ensuring that the plans
    produced by multiple Domain Orchestrators do not conflict with each other.
    """

    agent_type = "CoherenceAgent"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-sonnet-4-6",
    ) -> None:
        super().__init__(client, model)

    def _get_system_prompt(self) -> str:
        return (
            "You are a CoherenceAgent operating within the PIV/OAC framework. "
            "Your role is to perform Gate-1 coherence checks: review the plans "
            "produced by multiple Domain Orchestrators and identify any scope "
            "overlaps, schema mismatches, or logical contradictions.\n\n"
            "You MUST end every response with the following structured contract "
            "block. Each field on its own line:\n\n"
            "COHERENCE_STATUS: CONSISTENT | CONFLICT_DETECTED | SCOPE_OVERLAP\n"
            "GATE1_VERDICT: APPROVED | REJECTED\n"
            "CONFLICTS: <NONE, or literal text 'definidos a continuación'>\n\n"
            "If there are conflicts, append one CONFLICT line per conflict "
            "immediately after CONFLICTS:\n"
            "CONFLICT: expert_a=<name> expert_b=<name> conflict_type=<type> resolution=<resolution>\n\n"
            "All field names and enumeration values must be in English."
        )

    def _required_output_fields(self) -> list[str]:
        return ["COHERENCE_STATUS", "GATE1_VERDICT", "CONFLICTS"]

    async def invoke(
        self,
        prompt: str,
        max_retries: int = 2,
        objective_id: str = "unknown",
        timeout_seconds: float | None = None,
    ) -> dict[str, str]:
        """
        Invoke the coherence check and raise GateRejectedError if the gate
        verdict is REJECTED.
        """
        fields = await super().invoke(
            prompt,
            max_retries=max_retries,
            objective_id=objective_id,
            timeout_seconds=timeout_seconds,
        )
        if fields.get("GATE1_VERDICT") == "REJECTED":
            # Collect conflict descriptions for the error
            findings: list[str] = []
            # CONFLICTS field may contain free text; individual CONFLICT lines
            # will be parsed by callers if needed.
            if fields.get("CONFLICTS") not in (None, "NONE"):
                findings.append(fields["CONFLICTS"])
            raise GateRejectedError(gate="Gate-1", findings=findings)
        return fields

    @staticmethod
    def parse_conflicts(raw_output: str) -> list[dict[str, str]]:
        """
        Extract all CONFLICT lines from a raw agent response.

        Returns a list of dicts with keys:
        ``expert_a``, ``expert_b``, ``conflict_type``, ``resolution``.
        """
        conflicts = []
        for match in _CONFLICT_PATTERN.finditer(raw_output):
            conflicts.append(
                {
                    "expert_a": match.group(1),
                    "expert_b": match.group(2),
                    "conflict_type": match.group(3),
                    "resolution": match.group(4).strip(),
                }
            )
        return conflicts
