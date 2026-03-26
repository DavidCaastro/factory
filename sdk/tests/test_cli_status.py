"""
Tests for `piv status` CLI command.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from piv_oac.cli.main import cli


def _write_checkpoint(root: Path, obj_id: str, data: dict) -> None:
    (root / ".piv" / "active").mkdir(parents=True, exist_ok=True)
    path = root / ".piv" / "active" / f"{obj_id}.json"
    path.write_text(json.dumps(data), encoding="utf-8")


def _minimal_state(obj_id: str = "OBJ-001") -> dict:
    return {
        "objective_id": obj_id,
        "objective_description": "Auth module",
        "fase_actual": 4,
        "modo_meta": False,
        "mitigation_acknowledged": False,
        "gate3_reminder_hours": 24,
        "tareas": {
            "T-01": {"status": "MERGED", "branch": "feature/T-01", "experts": []},
            "T-02": {"status": "IN_PROGRESS", "branch": "feature/T-02", "experts": ["expert-A"]},
        },
        "gates": {"gate1": "APPROVED", "gate2": "PENDING", "gate3": "PENDING"},
        "created_at": "2026-03-22T00:00:00+00:00",
        "updated_at": "2026-03-22T00:00:00+00:00",
    }


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    return tmp_path


def test_status_shows_objective(repo: Path) -> None:
    _write_checkpoint(repo, "OBJ-001", _minimal_state())
    runner = CliRunner()
    # --no-validate avoids git subprocess calls in test
    result = runner.invoke(cli, ["status", "--root", str(repo), "--no-validate"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "OBJ-001" in result.output
    assert "Phase: 4/8" in result.output


def test_status_shows_task_states(repo: Path) -> None:
    _write_checkpoint(repo, "OBJ-001", _minimal_state())
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--root", str(repo), "--no-validate"], catch_exceptions=False)
    assert "T-01" in result.output
    assert "T-02" in result.output


def test_status_no_objectives_message(repo: Path) -> None:
    (repo / ".piv" / "active").mkdir(parents=True)
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--root", str(repo), "--no-validate"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "No active objectives" in result.output


def test_status_no_piv_dir(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--root", str(tmp_path), "--no-validate"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "No .piv/active" in result.output


def test_status_specific_objective(repo: Path) -> None:
    _write_checkpoint(repo, "OBJ-001", _minimal_state())
    _write_checkpoint(repo, "OBJ-002", {**_minimal_state("OBJ-002"), "fase_actual": 2})
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--root", str(repo), "--objective", "OBJ-001", "--no-validate"], catch_exceptions=False)
    assert "OBJ-001" in result.output
    assert "OBJ-002" not in result.output


def test_status_unknown_objective_exits_1(repo: Path) -> None:
    # Need at least one checkpoint so the command reaches the objective lookup
    _write_checkpoint(repo, "OBJ-001", _minimal_state())
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--root", str(repo), "--objective", "OBJ-NOPE", "--no-validate"])
    assert result.exit_code == 1


def test_status_modo_meta_flagged(repo: Path) -> None:
    state = _minimal_state()
    state["modo_meta"] = True
    _write_checkpoint(repo, "OBJ-META", state)
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--root", str(repo), "--no-validate"], catch_exceptions=False)
    assert "MODO_META" in result.output


def test_validate_dry_run_exits_zero_with_issues(tmp_path: Path) -> None:
    """--dry-run returns exit 0 even when issues found."""
    (tmp_path / "specs" / "active").mkdir(parents=True)
    (tmp_path / "specs" / "active" / "INDEX.md").write_text(
        "| Nombre | [PENDIENTE] |\n| execution_mode | DEVELOPMENT |\n"
        "| compliance_scope | MINIMAL |\n| Objetivo en curso | OBJ-001 |\n"
        "| Stack principal | Python |\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(tmp_path), "--no-cross-refs", "--dry-run"])
    assert result.exit_code == 0
    assert "DRY-RUN" in result.output
