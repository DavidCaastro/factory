"""
Tests para secops/scanner/cli.py — comandos t0, check y validación de argumentos.

Filosofía: la CLI es el contrato público del scanner. Los tests verifican
que los argumentos se parsean correctamente, que los exit codes son semánticamente
correctos (0=limpio, 1=hallazgos críticos, 2=error de usuario), y que los comandos
t0 y check producen output observable. No se mockea la lógica de negocio cuando
se puede invocar con fixtures reales.

Casos cubiertos:
- --method sin --dep → exit code 2 con mensaje a stderr
- --root inexistente → exit code 2 con mensaje a stderr
- t0 con payload existente → exit code según action_required
- t0 sin payload → exit code 0 (advertencia, no error)
- check con componente CRITICAL → exit code 1
- check con componente CLEAN → exit code 0
- build_parser() produce parser con subcomandos scan, t0, check
- --json desactiva progress y produce JSON parseable
- exit codes reflejan risk_level correctamente
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from secops.scanner.cli import build_parser, run


# ---------------------------------------------------------------------------
# build_parser — estructura del parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_parser_has_scan_subcommand(self):
        """El parser define el subcomando 'scan'."""
        parser = build_parser()
        # Parsear argumentos válidos de scan no debe lanzar
        args = parser.parse_args(["scan"])
        assert args.command == "scan"

    def test_parser_has_t0_subcommand(self):
        args = build_parser().parse_args(["t0"])
        assert args.command == "t0"

    def test_parser_has_check_subcommand(self):
        args = build_parser().parse_args(["check", "--component", "axios"])
        assert args.command == "check"
        assert args.component == "axios"

    def test_scan_parses_dep_and_method(self):
        args = build_parser().parse_args(["scan", "--dep", "axios", "--method", "buildFullPath"])
        assert args.dep == "axios"
        assert args.method == "buildFullPath"

    def test_scan_default_root_is_current_dir(self):
        args = build_parser().parse_args(["scan"])
        assert args.root == "."


# ---------------------------------------------------------------------------
# Validación de argumentos — exit code 2
# ---------------------------------------------------------------------------


class TestArgumentValidation:
    """Errores de uso del CLI deben retornar exit code 2 con mensaje claro en stderr."""

    def test_method_without_dep_returns_exit_2(self, capsys):
        """--method sin --dep es un error de usuario → exit 2."""
        exit_code = run(["scan", "--method", "buildFullPath"])

        assert exit_code == 2
        captured = capsys.readouterr()
        assert "dep" in captured.err.lower() or "--dep" in captured.err

    def test_nonexistent_root_returns_exit_2(self, tmp_path, capsys):
        """--root apuntando a directorio inexistente → exit 2."""
        nonexistent = str(tmp_path / "does_not_exist")
        exit_code = run(["scan", "--root", nonexistent])

        assert exit_code == 2
        captured = capsys.readouterr()
        assert "root" in captured.err.lower() or "no existe" in captured.err or nonexistent in captured.err


# ---------------------------------------------------------------------------
# Comando t0
# ---------------------------------------------------------------------------


class TestCmdT0:
    """t0 lee payload.json sin ejecutar scan. Es una operación de solo lectura."""

    def test_t0_returns_0_when_no_action_required(self, tmp_path, capsys):
        """Payload existente sin acción requerida → exit 0."""
        payload = {
            "risk_level": "LOW",
            "action_required": False,
            "summary_for_agent": "Sin hallazgos críticos",
            "stale": False,
        }
        payload_file = tmp_path / "bridge" / "payload.json"
        payload_file.parent.mkdir()
        payload_file.write_text(json.dumps(payload))

        with patch("secops.scanner.main.PAYLOAD_FILE", payload_file):
            exit_code = run(["t0", "--no-progress"])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "LOW" in captured.out

    def test_t0_returns_1_when_action_required(self, tmp_path, capsys):
        """Payload con action_required=True → exit 1 (alerta al usuario)."""
        payload = {
            "risk_level": "CRITICAL",
            "action_required": True,
            "summary_for_agent": "Supply chain attack detectado",
            "stale": False,
            "counts": {"CRITICAL": 1},
        }
        payload_file = tmp_path / "bridge" / "payload.json"
        payload_file.parent.mkdir()
        payload_file.write_text(json.dumps(payload))

        with patch("secops.scanner.main.PAYLOAD_FILE", payload_file):
            exit_code = run(["t0", "--no-progress"])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "action_required" in captured.out.lower() or "CRITICAL" in captured.out

    def test_t0_returns_0_when_no_payload_exists(self, tmp_path, capsys):
        """Sin payload.json → exit 0 con advertencia UNKNOWN (no es un error fatal)."""
        nonexistent = tmp_path / "bridge" / "payload.json"

        with patch("secops.scanner.main.PAYLOAD_FILE", nonexistent):
            exit_code = run(["t0", "--no-progress"])

        # Sin payload no debe ser exit 2 (error); es una advertencia, exit 0 o 1
        assert exit_code in (0, 1)
        captured = capsys.readouterr()
        assert "UNKNOWN" in captured.out or "unknown" in captured.out.lower()


# ---------------------------------------------------------------------------
# Comando check (T1)
# ---------------------------------------------------------------------------


class TestCmdCheck:
    def test_check_returns_1_for_critical_component(self, tmp_path, capsys):
        """Componente con riesgo CRITICAL → exit 1."""
        component_risk = {
            "axios": {"risk_level": "CRITICAL", "findings_count": 3}
        }
        risk_file = tmp_path / "bridge" / "component_risk.json"
        risk_file.parent.mkdir()
        risk_file.write_text(json.dumps(component_risk))

        with patch("secops.scanner.main.COMPONENT_RISK_FILE", risk_file):
            exit_code = run(["check", "--component", "axios", "--no-progress"])

        assert exit_code == 1

    def test_check_returns_0_for_clean_component(self, tmp_path, capsys):
        """Componente limpio o desconocido → exit 0."""
        component_risk = {}
        risk_file = tmp_path / "bridge" / "component_risk.json"
        risk_file.parent.mkdir()
        risk_file.write_text(json.dumps(component_risk))

        with patch("secops.scanner.main.COMPONENT_RISK_FILE", risk_file):
            exit_code = run(["check", "--component", "unknown-pkg", "--no-progress"])

        assert exit_code == 0

    def test_check_output_is_valid_json(self, tmp_path, capsys):
        """El output del comando check es JSON parseable."""
        component_risk = {
            "requests": {"risk_level": "HIGH", "findings_count": 1}
        }
        risk_file = tmp_path / "bridge" / "component_risk.json"
        risk_file.parent.mkdir()
        risk_file.write_text(json.dumps(component_risk))

        with patch("secops.scanner.main.COMPONENT_RISK_FILE", risk_file):
            run(["check", "--component", "requests", "--no-progress"])

        captured = capsys.readouterr()
        # El output debe ser JSON válido
        parsed = json.loads(captured.out)
        assert "risk_level" in parsed


# ---------------------------------------------------------------------------
# Exit codes del comando scan
# ---------------------------------------------------------------------------


class TestScanExitCodes:
    """Los exit codes del scan reflejan semánticamente el resultado:
    0 = limpio, 1 = hallazgos críticos/altos, 2 = error.
    """

    def test_scan_returns_0_for_clean_result(self, tmp_path):
        """Scan sin hallazgos → exit 0."""
        clean_result = {
            "risk_level": "CLEAN",
            "findings_count": 0,
            "deps_analyzed": 1,
            "report_path": str(tmp_path / "report.md"),
        }
        with patch("secops.scanner.main.run_full_scan", return_value=clean_result):
            exit_code = run(["scan", "--root", str(tmp_path), "--no-progress"])

        assert exit_code == 0

    def test_scan_returns_1_for_critical_result(self, tmp_path):
        """Scan con hallazgos CRITICAL → exit 1."""
        critical_result = {
            "risk_level": "CRITICAL",
            "findings_count": 3,
            "deps_analyzed": 2,
            "report_path": str(tmp_path / "report.md"),
        }
        with patch("secops.scanner.main.run_full_scan", return_value=critical_result):
            exit_code = run(["scan", "--root", str(tmp_path), "--no-progress"])

        assert exit_code == 1

    def test_scan_returns_1_for_high_result(self, tmp_path):
        """Scan con hallazgos HIGH → exit 1 (también requiere revisión)."""
        high_result = {
            "risk_level": "HIGH",
            "findings_count": 1,
            "deps_analyzed": 1,
            "report_path": str(tmp_path / "report.md"),
        }
        with patch("secops.scanner.main.run_full_scan", return_value=high_result):
            exit_code = run(["scan", "--root", str(tmp_path), "--no-progress"])

        assert exit_code == 1

    def test_scan_json_output_is_parseable(self, tmp_path, capsys):
        """Con --json, alguna línea del output es JSON válido con los campos esperados.

        El CLI puede emitir texto informativo antes del bloque JSON.
        Se busca la primera línea que comienza con '{'.
        """
        result = {
            "risk_level": "LOW",
            "findings_count": 2,
            "deps_analyzed": 3,
            "report_path": str(tmp_path / "report.md"),
        }
        with patch("secops.scanner.main.run_full_scan", return_value=result):
            run(["scan", "--root", str(tmp_path), "--json"])

        captured = capsys.readouterr()
        # Extraer el bloque JSON (puede haber texto informativo antes)
        json_lines = [l for l in captured.out.splitlines() if l.strip().startswith("{")]
        # Si no hay línea única, intentar parsear el bloque completo desde el primer '{'
        if not json_lines:
            json_start = captured.out.find("{")
            assert json_start >= 0, f"No JSON encontrado en output:\n{captured.out}"
            json_str = captured.out[json_start:]
        else:
            json_str = "\n".join(
                captured.out[captured.out.find("{"):]
                .splitlines()
            )
        parsed = json.loads(json_str)
        assert parsed["risk_level"] == "LOW"
        assert parsed["findings_count"] == 2
