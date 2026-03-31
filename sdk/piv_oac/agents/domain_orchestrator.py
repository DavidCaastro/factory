"""
PIV/OAC DomainOrchestrator — coordinates tasks within a single domain.

Contract (skills/agent-contracts.md §1.5):

    DO_TYPE: <type, e.g. BackendDO, FrontendDO>
    PLAN: <plain-text description of the overall plan>
    DEPENDENCIES: <comma-separated dependency edges, e.g. task_2->task_3, or NONE>

Followed by one or more WORKTREE lines:

    WORKTREE: task=<description> expert=<expert_type> base_branch=<branch>
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import anthropic

from .base import AgentBase

_WORKTREE_PATTERN = re.compile(
    r"^WORKTREE:\s+task=(.+?)\s+expert=(\S+)\s+base_branch=(\S+)$",
    re.MULTILINE,
)


@dataclass
class WorktreeSpec:
    """Parsed WORKTREE line from a DomainOrchestrator response."""

    task: str
    expert: str
    base_branch: str


class DomainOrchestrator(AgentBase):
    """
    Orchestrator responsible for coordinating all tasks within one domain
    (e.g. backend, frontend, data).

    A Domain Orchestrator:
    - Receives the domain's slice of the execution DAG from MasterOrchestrator.
    - Generates a plan and a set of WORKTREE specs for Specialist Agents.
    - Submits the plan to the gate (Security + Audit + Coherence) before
      creating any worktrees or specialist agents.

    Parameters
    ----------
    client:
        Async Anthropic client.
    model:
        Model to use (default: claude-sonnet-4-6 per CLAUDE.md assignment table).
    domain:
        Human-readable domain name (e.g. "backend", "frontend").  Used in the
        system prompt to scope the orchestrator's responsibilities.
    """

    agent_type = "DomainOrchestrator"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-sonnet-4-6",
        domain: str = "general",
    ) -> None:
        super().__init__(client, model)
        self._domain = domain

    # ------------------------------------------------------------------
    # AgentBase interface
    # ------------------------------------------------------------------

    def _get_system_prompt(self) -> str:
        return (
            f"You are a DomainOrchestrator for the '{self._domain}' domain, "
            "operating within the PIV/OAC framework. "
            "Your role is to receive a set of tasks from the MasterOrchestrator "
            "and produce a detailed execution plan with explicit worktree assignments "
            "for Specialist Agents.\n\n"
            "Rules you MUST follow:\n"
            "1. Never write implementation code yourself — only plan and assign.\n"
            "2. Never create worktrees or agents before the gate approves your plan.\n"
            "3. Each task must be assigned to at least one Specialist Agent.\n"
            "4. Declare inter-task dependencies explicitly.\n\n"
            "You MUST end every response with the following structured contract block:\n\n"
            "DO_TYPE: <your orchestrator type, e.g. BackendDO>\n"
            "PLAN: <one-paragraph description of the overall plan>\n"
            "DEPENDENCIES: <comma-separated edges like task_a->task_b, or NONE>\n\n"
            "Then append one WORKTREE line per specialist assignment:\n"
            "WORKTREE: task=<task description> expert=<SpecialistAgent> "
            "base_branch=<feature/branch-name>\n\n"
            "All field names and enumeration values must be in English."
        )

    def _required_output_fields(self) -> list[str]:
        return ["DO_TYPE", "PLAN", "DEPENDENCIES"]

    # ------------------------------------------------------------------
    # Additional helpers
    # ------------------------------------------------------------------

    @staticmethod
    def parse_worktrees(raw_output: str) -> list[WorktreeSpec]:
        """
        Extract all WORKTREE lines from a raw DomainOrchestrator response.

        Returns a list of :class:`WorktreeSpec` instances.  An empty list is
        returned if the response contains no WORKTREE lines (which would be a
        protocol violation — callers should validate that at least one spec is
        present).
        """
        specs: list[WorktreeSpec] = []
        for match in _WORKTREE_PATTERN.finditer(raw_output):
            specs.append(
                WorktreeSpec(
                    task=match.group(1).strip(),
                    expert=match.group(2),
                    base_branch=match.group(3),
                )
            )
        return specs
