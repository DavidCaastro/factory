"""
Tests for CheckpointValidator — .piv/active/ consistency with git.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from piv_oac.checkpoint.validator import CheckpointValidator, ValidationIssue, ValidationReport


def _write_checkpoint(piv_dir: Path, obj_id: str, data: dict) -> Path:
    path = piv_dir / f"{obj_id}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _minimal_state(obj_id: str = "OBJ-001") -> dict:
    return {
        "objective_id": obj_id,
        "objective_description": "Test objective",
        "fase_actual": 3,
        "modo_meta": False,
        "mitigation_acknowledged": False,
        "gate3_reminder_hours": 24,
        "tareas": {},
        "gates": {"gate1": "PENDING", "gate2": "PENDING", "gate3": "PENDING"},
        "created_at": "2026-03-22T00:00:00+00:00",
        "updated_at": "2026-03-22T00:00:00+00:00",
    }


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Minimal fake git repo with .piv/active/."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".piv" / "active").mkdir(parents=True)
    return tmp_path


def _validator(repo: Path, branches: list[str] | None = None) -> CheckpointValidator:
    v = CheckpointValidator(repo_root=repo)
    mock_branches = set(branches or [])
    v._list_git_branches = MagicMock(return_value=mock_branches)  # type: ignore[method-assign]
    return v


# ── No active objectives ──────────────────────────────────────────────────────

def test_validate_all_empty_dir(repo: Path) -> None:
    v = _validator(repo)
    report = v.validate_all()
    assert report.passed
    assert report.issues == []


def test_validate_all_no_piv_dir(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    v = CheckpointValidator(repo_root=tmp_path)
    report = v.validate_all()
    assert report.passed


# ── Valid checkpoint, no task branches ───────────────────────────────────────

def test_validate_passes_for_clean_state(repo: Path) -> None:
    _write_checkpoint(repo / ".piv" / "active", "OBJ-001", _minimal_state())
    v = _validator(repo)
    report = v.validate_all()
    assert report.passed


# ── Required fields ───────────────────────────────────────────────────────────

def test_missing_required_field_is_error(repo: Path) -> None:
    state = _minimal_state()
    del state["fase_actual"]
    _write_checkpoint(repo / ".piv" / "active", "OBJ-001", state)
    v = _validator(repo)
    report = v.validate_all()
    assert not report.passed
    assert any("fase_actual" in i.field for i in report.errors)


def test_invalid_json_is_error(repo: Path) -> None:
    path = repo / ".piv" / "active" / "OBJ-BAD.json"
    path.write_text("not valid json {{{", encoding="utf-8")
    v = _validator(repo)
    report = v.validate_all()
    assert not report.passed
    assert any(i.level == "ERROR" for i in report.issues)


# ── Task branch validation ────────────────────────────────────────────────────

def test_in_progress_task_missing_branch_is_error(repo: Path) -> None:
    state = _minimal_state()
    state["tareas"]["T-01"] = {
        "status": "IN_PROGRESS",
        "branch": "feature/T-01",
        "experts": [],
    }
    _write_checkpoint(repo / ".piv" / "active", "OBJ-001", state)
    v = _validator(repo, branches=[])  # branch does not exist
    report = v.validate_all()
    assert not report.passed
    assert any("feature/T-01" in i.message for i in report.errors)


def test_in_progress_task_branch_exists_is_ok(repo: Path) -> None:
    state = _minimal_state()
    state["tareas"]["T-01"] = {
        "status": "IN_PROGRESS",
        "branch": "feature/T-01",
        "experts": [],
    }
    _write_checkpoint(repo / ".piv" / "active", "OBJ-001", state)
    v = _validator(repo, branches=["feature/T-01"])
    report = v.validate_all()
    assert report.passed


def test_pending_task_missing_branch_is_warning(repo: Path) -> None:
    state = _minimal_state()
    state["tareas"]["T-02"] = {
        "status": "PENDING",
        "branch": "feature/T-02",
        "experts": [],
    }
    _write_checkpoint(repo / ".piv" / "active", "OBJ-001", state)
    v = _validator(repo, branches=[])
    report = v.validate_all()
    assert report.passed  # WARN does not fail
    assert any(i.level == "WARN" for i in report.warnings)


def test_merged_task_branch_missing_is_ok(repo: Path) -> None:
    state = _minimal_state()
    state["tareas"]["T-01"] = {
        "status": "MERGED",
        "branch": "feature/T-01",
        "experts": [],
    }
    _write_checkpoint(repo / ".piv" / "active", "OBJ-001", state)
    v = _validator(repo, branches=[])  # branch gone after merge — expected
    report = v.validate_all()
    assert report.passed


# ── Expert branch validation ──────────────────────────────────────────────────

def test_in_progress_expert_branch_missing_is_warning(repo: Path) -> None:
    state = _minimal_state()
    state["tareas"]["T-01"] = {
        "status": "IN_PROGRESS",
        "branch": "feature/T-01",
        "experts": ["expert-A"],
    }
    _write_checkpoint(repo / ".piv" / "active", "OBJ-001", state)
    # Provide task branch but not expert branch
    v = _validator(repo, branches=["feature/T-01"])
    report = v.validate_all()
    assert any("feature/T-01/expert-A" in i.message for i in report.warnings)


# ── Gate 3 stale warning ──────────────────────────────────────────────────────

def test_gate3_approved_in_active_is_warning(repo: Path) -> None:
    state = _minimal_state()
    state["gates"]["gate3"] = "APPROVED"
    _write_checkpoint(repo / ".piv" / "active", "OBJ-001", state)
    v = _validator(repo)
    report = v.validate_all()
    assert any("gate3" in i.field for i in report.warnings)


# ── validate_objective ────────────────────────────────────────────────────────

def test_validate_objective_not_found_is_error(repo: Path) -> None:
    v = _validator(repo)
    report = v.validate_objective("OBJ-MISSING")
    assert not report.passed
    assert any("not found" in i.message for i in report.errors)


# ── ValidationReport helpers ──────────────────────────────────────────────────

def test_report_format_pass() -> None:
    report = ValidationReport(issues=[])
    assert "PASS" in report.format()


def test_report_format_fail() -> None:
    issue = ValidationIssue(level="ERROR", objective_id="OBJ-X", field="f", message="broken")
    report = ValidationReport(issues=[issue])
    assert "FAIL" in report.format()
    assert "broken" in report.format()
