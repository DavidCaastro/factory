"""Tests for CheckpointStore — agent.md §18, skills/session-continuity.md."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from piv_oac.checkpoint.store import (
    CheckpointStore,
    ObjectiveState,
    TaskState,
    GateState,
)


@pytest.fixture
def tmp_store(tmp_path):
    """Return a CheckpointStore rooted at a temporary directory."""
    return CheckpointStore(base_dir=tmp_path)


@pytest.fixture
def sample_state():
    state = ObjectiveState(
        objective_id="obj-test-01",
        objective_description="Test objective",
        fase_actual=2,
        modo_meta=False,
        mitigation_acknowledged=False,
    )
    state.tareas["T-01"] = TaskState(status="IN_PROGRESS", branch="feature/t01")
    state.gates.gate1 = "APPROVED"
    return state


class TestSaveAndLoad:
    def test_save_creates_json_file(self, tmp_store, sample_state):
        tmp_store.save(sample_state)
        path = tmp_store.active_path("obj-test-01")
        assert path.exists()

    def test_load_returns_correct_state(self, tmp_store, sample_state):
        tmp_store.save(sample_state)
        loaded = tmp_store.load("obj-test-01")
        assert loaded is not None
        assert loaded.objective_id == "obj-test-01"
        assert loaded.fase_actual == 2
        assert loaded.gates.gate1 == "APPROVED"

    def test_load_returns_none_when_not_exists(self, tmp_store):
        assert tmp_store.load("nonexistent-obj") is None

    def test_save_is_atomic(self, tmp_store, sample_state):
        tmp_store.save(sample_state)
        # No .tmp file should remain after save
        tmp = tmp_store.active_path("obj-test-01").with_suffix(".tmp")
        assert not tmp.exists()

    def test_save_updates_updated_at(self, tmp_store, sample_state):
        original_ts = sample_state.updated_at
        import time; time.sleep(0.01)
        tmp_store.save(sample_state)
        loaded = tmp_store.load("obj-test-01")
        assert loaded.updated_at >= original_ts

    def test_corrupt_json_returns_none(self, tmp_store):
        tmp_store._ensure_dirs()
        path = tmp_store.active_path("corrupt-obj")
        path.write_text("{bad json", encoding="utf-8")
        assert tmp_store.load("corrupt-obj") is None


class TestTaskState:
    def test_task_state_persists(self, tmp_store, sample_state):
        tmp_store.save(sample_state)
        loaded = tmp_store.load("obj-test-01")
        assert "T-01" in loaded.tareas
        assert loaded.tareas["T-01"].status == "IN_PROGRESS"
        assert loaded.tareas["T-01"].branch == "feature/t01"

    def test_multiple_tasks(self, tmp_store):
        state = ObjectiveState(objective_id="obj-multi")
        state.tareas["T-01"] = TaskState(status="MERGED", branch="feature/t01", experts=["exp-1"])
        state.tareas["T-02"] = TaskState(status="PENDING", branch="feature/t02")
        tmp_store.save(state)
        loaded = tmp_store.load("obj-multi")
        assert loaded.tareas["T-01"].status == "MERGED"
        assert loaded.tareas["T-01"].experts == ["exp-1"]
        assert loaded.tareas["T-02"].status == "PENDING"


class TestLifecycle:
    def test_complete_moves_to_completed(self, tmp_store, sample_state):
        tmp_store.save(sample_state)
        tmp_store.complete("obj-test-01")
        assert not tmp_store.active_path("obj-test-01").exists()
        assert (tmp_store._completed / "obj-test-01.json").exists()

    def test_fail_moves_to_failed(self, tmp_store, sample_state):
        tmp_store.save(sample_state)
        tmp_store.fail("obj-test-01")
        assert not tmp_store.active_path("obj-test-01").exists()
        assert (tmp_store._failed / "obj-test-01.json").exists()

    def test_complete_nonexistent_does_not_raise(self, tmp_store):
        tmp_store.complete("ghost-obj")  # should not raise

    def test_list_active(self, tmp_store):
        for i in range(3):
            s = ObjectiveState(objective_id=f"obj-{i}")
            tmp_store.save(s)
        ids = tmp_store.list_active()
        assert set(ids) == {"obj-0", "obj-1", "obj-2"}

    def test_list_active_empty(self, tmp_store):
        assert tmp_store.list_active() == []


class TestSummary:
    def test_save_summary_creates_file(self, tmp_store):
        tmp_store.save_summary("obj-test-01", "# Summary\nThis is context for the LLM.")
        summary = tmp_store._active / "obj-test-01_summary.md"
        assert summary.exists()
        assert "Summary" in summary.read_text()

    def test_complete_removes_summary(self, tmp_store, sample_state):
        tmp_store.save(sample_state)
        tmp_store.save_summary("obj-test-01", "# Summary")
        tmp_store.complete("obj-test-01")
        summary = tmp_store._active / "obj-test-01_summary.md"
        assert not summary.exists()


class TestExists:
    def test_exists_true_after_save(self, tmp_store, sample_state):
        tmp_store.save(sample_state)
        assert tmp_store.exists("obj-test-01")

    def test_exists_false_before_save(self, tmp_store):
        assert not tmp_store.exists("obj-test-01")
