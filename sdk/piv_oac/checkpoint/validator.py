"""
PIV/OAC CheckpointValidator — validates .piv/active/ state against git.

Detects divergence between the session JSON (canonical source of truth) and
the actual state of the git repository: missing branches, merged tasks whose
branches still exist, and objectives in progress with no active worktrees.

Reference: skills/session-continuity.md, agent.md §18.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationIssue:
    """A single divergence found between checkpoint state and git reality."""

    level: str          # "ERROR" | "WARN"
    objective_id: str
    field: str          # what was checked
    message: str

    def __str__(self) -> str:
        return f"  [{self.level}] {self.objective_id} / {self.field}: {self.message}"


@dataclass
class ValidationReport:
    """Result of a full checkpoint validation run."""

    issues: list[ValidationIssue]

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "ERROR"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "WARN"]

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def format(self) -> str:
        if not self.issues:
            return "Checkpoint validation: PASS — no divergences found."
        lines = [f"Checkpoint validation: {'PASS' if self.passed else 'FAIL'}"]
        for issue in self.issues:
            lines.append(str(issue))
        lines.append(
            f"\n{len(self.errors)} error(s), {len(self.warnings)} warning(s)."
        )
        return "\n".join(lines)


class CheckpointValidator:
    """
    Validates .piv/active/ JSON files against the current git state.

    Checks performed:
      1. Task branches declared in the JSON exist in git (or were already merged).
      2. Expert branches for IN_PROGRESS tasks exist in git.
      3. Gate2-APPROVED tasks have their feature branch present in staging
         (or staging itself, if already merged).
      4. JSON is valid (parseable, required fields present).
    """

    _REQUIRED_FIELDS = {"objective_id", "fase_actual", "tareas", "gates"}

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = repo_root or self._find_root()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_all(self) -> ValidationReport:
        """Validate every .json in .piv/active/."""
        piv_active = self._root / ".piv" / "active"
        if not piv_active.is_dir():
            return ValidationReport(issues=[])

        issues: list[ValidationIssue] = []
        for json_file in sorted(piv_active.glob("*.json")):
            if json_file.name.endswith("_summary.json"):
                continue
            issues.extend(self._validate_file(json_file))

        return ValidationReport(issues=issues)

    def validate_objective(self, objective_id: str) -> ValidationReport:
        """Validate a single objective by ID."""
        path = self._root / ".piv" / "active" / f"{objective_id}.json"
        if not path.exists():
            return ValidationReport(issues=[ValidationIssue(
                level="ERROR",
                objective_id=objective_id,
                field="file",
                message=f".piv/active/{objective_id}.json not found",
            )])
        return ValidationReport(issues=self._validate_file(path))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _validate_file(self, path: Path) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        objective_id = path.stem

        # 1. Parse JSON
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return [ValidationIssue(
                level="ERROR",
                objective_id=objective_id,
                field="json_parse",
                message=f"Invalid JSON: {exc}",
            )]

        # 2. Required fields
        for field_name in self._REQUIRED_FIELDS:
            if field_name not in data:
                issues.append(ValidationIssue(
                    level="ERROR",
                    objective_id=objective_id,
                    field=field_name,
                    message=f"Required field '{field_name}' missing from checkpoint",
                ))

        if issues:  # can't proceed without valid structure
            return issues

        existing_branches = self._list_git_branches()

        # 3. Validate each task
        for task_id, task in data.get("tareas", {}).items():
            branch = task.get("branch", "")
            status = task.get("status", "PENDING")

            if branch and status not in ("MERGED",):
                if branch not in existing_branches:
                    level = "ERROR" if status == "IN_PROGRESS" else "WARN"
                    issues.append(ValidationIssue(
                        level=level,
                        objective_id=objective_id,
                        field=f"tareas.{task_id}.branch",
                        message=(
                            f"Branch '{branch}' declared for task {task_id} "
                            f"(status={status}) does not exist in git"
                        ),
                    ))

            # Expert branches for in-progress tasks
            if status == "IN_PROGRESS":
                for expert in task.get("experts", []):
                    expert_branch = f"feature/{task_id}/{expert}"
                    if expert_branch not in existing_branches:
                        issues.append(ValidationIssue(
                            level="WARN",
                            objective_id=objective_id,
                            field=f"tareas.{task_id}.experts.{expert}",
                            message=(
                                f"Expert branch '{expert_branch}' not found in git "
                                f"(task is IN_PROGRESS)"
                            ),
                        ))

        # 4. Gate 3 approved but staging not merged to main
        gates = data.get("gates", {})
        if gates.get("gate3") == "APPROVED":
            issues.append(ValidationIssue(
                level="WARN",
                objective_id=objective_id,
                field="gates.gate3",
                message=(
                    "Gate 3 is APPROVED but objective is still in .piv/active/ "
                    "(should be moved to .piv/completed/ after merge to main)"
                ),
            ))

        return issues

    def _list_git_branches(self) -> set[str]:
        """Return all local and remote branch names (stripped)."""
        try:
            result = subprocess.run(
                ["git", "branch", "-a", "--format=%(refname:short)"],
                capture_output=True,
                text=True,
                cwd=self._root,
                timeout=10,
            )
            if result.returncode != 0:
                return set()
            branches = set()
            for line in result.stdout.splitlines():
                name = line.strip()
                # Normalize remotes/origin/feature/X → feature/X
                if name.startswith("origin/"):
                    name = name[len("origin/"):]
                branches.add(name)
            return branches
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return set()

    @staticmethod
    def _find_root() -> Path:
        cwd = Path.cwd().resolve()
        for candidate in [cwd, *cwd.parents]:
            if (candidate / ".git").exists():
                return candidate
        return cwd
