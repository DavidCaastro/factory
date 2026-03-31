"""
PIV/OAC SecurityAgent — reviews tasks for security risks.

Contract (skills/agent-contracts.md §1.2):

    VERDICT: APPROVED | REJECTED | CONDITIONAL_APPROVED
    RISK_LEVEL: LOW | MEDIUM | HIGH | CRITICAL
    FINDINGS: <comma-separated findings, or NONE>

Optional veto field:

    SECURITY_VETO: <plain-text reason>

When SECURITY_VETO is present in the raw output the pipeline must halt.
Callers can detect this by checking the raw output or by calling
:meth:`check_veto` on the parsed result.
"""

from __future__ import annotations

import re

import anthropic

from piv_oac.exceptions import VetoError

from .base import AgentBase

_VETO_PATTERN = re.compile(r"^SECURITY_VETO:\s+(.+)$", re.MULTILINE)


class SecurityAgent(AgentBase):
    """
    Agent responsible for security review of proposed tasks and implementations.

    After :meth:`invoke` returns, callers should call :meth:`check_veto` with
    the raw output to detect hard-veto situations.
    """

    agent_type = "SecurityAgent"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-sonnet-4-6",
    ) -> None:
        super().__init__(client, model)

    def _get_system_prompt(self) -> str:
        return (
            "You are a SecurityAgent operating within the PIV/OAC framework. "
            "Your role is to review tasks, designs, and code changes for security risks "
            "including but not limited to: injection vulnerabilities, authentication flaws, "
            "privilege escalation, data exposure, and insecure dependencies.\n\n"
            "You MUST end every response with the following structured contract block. "
            "Each field must appear on its own line with no extra text:\n\n"
            "VERDICT: APPROVED | REJECTED | CONDITIONAL_APPROVED\n"
            "RISK_LEVEL: LOW | MEDIUM | HIGH | CRITICAL\n"
            "FINDINGS: <comma-separated list of findings, or NONE if APPROVED>\n\n"
            "If you detect a critical issue requiring a hard pipeline halt, also emit:\n"
            "SECURITY_VETO: <plain-text reason>\n\n"
            "All field names and enumeration values must be in English. "
            "Free-form reasoning may precede the contract block."
        )

    def _required_output_fields(self) -> list[str]:
        return ["VERDICT", "RISK_LEVEL", "FINDINGS"]

    async def invoke(
        self,
        prompt: str,
        max_retries: int = 2,
        objective_id: str = "unknown",
        timeout_seconds: float | None = None,
    ) -> dict[str, str]:
        """
        Invoke the security review.

        After parsing the contract fields, checks for the optional SECURITY_VETO
        field and raises VetoError if present.
        """
        return await super().invoke(
            prompt,
            max_retries=max_retries,
            objective_id=objective_id,
            timeout_seconds=timeout_seconds,
        )

    @staticmethod
    def check_veto(raw_output: str, agent_type: str = "SecurityAgent") -> None:
        """
        Inspect *raw_output* for a SECURITY_VETO field and raise VetoError
        if found.  Call this immediately after :meth:`invoke` when you have
        access to the raw model response.
        """
        match = _VETO_PATTERN.search(raw_output)
        if match:
            raise VetoError(agent_type=agent_type, reason=match.group(1).strip())
