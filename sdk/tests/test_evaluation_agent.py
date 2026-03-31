"""
Tests for EvaluationAgent — scoring, JSONL output, winner selection.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from piv_oac.agents.evaluation_agent import (
    CohInput,
    EvaluationAgent,
    FootInput,
    FuncInput,
    QualInput,
    SecInput,
    ScoringResult,
)

_BLOCKED = "BLOQUEADO_POR_HERRAMIENTA"


def _agent(tmp_path: Path) -> EvaluationAgent:
    return EvaluationAgent(logs_dir=tmp_path / "logs_scores")


def _perfect_inputs() -> dict:
    return {
        "func": FuncInput(acs_covered=4, acs_partial=0, acs_total=4),
        "sec": SecInput(findings_critical_high=0, total_checks=100, tool="semgrep"),
        "qual": QualInput(coverage_pct=100.0, violations=0),
        "coh": CohInput(
            implements_in_declared_layer=True,
            no_layer_bypass=True,
            interfaces_match_plan=True,
            no_undeclared_deps=True,
        ),
        "foot": FootInput(files_changed=3, files_declared=3),
    }


def _score(tmp_path: Path, **overrides) -> ScoringResult:
    agent = _agent(tmp_path)
    inputs = _perfect_inputs()
    inputs.update(overrides)
    return agent.score(
        objective_id="OBJ-TEST",
        task_id="T-01",
        expert_id="expert-A",
        **inputs,
    )


# ── Basic score structure ─────────────────────────────────────────────────────

def test_score_returns_five_dimensions(tmp_path: Path) -> None:
    result = _score(tmp_path)
    assert set(result.scores_per_criterion.keys()) == {"FUNC", "SEC", "QUAL", "COH", "FOOT"}


def test_score_dimensions_in_range(tmp_path: Path) -> None:
    result = _score(tmp_path)
    for dim, data in result.scores_per_criterion.items():
        s = data["score"]
        assert isinstance(s, float), f"{dim} score should be float, got {type(s)}"
        assert 0.0 <= s <= 1.0, f"{dim} score {s} out of range"


def test_perfect_score_is_one(tmp_path: Path) -> None:
    result = _score(tmp_path)
    assert result.total_score == pytest.approx(1.0, abs=1e-4)


# ── FUNC dimension ────────────────────────────────────────────────────────────

def test_func_partial_coverage(tmp_path: Path) -> None:
    result = _score(tmp_path, func=FuncInput(acs_covered=2, acs_partial=2, acs_total=4))
    assert result.scores_per_criterion["FUNC"]["score"] == pytest.approx(0.75, abs=1e-4)


def test_func_zero_acs_total_is_blocked(tmp_path: Path) -> None:
    result = _score(tmp_path, func=FuncInput(acs_covered=0, acs_partial=0, acs_total=0))
    assert result.scores_per_criterion["FUNC"]["score"] == _BLOCKED
    assert result.total_score == _BLOCKED


# ── SEC dimension ─────────────────────────────────────────────────────────────

def test_sec_no_findings_is_one(tmp_path: Path) -> None:
    result = _score(tmp_path, sec=SecInput(findings_critical_high=0, total_checks=50))
    assert result.scores_per_criterion["SEC"]["score"] == pytest.approx(1.0)
    assert result.scores_per_criterion["SEC"]["sec_findings_present"] is False


def test_sec_findings_present_flag(tmp_path: Path) -> None:
    result = _score(tmp_path, sec=SecInput(findings_critical_high=5, total_checks=100))
    assert result.scores_per_criterion["SEC"]["sec_findings_present"] is True
    assert result.scores_per_criterion["SEC"]["score"] == pytest.approx(0.95)


def test_sec_none_returns_blocked(tmp_path: Path) -> None:
    result = _score(tmp_path, sec=None)
    assert result.scores_per_criterion["SEC"]["score"] == _BLOCKED


# ── QUAL dimension ────────────────────────────────────────────────────────────

def test_qual_full_coverage_no_violations(tmp_path: Path) -> None:
    result = _score(tmp_path, qual=QualInput(coverage_pct=100.0, violations=0))
    assert result.scores_per_criterion["QUAL"]["score"] == pytest.approx(1.0)


def test_qual_50_coverage_5_violations(tmp_path: Path) -> None:
    result = _score(tmp_path, qual=QualInput(coverage_pct=50.0, violations=5, max_violations_tolerated=10))
    expected = 0.5 * 0.5 + 0.5 * 0.5  # score_cov=0.5, score_ruff=0.5
    assert result.scores_per_criterion["QUAL"]["score"] == pytest.approx(expected, abs=1e-4)


def test_qual_none_returns_blocked(tmp_path: Path) -> None:
    result = _score(tmp_path, qual=None)
    assert result.scores_per_criterion["QUAL"]["score"] == _BLOCKED


# ── COH dimension ─────────────────────────────────────────────────────────────

def test_coh_all_pass(tmp_path: Path) -> None:
    result = _score(tmp_path)
    assert result.scores_per_criterion["COH"]["score"] == pytest.approx(1.0)


def test_coh_two_failures(tmp_path: Path) -> None:
    coh = CohInput(
        implements_in_declared_layer=True,
        no_layer_bypass=False,
        interfaces_match_plan=True,
        no_undeclared_deps=False,
    )
    result = _score(tmp_path, coh=coh)
    assert result.scores_per_criterion["COH"]["score"] == pytest.approx(0.5)


# ── FOOT dimension ────────────────────────────────────────────────────────────

def test_foot_exact_footprint(tmp_path: Path) -> None:
    result = _score(tmp_path, foot=FootInput(files_changed=5, files_declared=5))
    assert result.scores_per_criterion["FOOT"]["score"] == pytest.approx(1.0)


def test_foot_over_footprint(tmp_path: Path) -> None:
    result = _score(tmp_path, foot=FootInput(files_changed=10, files_declared=5))
    assert result.scores_per_criterion["FOOT"]["score"] == pytest.approx(0.5)


def test_foot_under_footprint_capped_at_one(tmp_path: Path) -> None:
    result = _score(tmp_path, foot=FootInput(files_changed=3, files_declared=5))
    assert result.scores_per_criterion["FOOT"]["score"] == pytest.approx(1.0)


# ── Total score weights ───────────────────────────────────────────────────────

def test_total_score_is_weighted_sum(tmp_path: Path) -> None:
    # Only FUNC=1, all others=0
    result = _score(
        tmp_path,
        func=FuncInput(acs_covered=1, acs_partial=0, acs_total=1),
        sec=SecInput(findings_critical_high=100, total_checks=100),  # score=0
        qual=QualInput(coverage_pct=0.0, violations=100, max_violations_tolerated=1),
        coh=CohInput(
            implements_in_declared_layer=False,
            no_layer_bypass=False,
            interfaces_match_plan=False,
            no_undeclared_deps=False,
        ),
        foot=FootInput(files_changed=100, files_declared=1),
    )
    assert isinstance(result.total_score, float)
    # FUNC weight = 0.35, all others ≈ 0
    assert result.total_score == pytest.approx(0.35, abs=0.01)


# ── JSONL output ──────────────────────────────────────────────────────────────

def test_append_to_log_creates_file(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    result = _score(tmp_path)
    log_path = agent.append_to_log(result, session_id="test-session")
    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["schema_version"] == "1.0"
    assert record["objective_id"] == "OBJ-TEST"


def test_append_to_log_is_append_only(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    for i in range(3):
        result = _score(tmp_path)
        result.expert_id = f"expert-{i}"
        agent.append_to_log(result, session_id="session-1")
    lines = (tmp_path / "logs_scores" / "session-1.jsonl").read_text().strip().splitlines()
    assert len(lines) == 3


def test_jsonl_total_score_matches_criteria(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    result = _score(tmp_path)
    log_path = agent.append_to_log(result, session_id="verify")
    record = json.loads(log_path.read_text().strip())
    # Recompute expected total
    from piv_oac.agents.evaluation_agent import _WEIGHTS
    expected = sum(
        _WEIGHTS[d] * record["scores_per_criterion"][d]["score"]
        for d in _WEIGHTS
    )
    assert record["total_score"] == pytest.approx(expected, abs=1e-3)


# ── Winner selection ──────────────────────────────────────────────────────────

def test_select_winner_marks_highest(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    low = _score(tmp_path, sec=SecInput(findings_critical_high=50, total_checks=100))
    high = _score(tmp_path)
    winner = agent.select_winner([low, high])
    assert winner.winner is True
    assert winner is high


def test_select_winner_empty_raises(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    with pytest.raises(ValueError):
        agent.select_winner([])


# ── Early termination recommendation ─────────────────────────────────────────

def test_early_termination_recommends_when_threshold_met(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    high = _score(tmp_path)  # total_score ≈ 1.0
    recommend, expert_id = agent.should_recommend_early_termination([high], active_experts=2)
    assert recommend is True
    assert expert_id == "expert-A"


def test_early_termination_no_recommendation_single_expert(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    high = _score(tmp_path)
    recommend, _ = agent.should_recommend_early_termination([high], active_experts=1)
    assert recommend is False


def test_early_termination_no_recommendation_below_threshold(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    low = _score(tmp_path, sec=SecInput(findings_critical_high=50, total_checks=100))
    recommend, _ = agent.should_recommend_early_termination([low], active_experts=2)
    assert recommend is False
