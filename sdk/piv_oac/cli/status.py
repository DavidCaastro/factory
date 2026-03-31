"""
piv status — Show current PIV/OAC objective state from .piv/active/.

Reads the canonical JSON (not the summary .md) and prints a structured
status table. Also runs checkpoint validation and flags divergences.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from piv_oac.checkpoint.validator import CheckpointValidator


def _find_root() -> Path:
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / ".git").exists():
            return candidate
    return cwd


def _status_icon(value: str) -> str:
    mapping = {
        "APPROVED": "APPROVED",
        "REJECTED": "REJECTED",
        "PENDING": "pending",
        "MERGED": "merged",
        "IN_PROGRESS": "running",
        "GATE1_APPROVED": "gate1-ok",
        "GATE2_APPROVED": "gate2-ok",
    }
    return mapping.get(value, value)


@click.command("status")
@click.option("--objective", "-o", default=None, help="Objective ID to inspect. Defaults to all active.")
@click.option("--validate/--no-validate", default=True, help="Run checkpoint validation (default: on).")
@click.option("--root", "root_path", default=None, type=click.Path(exists=True, file_okay=False), help="Repository root (default: auto-detected from CWD).")
def status(objective: str | None, validate: bool, root_path: str | None) -> None:
    """Show current PIV/OAC objective status from .piv/active/.

    Reads the canonical JSON source of truth and prints phase, task states,
    and gate approvals. Optionally validates consistency with git state.
    """
    root = Path(root_path).resolve() if root_path else _find_root()
    piv_active = root / ".piv" / "active"

    if not piv_active.is_dir():
        click.echo("No .piv/active/ directory found. No active objectives.")
        click.echo("Run 'piv init' to bootstrap a project.")
        return

    json_files = sorted(piv_active.glob("*.json"))
    json_files = [f for f in json_files if not f.name.endswith("_summary.json")]

    if not json_files:
        click.echo("No active objectives in .piv/active/.")
        return

    if objective:
        target = piv_active / f"{objective}.json"
        if not target.exists():
            click.echo(f"[ERROR] Objective '{objective}' not found in .piv/active/", err=True)
            sys.exit(1)
        json_files = [target]

    for json_file in json_files:
        _print_objective(json_file)

    if validate:
        click.echo("")
        validator = CheckpointValidator(repo_root=root)
        if objective:
            report = validator.validate_objective(json_file.stem)
        else:
            report = validator.validate_all()

        click.echo(report.format())
        if not report.passed:
            sys.exit(1)


def _print_objective(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        click.echo(f"[ERROR] Cannot read {path.name}: {exc}", err=True)
        return

    obj_id = data.get("objective_id", path.stem)
    fase = data.get("fase_actual", "?")
    desc = data.get("objective_description", "")
    modo_meta = " [MODO_META]" if data.get("modo_meta") else ""

    click.echo(f"\nObjective: {obj_id}{modo_meta}")
    if desc:
        click.echo(f"  {desc}")
    click.echo(f"  Phase: {fase}/8")

    # Gates
    gates = data.get("gates", {})
    click.echo(
        f"  Gates: "
        f"G1={_status_icon(gates.get('gate1','?'))}  "
        f"G2={_status_icon(gates.get('gate2','?'))}  "
        f"G3={_status_icon(gates.get('gate3','?'))}"
    )

    # Tasks
    tareas = data.get("tareas", {})
    if tareas:
        click.echo(f"  Tasks ({len(tareas)}):")
        for task_id, task in sorted(tareas.items()):
            st = _status_icon(task.get("status", "?"))
            branch = task.get("branch", "")
            experts = task.get("experts", [])
            expert_str = f"  [{', '.join(experts)}]" if experts else ""
            click.echo(f"    {task_id:12} {st:14} {branch}{expert_str}")
    else:
        click.echo("  Tasks: none recorded")
