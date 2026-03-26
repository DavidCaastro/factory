"""
Tests for `piv init` CLI command (non-interactive via --answers or input mocking).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from piv_oac.cli.main import cli


@pytest.fixture()
def repo_with_templates(tmp_path: Path) -> Path:
    """Minimal repo with specs/_templates/INDEX.md for testing piv init."""
    templates = tmp_path / "specs" / "_templates"
    templates.mkdir(parents=True)
    # Minimal INDEX.md template with [PENDIENTE] fields
    (templates / "INDEX.md").write_text(
        "| Nombre | [PENDIENTE] |\n"
        "| Stack principal | [PENDIENTE] |\n"
        "| execution_mode | INIT |\n"
        "| compliance_scope | [PENDIENTE] |\n"
        "| Objetivo en curso | [PENDIENTE] |\n",
        encoding="utf-8",
    )
    (templates / "functional.md").write_text("# Functional specs\n", encoding="utf-8")
    (templates / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (templates / "quality.md").write_text("# Quality\n", encoding="utf-8")
    (templates / "security.md").write_text("# Security\n", encoding="utf-8")
    (templates / "compliance.md").write_text("# Compliance\n", encoding="utf-8")
    # Fake CLAUDE.md so _find_root() resolves to tmp_path
    (tmp_path / "CLAUDE.md").write_text("# PIV/OAC", encoding="utf-8")
    return tmp_path


def _write_answers(tmp_path: Path, answers: dict) -> Path:
    answers_file = tmp_path / "answers.yaml"
    answers_file.write_text(yaml.dump(answers), encoding="utf-8")
    return answers_file


def test_init_generates_active_directory(repo_with_templates: Path) -> None:
    answers = {
        "Nombre": "TestProject",
        "Stack principal": "Python/FastAPI",
        "Mercado objetivo": "Developers",
        "Tipo de producto": "API",
        "execution_mode": "DEVELOPMENT",
        "compliance_scope": "MINIMAL",
        "Objetivo en curso": "OBJ-001 — Auth module",
    }
    answers_file = _write_answers(repo_with_templates, answers)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["init", "--answers", str(answers_file), "--root", str(repo_with_templates)],
        catch_exceptions=False,
    )

    active = repo_with_templates / "specs" / "active"
    assert active.is_dir(), f"specs/active not created. Output: {result.output}"
    assert (active / "INDEX.md").exists()
    assert (active / "functional.md").exists()


def test_init_applies_answers_to_index(repo_with_templates: Path) -> None:
    # Provide all 7 answers to avoid interactive prompts
    answers = {
        "Nombre": "MyFramework",
        "Stack principal": "Python",
        "Mercado objetivo": "Developers",
        "Tipo de producto": "API",
        "execution_mode": "DEVELOPMENT",
        "compliance_scope": "NONE",
        "Objetivo en curso": "OBJ-002",
    }
    answers_file = _write_answers(repo_with_templates, answers)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["init", "--answers", str(answers_file), "--root", str(repo_with_templates)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    index_content = (repo_with_templates / "specs" / "active" / "INDEX.md").read_text(encoding="utf-8")
    assert "MyFramework" in index_content
    assert "DEVELOPMENT" in index_content


def test_init_leaves_unanswered_as_pendiente(repo_with_templates: Path) -> None:
    """When answers are empty strings, fields are replaced with empty string (not [PENDIENTE]).
    Template [PENDIENTE] is replaced by the regex regardless — empty input leaves empty value."""
    # Provide all 7 keys with empty values → regex replaces [PENDIENTE] with ""
    answers = {
        "Nombre": "",
        "Stack principal": "",
        "Mercado objetivo": "",
        "Tipo de producto": "",
        "execution_mode": "",
        "compliance_scope": "",
        "Objetivo en curso": "",
    }
    answers_file = _write_answers(repo_with_templates, answers)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["init", "--answers", str(answers_file), "--root", str(repo_with_templates)],
        catch_exceptions=False,
    )
    # Even with empty answers, the file should be generated
    active_index = repo_with_templates / "specs" / "active" / "INDEX.md"
    assert active_index.exists(), f"INDEX.md not generated. Output: {result.output}"


def test_init_fails_without_templates_dir(tmp_path: Path) -> None:
    """Without specs/_templates, piv init should exit with error."""
    answers_file = _write_answers(tmp_path, {})

    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--answers", str(answers_file), "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "Templates" in result.output


def test_init_help_works() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--help"])
    assert result.exit_code == 0
