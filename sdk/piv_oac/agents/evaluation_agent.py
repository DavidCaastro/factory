"""
PIV/OAC EvaluationAgent — scoring 0-1 for parallel Specialist Agent outputs.

Implements the rubric defined in contracts/evaluation.md:
  FUNC  (0.35) — functional completeness vs. AC list
  SEC   (0.25) — security findings ratio (tool-based)
  QUAL  (0.20) — pytest-cov coverage + ruff violations (tool-based)
  COH   (0.15) — architectural coherence (LLM rubric)
  FOOT  (0.05) — footprint: files_changed vs. files_declared

Constraints (contracts/evaluation.md §Restricciones):
  - Read-only access to expert branches via git show (no checkout)
  - Does NOT emit Gate 1 verdicts (CoherenceAgent exclusive)
  - Does NOT execute early termination autonomously (recommendation only)
  - Cannot write to any expert worktree
"""

from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

_BLOCKED = "BLOQUEADO_POR_HERRAMIENTA"

_WEIGHTS = {
    "FUNC": 0.35,
    "SEC": 0.25,
    "QUAL": 0.20,
    "COH": 0.15,
    "FOOT": 0.05,
}

_EARLY_TERMINATION_THRESHOLD = 0.90
_MIN_EXPERTS_FOR_TOURNAMENT = 2


@dataclass
class FuncInput:
    """Input data for FUNC dimension scoring."""

    acs_covered: int
    acs_partial: int
    acs_total: int


@dataclass
class SecInput:
    """Input data for SEC dimension scoring (tool-based)."""

    findings_critical_high: int
    total_checks: int
    tool: str = "semgrep"


@dataclass
class QualInput:
    """Input data for QUAL dimension scoring (tool-based)."""

    coverage_pct: float  # 0.0 – 100.0
    violations: int
    max_violations_tolerated: int = 10


@dataclass
class CohInput:
    """Input data for COH dimension scoring (LLM rubric — 4 binary items)."""

    implements_in_declared_layer: bool
    no_layer_bypass: bool
    interfaces_match_plan: bool
    no_undeclared_deps: bool


@dataclass
class FootInput:
    """Input data for FOOT dimension scoring (tool-based)."""

    files_changed: int
    files_declared: int


@dataclass
class ScoringResult:
    """Full scoring result for one expert against one task."""

    objective_id: str
    task_id: str
    expert_id: str
    scores_per_criterion: dict[str, dict]
    total_score: float | str  # float or _BLOCKED if aggregate not computable
    winner: bool = False
    early_terminated: bool = False
    evaluator_agent: str = "EvaluationAgent"
    rubric_version: str = "1.0"
    tokens_consumed: int = 0
    timestamp_iso8601: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def to_jsonl_record(self) -> str:
        """Serialize to a single JSONL line."""
        record = {
            "schema_version": "1.0",
            "objective_id": self.objective_id,
            "task_id": self.task_id,
            "expert_id": self.expert_id,
            "timestamp_iso8601": self.timestamp_iso8601,
            "scores_per_criterion": self.scores_per_criterion,
            "total_score": self.total_score,
            "winner": self.winner,
            "early_terminated": self.early_terminated,
            "evaluator_agent": self.evaluator_agent,
            "rubric_version": self.rubric_version,
            "tokens_consumed": self.tokens_consumed,
        }
        return json.dumps(record, ensure_ascii=False)


