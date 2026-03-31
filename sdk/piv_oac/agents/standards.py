"""
PIV/OAC StandardsAgent — validates code quality, test coverage, and documentation.

The StandardsAgent acts at Gate 2 (feature/<task> → staging) and at FASE 8
(closure). It enforces the quality checklist defined in skills/standards.md:

- Real test coverage via pytest-cov (no estimation)
- Docstrings on all public functions/classes
- No dead code or unused imports
- Cyclomatic complexity within limits
- Tests cover edge cases and error paths

Contract emitted on every review:

    STANDARDS_VERDICT: APPROVED | REJECTED
    COVERAGE_REPORTED: <percentage or UNKNOWN>
    DIMENSIONS_REJECTED: <comma-separated list, or NONE if APPROVED>
    SKILLS_PROPOSAL: <path to proposal file, or NONE>
"""

from __future__ import annotations

import anthropic

from piv_oac.exceptions import GateRejectedError

from .base import AgentBase


class StandardsAgent(AgentBase):
    """
    Superagent that enforces coding standards, test coverage, and documentation
    quality before any branch is promoted to staging.

    StandardsAgent is a permanent member of the control environment — it is
    always present in Nivel 2 objectives.  It never writes production code;
    it only reviews and reports.

    Gate 2 checklist (skills/standards.md):
    - pytest-cov coverage meets the threshold defined in specs/quality.md
    - Every public function/class has a docstring
    - No dead code, no unused imports
    - Tests cover edge cases and error paths, not only happy path
    - API documentation updated if applicable

    Parameters
    ----------
    client:
        Async Anthropic client.
    model:
        Model to use (default: claude-sonnet-4-6 per CLAUDE.md assignment table).
    coverage_threshold:
        Minimum acceptable coverage percentage (0–100).  Defaults to 80.
        Should match the value in specs/active/quality.md.
    """

    agent_type = "StandardsAgent"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-sonnet-4-6",
        coverage_threshold: int = 80,
    ) -> None:
        super().__init__(client, model)
        self._coverage_threshold = coverage_threshold

    # ------------------------------------------------------------------
    # AgentBase interface
    # ------------------------------------------------------------------

    def _get_system_prompt(self) -> str:
        return (
            "You are a StandardsAgent operating within the PIV/OAC framework. "
            "Your role is to enforce code quality, test coverage, and documentation "
            "standards before any branch is promoted to staging.\n\n"
            "Gate 2 checklist you MUST evaluate:\n"
            f"[ ] Test coverage ≥ {self._coverage_threshold}% (reported by pytest-cov, not estimated)\n"
            "[ ] Every public function and class has a docstring\n"
            "[ ] No dead code, no unused imports\n"
            "[ ] Cyclomatic complexity within acceptable limits\n"
            "[ ] Tests cover edge cases and error paths, not only happy path\n"
            "[ ] API documentation updated if applicable\n\n"
            "IMPORTANT: You never write production code. You only review and report.\n"
            "IMPORTANT: If coverage data is not available from tools, report "
            "COVERAGE_REPORTED: UNKNOWN and note it in DIMENSIONS_REJECTED — "
            "never estimate coverage.\n\n"
            "You MUST end every response with the following structured contract block:\n\n"
            "STANDARDS_VERDICT: APPROVED | REJECTED\n"
            "COVERAGE_REPORTED: <percentage as integer, e.g. 87, or UNKNOWN>\n"
            "DIMENSIONS_REJECTED: <comma-separated list of failed checklist items, "
            "or NONE if APPROVED>\n"
            "SKILLS_PROPOSAL: <path to a proposed skills/ update file, or NONE>\n\n"
            "All field names and enumeration values must be in English."
        )

    def _required_output_fields(self) -> list[str]:
        return [
            "STANDARDS_VERDICT",
            "COVERAGE_REPORTED",
            "DIMENSIONS_REJECTED",
            "SKILLS_PROPOSAL",
        ]

    async def invoke(self, prompt: str, max_retries: int = 2, **kwargs) -> dict[str, str]:
        """
        Invoke the standards review and raise GateRejectedError if rejected.

        Parameters
        ----------
        prompt:
            The review request, typically including diff output or file contents.
        max_retries:
            Retry budget for malformed output (default 2).

        Raises
        ------
        GateRejectedError
            If STANDARDS_VERDICT is REJECTED.
        AgentUnrecoverableError
            If the agent fails to produce valid output within the retry budget.
        """
        fields = await super().invoke(prompt, max_retries=max_retries, **kwargs)
        if fields.get("STANDARDS_VERDICT") == "REJECTED":
            rejected = fields.get("DIMENSIONS_REJECTED", "no details")
            raise GateRejectedError(gate="Gate-2-Standards", findings=[rejected])
        return fields
