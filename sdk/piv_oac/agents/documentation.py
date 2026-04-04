"""
PIV/OAC DocumentationAgent — generates missing product documentation for Gate 3.

Temporary specialist instantiated by DomainOrchestrator (or MasterOrchestrator
if the domain has already closed) when StandardsAgent detects missing required
deliverables during Gate 3.

NOT created preventively — only instantiated when StandardsAgent emits
GATE_3_DOCS_BLOQUEADO (registry/documentation_agent.md §2).

Protocol (registry/documentation_agent.md §3):
    INPUT  : list of missing deliverables + specs/active/ + staging code (read-only)
    OUTPUT : generated files committed to staging + report to DomainOrchestrator

Contract emitted:

    DOCS_STATUS: COMPLETADO | PARTIAL
    FILES_GENERATED: <comma-separated file paths, or NONE>
    MISSING_DATA: <spec gaps that could not be inferred, or NONE>

Restrictions (registry/documentation_agent.md §5):
    - Only writes to the product folder — never to registry/, skills/, engram/, specs/
    - Never modifies source code — documentation only
    - Never marks Gate 3 as approved — that is exclusively StandardsAgent's role
    - Uses [COMPLETAR: <description>] placeholders when spec data is missing
"""

from __future__ import annotations

import anthropic

from .base import AgentBase


class DocumentationAgent(AgentBase):
    """
    Generates missing product documentation deliverables for Gate 3.

    DocumentationAgent is a temporary specialist — it self-destructs
    after delivering its output to the DomainOrchestrator. It works
    sequentially with StandardsAgent to eliminate race conditions
    (registry/documentation_agent.md §4).

    Parameters
    ----------
    client:
        Async Anthropic client.
    model:
        Model to use. Defaults to claude-haiku-4-5 for structured
        documentation; use claude-sonnet-4-6 when design inference
        from incomplete specs is required.
    missing_deliverables:
        List of deliverable descriptions reported by StandardsAgent.
        Each entry should identify the file path and what sections are absent.
    """

    agent_type = "DocumentationAgent"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-haiku-4-5-20251001",
        missing_deliverables: list[str] | None = None,
    ) -> None:
        super().__init__(client, model)
        self._missing_deliverables = missing_deliverables or []

    def _get_system_prompt(self) -> str:
        deliverables_block = (
            "\n".join(f"  - {d}" for d in self._missing_deliverables)
            if self._missing_deliverables
            else "  (deliverables provided in the user message)"
        )
        return (
            "You are a DocumentationAgent operating within the PIV/OAC framework. "
            "You generate missing product documentation deliverables identified by "
            "the StandardsAgent during Gate 3 evaluation.\n\n"
            f"Missing deliverables to generate:\n{deliverables_block}\n\n"
            "CRITICAL RULES:\n"
            "- You ONLY write documentation — never source code.\n"
            "- You ONLY write to the product folder — never to registry/, skills/, "
            "engram/, or specs/.\n"
            "- If required information is not present in the provided specs, use "
            "[COMPLETAR: <description of missing data>] as a placeholder and report "
            "it in MISSING_DATA.\n"
            "- You NEVER mark Gate 3 as approved — that is StandardsAgent's role.\n"
            "- You NEVER escalate directly to the user — always through "
            "DomainOrchestrator or MasterOrchestrator.\n\n"
            "After generating all deliverables you MUST emit the following structured "
            "contract block. Each field must appear on its own line:\n\n"
            "DOCS_STATUS: COMPLETADO | PARTIAL\n"
            "FILES_GENERATED: <comma-separated list of file paths written, or NONE>\n"
            "MISSING_DATA: <comma-separated descriptions of spec gaps that required "
            "[COMPLETAR] placeholders, or NONE>\n\n"
            "DOCS_STATUS must be COMPLETADO only when every requested deliverable "
            "was fully generated (even with placeholders). Use PARTIAL if any "
            "deliverable could not be generated at all."
        )

    def _required_output_fields(self) -> list[str]:
        return ["DOCS_STATUS", "FILES_GENERATED", "MISSING_DATA"]
