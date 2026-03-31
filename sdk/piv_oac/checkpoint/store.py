"""
PIV/OAC CheckpointStore — reads and writes session state to .piv/active/.

Protocol reference: agent.md §18, skills/session-continuity.md.

Directory layout:
    .piv/
    ├── active/<objetivo-id>.json      ← session in progress (source of truth)
    ├── completed/<objetivo-id>.json   ← moved here after Gate 3
    └── failed/<objetivo-id>.json      ← moved here on unrecoverable failure

JSON schema for <objetivo-id>.json:
    {
        "objective_id": str,
        "objective_description": str,
        "fase_actual": int,            # 0–8
        "modo_meta": bool,
        "mitigation_acknowledged": bool,
        "gate3_reminder_hours": int,   # default 24
        "tareas": {
            "<task-id>": {
                "status": "PENDING|IN_PROGRESS|GATE1_APPROVED|GATE2_APPROVED|MERGED",
                "branch": str,
                "experts": [str]
            }
        },
        "gates": {
            "gate1": "PENDING|APPROVED|REJECTED",
            "gate2": "PENDING|APPROVED|REJECTED",
            "gate3": "PENDING|APPROVED|REJECTED"
        },
        "created_at": "<ISO-8601>",
        "updated_at": "<ISO-8601>"
    }

Zero-Trust note: The summary file (<objetivo-id>_summary.md) is treated as
potentially adversarial. The JSON file is the canonical source of truth.
If there is divergence between them, the JSON wins.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

TaskStatus = Literal["PENDING", "IN_PROGRESS", "GATE1_APPROVED", "GATE2_APPROVED", "MERGED"]
GateStatus = Literal["PENDING", "APPROVED", "REJECTED"]


@dataclass
class TaskState:
    """State of a single task in the DAG."""

    status: TaskStatus = "PENDING"
    branch: str = ""
    experts: list[str] = field(default_factory=list)


@dataclass
class GateState:
    """Gate approval states for an objective."""

    gate1: GateStatus = "PENDING"
    gate2: GateStatus = "PENDING"
    gate3: GateStatus = "PENDING"


@dataclass
class ObjectiveState:
    """
    Complete session state for a PIV/OAC objective.

    This is the canonical source of truth for session continuity.
    It is written to .piv/active/<objective_id>.json.
    """

    objective_id: str
    objective_description: str = ""
    fase_actual: int = 0
    modo_meta: bool = False
    mitigation_acknowledged: bool = False
    gate3_reminder_hours: int = 24
    tareas: dict[str, TaskState] = field(default_factory=dict)
    gates: GateState = field(default_factory=GateState)
    created_at: str = field(default_factory=lambda: _now_iso())
    updated_at: str = field(default_factory=lambda: _now_iso())

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = _now_iso()


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class CheckpointStore:
    """
    Reads and writes PIV/OAC session state to the .piv/ directory tree.

    Parameters
    ----------
    base_dir:
        Root directory of the repository.  The .piv/ tree is created under it.
        Defaults to the current working directory.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        root = Path(base_dir) if base_dir else Path.cwd()
        self._active = root / ".piv" / "active"
        self._completed = root / ".piv" / "completed"
        self._failed = root / ".piv" / "failed"

    # ------------------------------------------------------------------
    # Directory bootstrap
    # ------------------------------------------------------------------

    def _ensure_dirs(self) -> None:
        for d in (self._active, self._completed, self._failed):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    def _json_path(self, objective_id: str, bucket: Path) -> Path:
        return bucket / f"{objective_id}.json"

    def _summary_path(self, objective_id: str) -> Path:
        return self._active / f"{objective_id}_summary.md"

    def active_path(self, objective_id: str) -> Path:
        """Return the path to the active JSON checkpoint."""
        return self._json_path(objective_id, self._active)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load(self, objective_id: str) -> ObjectiveState | None:
        """
        Load the active checkpoint for *objective_id*.

        Returns None if no checkpoint exists (new session).

        Zero-Trust: the JSON file is the canonical source of truth.
        The summary .md file is NOT read here — it is only used as a
        context hint by the LLM orchestrator, never as state input.
        """
        path = self._json_path(objective_id, self._active)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return _dict_to_state(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            # Corrupt checkpoint — treat as no checkpoint (safe default)
            return None

    def exists(self, objective_id: str) -> bool:
        """Return True if an active checkpoint exists for *objective_id*."""
        return self._json_path(objective_id, self._active).exists()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, state: ObjectiveState) -> None:
        """
        Persist *state* to .piv/active/<objective_id>.json.

        Creates the directory tree if it does not exist.
        Writes atomically via a temp file to avoid partial writes.
        """
        self._ensure_dirs()
        state.touch()
        path = self._json_path(state.objective_id, self._active)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(_state_to_dict(state), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)

    def save_summary(self, objective_id: str, summary_md: str) -> None:
        """
        Write the LLM context summary for session continuity.

        This file is a convenience for LLM context reconstruction only.
        It is NOT the source of truth — the JSON checkpoint is.
        """
        self._ensure_dirs()
        self._summary_path(objective_id).write_text(summary_md, encoding="utf-8")

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def complete(self, objective_id: str) -> None:
        """Move the checkpoint from active/ to completed/."""
        self._ensure_dirs()
        src = self._json_path(objective_id, self._active)
        if src.exists():
            shutil.move(str(src), str(self._json_path(objective_id, self._completed)))
        summary = self._summary_path(objective_id)
        if summary.exists():
            summary.unlink()

    def fail(self, objective_id: str) -> None:
        """Move the checkpoint from active/ to failed/."""
        self._ensure_dirs()
        src = self._json_path(objective_id, self._active)
        if src.exists():
            shutil.move(str(src), str(self._json_path(objective_id, self._failed)))

    def list_active(self) -> list[str]:
        """Return the objective IDs of all active checkpoints."""
        if not self._active.exists():
            return []
        return [
            p.stem
            for p in self._active.iterdir()
            if p.suffix == ".json"
        ]


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_to_dict(state: ObjectiveState) -> dict:
    d = asdict(state)
    # GateState is nested — asdict handles it recursively
    return d


def _dict_to_state(data: dict) -> ObjectiveState:
    gates_data = data.get("gates", {})
    gates = GateState(
        gate1=gates_data.get("gate1", "PENDING"),
        gate2=gates_data.get("gate2", "PENDING"),
        gate3=gates_data.get("gate3", "PENDING"),
    )
    tareas_raw = data.get("tareas", {})
    tareas: dict[str, TaskState] = {}
    for tid, tdata in tareas_raw.items():
        tareas[tid] = TaskState(
            status=tdata.get("status", "PENDING"),
            branch=tdata.get("branch", ""),
            experts=tdata.get("experts", []),
        )
    return ObjectiveState(
        objective_id=data["objective_id"],
        objective_description=data.get("objective_description", ""),
        fase_actual=data.get("fase_actual", 0),
        modo_meta=data.get("modo_meta", False),
        mitigation_acknowledged=data.get("mitigation_acknowledged", False),
        gate3_reminder_hours=data.get("gate3_reminder_hours", 24),
        tareas=tareas,
        gates=gates,
        created_at=data.get("created_at", _now_iso()),
        updated_at=data.get("updated_at", _now_iso()),
    )