class EvaluationAgent:
    """
    Scores Specialist Agent outputs on a 0-1 scale across 5 dimensions.

    Tool-based dimensions (deterministic):
      SEC  — uses the provided sec_tool_runner callable or a subprocess fallback
      QUAL — uses coverage_pct and violations from caller-supplied QualInput
      FOOT — uses git diff --stat counts from caller-supplied FootInput

    LLM-based dimensions (structured rubric):
      FUNC — caller supplies FuncInput (AC counts already evaluated)
      COH  — caller supplies CohInput (4 binary checklist items)

    This design keeps the agent testable without mocking LLM calls: FUNC and COH
    use caller-provided structured input rather than free-form LLM text.
    """

    def __init__(
        self,
        logs_dir: Path | None = None,
        sec_tool_runner: Callable[[str], tuple[int, int]] | None = None,
    ) -> None:
        """
        Parameters
        ----------
        logs_dir:
            Directory for JSONL audit trail (logs_scores/). Defaults to
            ./logs_scores relative to cwd.
        sec_tool_runner:
            Optional callable(worktree_path) → (findings_critical_high, total_checks).
            Injected for testing; defaults to subprocess semgrep/bandit call.
        """
        self._logs_dir = logs_dir or (Path.cwd() / "logs_scores")
        self._sec_tool_runner = sec_tool_runner

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def score(
        self,
        objective_id: str,
        task_id: str,
        expert_id: str,
        func: FuncInput,
        sec: SecInput | None,
        qual: QualInput | None,
        coh: CohInput,
        foot: FootInput,
        tokens_consumed: int = 0,
    ) -> ScoringResult:
        """
        Compute the full scoring for one expert on one task.

        Returns a ScoringResult with per-dimension breakdown and weighted total.
        Does NOT write to logs_scores/ automatically — call append_to_log() to persist.
        """
        criteria: dict[str, dict] = {}

        # FUNC
        criteria["FUNC"] = self._score_func(func)

        # SEC
        criteria["SEC"] = self._score_sec(sec)

        # QUAL
        criteria["QUAL"] = self._score_qual(qual)

        # COH
        criteria["COH"] = self._score_coh(coh)

        # FOOT
        criteria["FOOT"] = self._score_foot(foot)

        total = self._compute_total(criteria)

        return ScoringResult(
            objective_id=objective_id,
            task_id=task_id,
            expert_id=expert_id,
            scores_per_criterion=criteria,
            total_score=total,
            tokens_consumed=tokens_consumed,
        )

    def append_to_log(self, result: ScoringResult, session_id: str) -> Path:
        """
        Append *result* as a JSONL record to logs_scores/<session_id>.jsonl.

        Returns the path of the log file.
        The file is append-only: existing records are never modified.
        """
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._logs_dir / f"{session_id}.jsonl"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(result.to_jsonl_record() + "\n")
        return log_path

    def select_winner(self, results: list[ScoringResult]) -> ScoringResult:
        """
        Mark the highest-scoring result as winner and return it.

        Mutates the winner's .winner attribute to True.
        All other results retain winner=False.
        Raises ValueError if results is empty.
        """
        if not results:
            raise ValueError("Cannot select winner from empty results list.")

        valid = [r for r in results if isinstance(r.total_score, float)]
        if not valid:
            raise ValueError("No results with a computable total_score to compare.")

        winner = max(valid, key=lambda r: r.total_score)  # type: ignore[arg-type]
        winner.winner = True
        return winner

    def should_recommend_early_termination(
        self, results: list[ScoringResult], active_experts: int
    ) -> tuple[bool, str | None]:
        """
        Return (True, expert_id) if early termination should be recommended.

        Conditions (contracts/evaluation.md §Resource Policy):
          - active_experts >= MIN_EXPERTS_FOR_TOURNAMENT (2)
          - At least one expert has total_score >= early_termination_threshold (0.90)

        This is a RECOMMENDATION only — the Domain Orchestrator decides.
        """
        if active_experts < _MIN_EXPERTS_FOR_TOURNAMENT:
            return False, None
        for r in results:
            if isinstance(r.total_score, float) and r.total_score >= _EARLY_TERMINATION_THRESHOLD:
                return True, r.expert_id
        return False, None

    # ──────────────────────────────────────────────────────────────────────────
    # Dimension scorers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _score_func(inp: FuncInput) -> dict:
        if inp.acs_total == 0:
            return {"score": _BLOCKED, "tool": None, "acs_covered": 0, "acs_total": 0}
        score = (inp.acs_covered + 0.5 * inp.acs_partial) / inp.acs_total
        score = max(0.0, min(1.0, score))
        return {
            "score": round(score, 4),
            "tool": None,
            "acs_covered": inp.acs_covered,
            "acs_total": inp.acs_total,
        }

    @staticmethod
    def _score_sec(inp: SecInput | None) -> dict:
        if inp is None:
            return {
                "score": _BLOCKED,
                "tool": "semgrep",
                "findings": 0,
                "checks": 0,
                "sec_findings_present": False,
            }
        if inp.total_checks == 0:
            score = 1.0
        else:
            score = max(0.0, 1.0 - (inp.findings_critical_high / inp.total_checks))
        return {
            "score": round(score, 4),
            "tool": inp.tool,
            "findings": inp.findings_critical_high,
            "checks": inp.total_checks,
            "sec_findings_present": inp.findings_critical_high > 0,
        }

    @staticmethod
    def _score_qual(inp: QualInput | None) -> dict:
        if inp is None:
            return {
                "score": _BLOCKED,
                "tool": "pytest-cov+ruff",
                "coverage": 0.0,
                "violations": 0,
            }
        score_cov = max(0.0, min(1.0, inp.coverage_pct / 100.0))
        max_v = max(1, inp.max_violations_tolerated)
        score_ruff = max(0.0, 1.0 - (inp.violations / max_v))
        score = round(0.5 * score_cov + 0.5 * score_ruff, 4)
        return {
            "score": score,
            "tool": "pytest-cov+ruff",
            "coverage": round(inp.coverage_pct, 2),
            "violations": inp.violations,
        }

    @staticmethod
    def _score_coh(inp: CohInput) -> dict:
        items = [
            inp.implements_in_declared_layer,
            inp.no_layer_bypass,
            inp.interfaces_match_plan,
            inp.no_undeclared_deps,
        ]
        score = round(sum(items) / 4, 4)
        return {"score": score, "tool": None, "rationale": f"{sum(items)}/4 rubric items passed"}

    @staticmethod
    def _score_foot(inp: FootInput) -> dict:
        if inp.files_changed == 0:
            score = 1.0
        else:
            score = min(1.0, inp.files_declared / inp.files_changed)
        return {
            "score": round(score, 4),
            "tool": "git diff --stat",
            "files_changed": inp.files_changed,
            "files_declared": inp.files_declared,
        }

    @staticmethod
    def _compute_total(criteria: dict[str, dict]) -> float | str:
        """Weighted sum. Returns _BLOCKED if any dimension is blocked."""
        total = 0.0
        for dim, weight in _WEIGHTS.items():
            score = criteria.get(dim, {}).get("score", _BLOCKED)
            if isinstance(score, str):  # _BLOCKED
                return _BLOCKED
            total += weight * score
        return round(total, 4)
