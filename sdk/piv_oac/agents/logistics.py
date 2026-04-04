"""
PIV/OAC LogisticsAgent — proactive token budget estimator.

Active in FASE 1 (post-DAG) of Nivel 2 objectives. Estimates token
consumption per DAG task BEFORE specialists are instantiated.
Never emits gate verdicts. Never blocks plans. Informs only.

Contract emitted (registry/logistics_agent.md §4):

    TOTAL_ESTIMATED_TOKENS: <integer>
    TOTAL_ESTIMATED_COST_USD: <float>
    FRAGMENTATION_RECOMMENDED: <comma-separated task IDs, or NONE>
    WARNINGS: <WARNING_ANOMALOUS_ESTIMATE messages, or NONE>

Token caps (registry/logistics_agent.md §3):

    Nivel 1              :   8 000 tokens
    Nivel 2 (≤3 files)   :  40 000 tokens
    Nivel 2 standard     : 100 000 tokens
    Nivel 2 (≥10 files)  : 200 000 tokens
"""

from __future__ import annotations

import anthropic

from .base import AgentBase

TOKEN_CAPS: dict[str, int] = {
    "nivel_1": 8_000,
    "nivel_2_small": 40_000,
    "nivel_2_standard": 100_000,
    "nivel_2_large": 200_000,
}

# Rough cost estimate per 1 000 tokens for claude-haiku-4-5 (input+output blended)
_COST_PER_1K_TOKENS_USD = 0.0003


class LogisticsAgent(AgentBase):
    """
    Estimates token budget for a DAG before specialist instantiation.

    LogisticsAgent operates with its own fixed budget of 3 000 tokens,
    separate from the objective pool. It never reclassifies tasks, never
    vetoes plans, and cannot exceed the caps defined in TOKEN_CAPS.

    Parameters
    ----------
    client:
        Async Anthropic client.
    model:
        Model to use (default: claude-haiku-4-5 per registry assignment).
    nivel:
        Objective classification — "nivel_1" or "nivel_2". Determines
        which cap table row applies when no per-task override is provided.
    """

    agent_type = "LogisticsAgent"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-haiku-4-5-20251001",
        nivel: str = "nivel_2_standard",
    ) -> None:
        super().__init__(client, model)
        self._nivel = nivel
        self._cap = TOKEN_CAPS.get(nivel, TOKEN_CAPS["nivel_2_standard"])

    def _get_system_prompt(self) -> str:
        return (
            "You are a LogisticsAgent operating within the PIV/OAC framework. "
            "Your sole responsibility is to estimate token consumption for each "
            "task in an execution DAG BEFORE any specialist agents are launched.\n\n"
            "CRITICAL RULES:\n"
            "- You NEVER emit gate verdicts or veto plans.\n"
            "- You NEVER reclassify task levels.\n"
            f"- Token cap for this objective: {self._cap} tokens per task.\n"
            "- If any single task estimate exceeds 60% of a specialist's context "
            "window, mark it as requiring fragmentation.\n"
            "- Emit WARNING_ANOMALOUS_ESTIMATE if any task estimate exceeds the cap.\n\n"
            "After your analysis you MUST emit the following structured contract block. "
            "Each field must appear on its own line:\n\n"
            "TOTAL_ESTIMATED_TOKENS: <integer — sum across all tasks>\n"
            "TOTAL_ESTIMATED_COST_USD: <float rounded to 6 decimal places>\n"
            "FRAGMENTATION_RECOMMENDED: <comma-separated task IDs that need fragmentation, or NONE>\n"
            "WARNINGS: <WARNING_ANOMALOUS_ESTIMATE: <task_id> exceeds cap messages, or NONE>\n\n"
            "Be conservative: overestimate rather than underestimate."
        )

    def _required_output_fields(self) -> list[str]:
        return [
            "TOTAL_ESTIMATED_TOKENS",
            "TOTAL_ESTIMATED_COST_USD",
            "FRAGMENTATION_RECOMMENDED",
            "WARNINGS",
        ]

    @staticmethod
    def estimate_cost(total_tokens: int) -> float:
        """Return a rough USD cost estimate for the given token count."""
        return round(total_tokens * _COST_PER_1K_TOKENS_USD / 1000, 6)
