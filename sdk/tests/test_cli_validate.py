"""
Tests for `piv validate` CLI command.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from piv_oac.cli.main import cli


@pytest.fixture()
def valid_specs(tmp_path: Path) -> Path:
    """Create a minimal valid specs/active/INDEX.md in tmp_path."""
    (tmp_path / "specs" / "active").mkdir(parents=True)
    index = tmp_path / "specs" / "active" / "INDEX.md"
    index.write_text(
        "# SPECS\n\n"
        "## Identidad del Proyecto\n\n"
        "| Atributo | Valor |\n"
        "|---|---|\n"
        "| Nombre | TestProject |\n"
        "| Stack principal | Python |\n"
        "| execution_mode | DEVELOPMENT |\n"
        "| compliance_scope | MINIMAL |\n"
        "| Objetivo en curso | OBJ-001 |\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def invalid_specs(tmp_path: Path) -> Path:
    """Create specs/active/INDEX.md with [PENDIENTE] in a required field."""
    (tmp_path / "specs" / "active").mkdir(parents=True)
    index = tmp_path / "specs" / "active" / "INDEX.md"
    index.write_text(
        "# SPECS\n\n"
        "## Identidad del Proyecto\n\n"
        "| Atributo | Valor |\n"
        "|---|---|\n"
        "| Nombre | [PENDIENTE] |\n"
        "| Stack principal | Python |\n"
        "| execution_mode | DEVELOPMENT |\n"
        "| compliance_scope | MINIMAL |\n"
        "| Objetivo en curso | OBJ-001 |\n",
        encoding="utf-8",
    )
    return tmp_path


def test_validate_passes_with_valid_specs(valid_specs: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(valid_specs), "--no-cross-refs"])
    assert result.exit_code == 0, result.output
    assert "PASS" in result.output


def test_validate_fails_with_pendiente_field(invalid_specs: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(invalid_specs), "--no-cross-refs"])
    assert result.exit_code == 1
    assert "FAIL" in result.output
    assert "Nombre" in result.output


def test_validate_fails_when_index_missing(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(tmp_path), "--no-cross-refs"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_validate_invalid_execution_mode(tmp_path: Path) -> None:
    (tmp_path / "specs" / "active").mkdir(parents=True)
    index = tmp_path / "specs" / "active" / "INDEX.md"
    index.write_text(
        "| Nombre | TestProject |\n"
        "| Stack principal | Python |\n"
        "| execution_mode | INVALID_MODE |\n"
        "| compliance_scope | MINIMAL |\n"
        "| Objetivo en curso | OBJ-001 |\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(tmp_path), "--no-cross-refs"])
    assert result.exit_code == 1
    assert "execution_mode" in result.output


def test_validate_invalid_compliance_scope(tmp_path: Path) -> None:
    (tmp_path / "specs" / "active").mkdir(parents=True)
    index = tmp_path / "specs" / "active" / "INDEX.md"
    index.write_text(
        "| Nombre | TestProject |\n"
        "| Stack principal | Python |\n"
        "| execution_mode | DEVELOPMENT |\n"
        "| compliance_scope | BADVALUE |\n"
        "| Objetivo en curso | OBJ-001 |\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(tmp_path), "--no-cross-refs"])
    assert result.exit_code == 1
    assert "compliance_scope" in result.output


def test_validate_help_works() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--help"])
    assert result.exit_code == 0
    assert "PATH" in result.output
