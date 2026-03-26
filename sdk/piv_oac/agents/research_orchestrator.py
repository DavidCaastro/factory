"""
PIV/OAC ResearchOrchestrator — agent for RESEARCH and MIXED execution modes.

Coordinates research tasks: formulates Research Questions (RQs), delegates
to EpistemicAgents for evidence gathering, evaluates source quality, and
synthesises findings into a structured report.

Protocol reference: skills/research-methodology.md, registry/research_orchestrator.md.
Execution modes: RESEARCH | MIXED (tasks declared Modo: RES in the DAG).
"""

from __future__ import annotations

from piv_oac.agents.base import AgentBase


class ResearchOrchestrator(AgentBase):
    """
    Orchestrates research objectives within the PIV/OAC framework.

    Responsibilities (registry/research_orchestrator.md §2):
    - Decompose research objectives into atomic RQs
    - Delegate evidence gathering to EpistemicAgent instances
    - Evaluate source credibility (skills/source-evaluation.md)
    - Synthesise findings: confidence level ALTA / MEDIA / BAJA
    - Gate 2 criterion: confidence ≥ ALTA/MEDIA (not binary PASS/FAIL)

    Execution mode gate:
    - RESEARCH: all tasks are RES — no code produced
    - MIXED: tasks declared Modo: RES use this orchestrator;
      tasks declared Modo: DEV use DomainOrchestrator
    """

    agent_type = "ResearchOrchestrator"

    def _get_system_prompt(self) -> str:
        return (
            "You are the ResearchOrchestrator in the PIV/OAC framework. "
            "Your role is to coordinate research objectives by decomposing them into "
            "atomic Research Questions (RQs), evaluating evidence quality, and synthesising "
            "findings with explicit confidence levels (ALTA / MEDIA / BAJA). "
            "You never produce code — only structured research reports. "
            "Follow skills/research-methodology.md and skills/source-evaluation.md. "
            "Your output must include the fields: RQ_ID, CONFIDENCE, FINDINGS, SOURCES, GAPS."
        )

    def _required_output_fields(self) -> list[str]:
        return ["RQ_ID", "CONFIDENCE", "FINDINGS", "SOURCES", "GAPS"]
