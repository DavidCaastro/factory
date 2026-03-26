"""
PIV/OAC SpecialistAgent — implements an atomic unit of work in its worktree.

Contract (skills/agent-contracts.md §1.6):

    IMPLEMENTATION: <plain-text description of what was implemented>
    FILES_CHANGED: <comma-separated list of file paths>
    TESTS_ADDED: <integer>
    RF_ADDRESSED: <comma-separated RF identifiers, or NONE>
"""

from __future__ import annotations

import anthropic

from .base import AgentBase


class SpecialistAgent(AgentBase):
    """
    Agent responsible for implementing a single atomic task inside an isolated
    worktree branch.

    Specialist Agents:
    - Write code, tests, and documentation for one assigned task.
    - Never create sub-agents.
    - Never modify files outside their assigned scope.
    - Report exactly which files changed and which RFs they addressed.

    Parameters
    ----------
    client:
        Async Anthropic client.
    model:
        Model to use (default: claude-sonnet-4-6; may be claude-haiku-4-5 for
        mechanical tasks per CLAUDE.md assignment table).
    specialization:
        Human-readable role hint (e.g. "backend", "test-writer", "db-architect").
        Injected into the system prompt to scope the agent's behaviour.
    """

    agent_type = "SpecialistAgent"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-sonnet-4-6",
        specialization: str = "general",
    ) -> None:
        super().__init__(client, model)
        self._specialization = specialization

    # ------------------------------------------------------------------
    # AgentBase interface
    # ------------------------------------------------------------------

    def _get_system_prompt(self) -> str:
        return (
            f"You are a SpecialistAgent ({self._specialization}) operating within "
            "the PIV/OAC framework. "
            "Your role is to implement the task assigned to you by the Domain "
            "Orchestrator. You work inside an isolated worktree branch — you must "
            "not modify files outside the scope described in your task.\n\n"
            "Rules you MUST follow:\n"
            "1. Only modify files within your assigned worktree scope.\n"
            "2. Write tests for every piece of logic you implement.\n"
            "3. Do not create sub-agents.\n"
            "4. Report your work using the contract block below.\n\n"
            "You MUST end every response with the following structured contract block:\n\n"
            "IMPLEMENTATION: <one-paragraph description of what you implemented>\n"
            "FILES_CHANGED: <comma-separated list of file paths you modified or created>\n"
            "TESTS_ADDED: <integer — number of new test cases added>\n"
            "RF_ADDRESSED: <comma-separated RF identifiers (e.g. RF-01, RF-02), or NONE>\n\n"
            "All field names must be in English."
        )

    def _required_output_fields(self) -> list[str]:
        return ["IMPLEMENTATION", "FILES_CHANGED", "TESTS_ADDED", "RF_ADDRESSED"]
