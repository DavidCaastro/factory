"""
Tests para secops/scanner/impact.py

Filosofía: impact.py es evidencia para responsible disclosure.
Cada test verifica que el registro es fiel, deduplicado, y que
la lógica de reachability produce conclusiones correctas con inputs reales.

Casos cubiertos:
- Append-only: nuevos hallazgos se escriben, entradas previas nunca se modifican
- Deduplicación: el mismo hallazgo no se escribe dos veces
- JSONL corrupto: líneas inválidas no impiden lectura del resto
- _check_reachability: detecta correctamente imports en el proyecto
- _check_reachability: project_root inexistente retorna None sin error
- _suggest_action: behavioral anomaly crítico → acción urgente
- _suggest_action: hallazgo no alcanzable → monitor
- Archivo no existente: se crea correctamente
"""

import json
import pathlib
from pathlib import Path

import pytest

from secops.scanner.impact import (
    _check_reachability,
    _entry_key,
    _load_existing_keys,
    _suggest_action,
    write_impact,
)
from secops.scanner.taint_analyzer import Finding


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finding(
    finding_type="TAINT_FLOW",
    severity="HIGH",
    dep_name="axios",
    dep_version="1.7.9",
    file_path="node_modules/axios/lib/adapters/xhr.js",
    line=42,
    title="axios → network sink sin validación",
    motor="taint_analyzer",
) -> Finding:
    return Finding(
        finding_type=finding_type,
        severity=severity,
        dep_name=dep_name,
        dep_version=dep_version,
        file_path=file_path,
        line=line,
        title=title,
        description="Flujo taint detectado",
        evidence="config.url → open(config.url)",
        motor=motor,
    )


# ---------------------------------------------------------------------------
# Append-only e integridad del archivo
# ---------------------------------------------------------------------------


class TestAppendOnly:
    """El archivo JSONL es evidencia permanente. Nunca se modifica lo escrito."""

    def test_creates_file_on_first_write(self, tmp_path):
        """Archivo no existente → se crea con la entrada nueva."""
        impact_file = tmp_path / "records" / "impact_analysis.jsonl"
        findings = [_finding()]

        written = write_impact(findings, tmp_path, impact_file)

        assert impact_file.exists()
        assert written == 1
        lines = impact_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["dep"] == "axios"
        assert entry["finding_type"] == "TAINT_FLOW"

    def test_appends_new_findings_without_overwriting(self, tmp_path):
        """Segunda escritura agrega entradas, no sobreescribe las anteriores."""
        impact_file = tmp_path / "impact_analysis.jsonl"
        f1 = _finding(dep_name="axios", dep_version="1.7.9", line=10)
        f2 = _finding(dep_name="requests", dep_version="2.28.0", line=20,
                      file_path="requests/adapters.py", finding_type="CONTRACT_VIOLATION",
                      motor="contract_verifier")

        write_impact([f1], tmp_path, impact_file)
        first_content = impact_file.read_text(encoding="utf-8")

        write_impact([f2], tmp_path, impact_file)
        second_content = impact_file.read_text(encoding="utf-8")

        # El contenido original sigue igual al inicio
        assert second_content.startswith(first_content)
        lines = second_content.splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["dep"] == "axios"
        assert json.loads(lines[1])["dep"] == "requests"

    def test_all_required_fields_present(self, tmp_path):
        """Cada entrada contiene todos los campos del schema de RF-08."""
        impact_file = tmp_path / "impact_analysis.jsonl"
        write_impact([_finding()], tmp_path, impact_file)

        entry = json.loads(impact_file.read_text(encoding="utf-8").splitlines()[0])
        required_fields = {"date", "dep", "version", "finding_type", "severity",
                           "motor", "file", "line", "title", "reachable",
                           "call_path", "evidence", "action"}
        assert required_fields.issubset(set(entry.keys()))


# ---------------------------------------------------------------------------
# Deduplicación
# ---------------------------------------------------------------------------


class TestDeduplication:
    """El mismo hallazgo no debe aparecer dos veces en el JSONL."""

    def test_duplicate_finding_not_written_twice(self, tmp_path):
        """El mismo hallazgo enviado dos veces → solo una entrada en el archivo."""
        impact_file = tmp_path / "impact_analysis.jsonl"
        finding = _finding()

        write_impact([finding], tmp_path, impact_file)
        write_impact([finding], tmp_path, impact_file)

        lines = impact_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1

    def test_different_line_is_not_duplicate(self, tmp_path):
        """Mismo dep/version/type pero distinto line → dos entradas distintas."""
        impact_file = tmp_path / "impact_analysis.jsonl"
        f1 = _finding(line=10)
        f2 = _finding(line=99)

        write_impact([f1, f2], tmp_path, impact_file)

        lines = impact_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2

    def test_load_existing_keys_handles_corrupt_jsonl(self, tmp_path):
        """Línea JSON inválida no impide leer el resto del archivo."""
        impact_file = tmp_path / "impact_analysis.jsonl"
        valid_entry = json.dumps({
            "dep": "axios", "version": "1.7.9",
            "finding_type": "TAINT_FLOW", "file": "xhr.js", "line": 10
        })
        impact_file.write_text(
            valid_entry + "\n"
            + "{ corrupt json without closing\n"
            + valid_entry + "\n",
            encoding="utf-8"
        )

        keys = _load_existing_keys(impact_file)

        # La línea corrupta se ignora, las válidas se cargan
        assert len(keys) == 1  # las dos válidas son idénticas → 1 key única

    def test_load_existing_keys_on_empty_file(self, tmp_path):
        """Archivo vacío → set vacío sin error."""
        impact_file = tmp_path / "impact_analysis.jsonl"
        impact_file.write_text("", encoding="utf-8")

        keys = _load_existing_keys(impact_file)

        assert keys == set()

    def test_load_existing_keys_on_nonexistent_file(self, tmp_path):
        """Archivo no existente → set vacío sin error."""
        impact_file = tmp_path / "nonexistent.jsonl"

        keys = _load_existing_keys(impact_file)

        assert keys == set()


# ---------------------------------------------------------------------------
# Reachability
# ---------------------------------------------------------------------------


class TestReachability:
    """_check_reachability busca en el código del proyecto si la dependencia
    es importada. Un hallazgo no alcanzable cambia la acción recomendada.
    """

    def test_detects_python_import_in_project(self, tmp_path):
        """Dependencia importada en un .py del proyecto → reachable=True."""
        # Crear un archivo Python que importa la dependencia
        src = tmp_path / "src" / "app.py"
        src.parent.mkdir()
        src.write_text("import requests\nrequests.get('http://example.com')\n")

        finding = _finding(dep_name="requests")
        reachable, call_path = _check_reachability(finding, tmp_path)

        assert reachable is True
        assert "app.py" in call_path

    def test_not_reachable_when_dep_not_imported(self, tmp_path):
        """Dependencia no importada en el proyecto → reachable=False."""
        src = tmp_path / "src" / "app.py"
        src.parent.mkdir()
        src.write_text("import os\nprint('hello')\n")

        finding = _finding(dep_name="axios")
        reachable, call_path = _check_reachability(finding, tmp_path)

        assert reachable is False
        assert "no importada" in call_path.lower() or "axios" in call_path

    def test_project_root_not_exists_returns_none(self, tmp_path):
        """project_root inexistente → reachable=None (no determinado), sin excepción."""
        nonexistent = tmp_path / "does_not_exist"
        finding = _finding()

        reachable, call_path = _check_reachability(finding, nonexistent)

        assert reachable is None
        assert "project_root" in call_path.lower() or "no disponible" in call_path.lower()

    def test_secops_dir_excluded_from_reachability(self, tmp_path):
        """Imports dentro de secops/ no cuentan como reachable (módulo analiza a sí mismo)."""
        secops_file = tmp_path / "secops" / "scanner" / "main.py"
        secops_file.parent.mkdir(parents=True)
        secops_file.write_text("import axios_compat\n")

        finding = _finding(dep_name="axios_compat")
        reachable, _ = _check_reachability(finding, tmp_path)

        # secops/ está excluido, así que no debe detectar el import
        assert reachable is False


# ---------------------------------------------------------------------------
# Suggest action
# ---------------------------------------------------------------------------


class TestSuggestAction:
    """La acción sugerida debe ser determinista y correcta para cada combinación
    de tipo de hallazgo, severidad y reachability.
    """

    def test_behavioral_anomaly_critical_reachable_is_urgent(self):
        """Supply chain attack crítico y alcanzable → acción urgente."""
        f = _finding(finding_type="BEHAVIORAL_ANOMALY", severity="CRITICAL", motor="behavioral_delta")
        action = _suggest_action(f, reachable=True)
        assert "URGENT" in action or "urgent" in action.lower()

    def test_not_reachable_finding_suggests_monitor(self):
        """Hallazgo presente pero dependencia no usada → monitor."""
        f = _finding(severity="HIGH")
        action = _suggest_action(f, reachable=False)
        assert "monitor" in action.lower()

    def test_reachable_critical_suggests_upgrade(self):
        """Hallazgo CRITICAL alcanzable → upgrade requerido."""
        f = _finding(severity="CRITICAL")
        action = _suggest_action(f, reachable=True)
        assert "upgrade" in action.lower() or "URGENT" in action

    def test_unknown_reachability_suggests_investigate(self):
        """No se pudo determinar reachability → investigate."""
        f = _finding(severity="HIGH")
        action = _suggest_action(f, reachable=None)
        assert "investigate" in action.lower()

    def test_info_severity_always_monitor(self):
        """Hallazgos INFO son solo informativos independientemente de reachability."""
        f = _finding(severity="INFO")
        action = _suggest_action(f, reachable=True)
        assert "monitor" in action.lower()



class TestReachabilityOSError:
    """_check_reachability maneja OSError silenciosamente en bucles de archivos."""

    def test_oserror_on_python_file_is_skipped(self, tmp_path):
        """OSError al leer un .py -> se ignora y continua (lines 82-83)."""
        from unittest.mock import patch

        src_ok = tmp_path / "ok.py"
        src_ok.write_text("import mylib" + chr(10))
        src_bad = tmp_path / "bad.py"
        src_bad.write_text("import mylib" + chr(10))

        original_read_text = pathlib.Path.read_text

        def selective_fail(self_path, *args, **kwargs):
            if self_path.name == "bad.py":
                raise OSError("cannot read")
            return original_read_text(self_path, *args, **kwargs)

        finding = _finding(dep_name="mylib")
        with patch.object(pathlib.Path, "read_text", selective_fail):
            reachable, call_path = _check_reachability(finding, tmp_path)

        # ok.py se pudo leer -> reachable True
        assert reachable is True

    def test_oserror_on_js_file_is_skipped(self, tmp_path):
        """OSError al leer un .js -> se ignora y continua (lines 90-98)."""
        from unittest.mock import patch

        src_js = tmp_path / "app.js"
        # Use require with double quotes to ensure detection
        src_js.write_text('const m = require("jsonly");' + chr(10))

        original_read_text = pathlib.Path.read_text

        def selective_fail(self_path, *args, **kwargs):
            if self_path.suffix == ".js":
                raise OSError("cannot read js")
            return original_read_text(self_path, *args, **kwargs)

        finding = _finding(dep_name="jsonly")
        with patch.object(pathlib.Path, "read_text", selective_fail):
            reachable, call_path = _check_reachability(finding, tmp_path)

        # JS not readable -> not reachable
        assert reachable is False



class TestCallPathTruncation:
    """Cuando hay 4+ archivos que importan la misma dep, call_path indica cuantos mas."""

    def test_call_path_shows_overflow_count(self, tmp_path):
        """4 archivos importan la misma dep -> call_path contiene '+N mas' (line 105)."""
        dep = "mypkg"
        for i in range(4):
            f = tmp_path / ("mod" + str(i) + ".py")
            f.write_text("import " + dep + chr(10))

        finding = _finding(dep_name=dep)
        reachable, call_path = _check_reachability(finding, tmp_path)

        assert reachable is True
        # Should mention overflow
        assert "+" in call_path



class TestSuggestActionReview:
    """_suggest_action retorna review para reachable=True con severidad no critica."""

    def test_reachable_medium_severity_returns_review(self):
        """reachable=True + severity=MEDIUM -> review (line 122)."""
        f = _finding(severity="MEDIUM")
        action = _suggest_action(f, reachable=True)
        assert action == "review"

    def test_reachable_low_severity_returns_review(self):
        """reachable=True + severity=LOW -> review (line 122)."""
        f = _finding(severity="LOW")
        action = _suggest_action(f, reachable=True)
        assert action == "review"



class TestLoadExistingKeysBlankLines:
    """_load_existing_keys ignora lineas en blanco en el JSONL (line 132)."""

    def test_blank_lines_in_jsonl_are_skipped(self, tmp_path):
        """Lineas vacias intercaladas en JSONL -> se saltan sin error."""
        impact_file = tmp_path / "impact.jsonl"
        entry = json.dumps({
            "dep": "pkg", "version": "1.0", "finding_type": "TAINT_FLOW",
            "file": "main.py", "line": 10
        })
        # Write with blank lines intercalated
        impact_file.write_text(
            entry + chr(10) + chr(10) + entry + chr(10) + chr(10),
            encoding="utf-8"
        )

        keys = _load_existing_keys(impact_file)

        # Two identical entries -> 1 unique key; blank lines ignored
        assert len(keys) == 1



class TestReachabilityJSDetection:
    """_check_reachability detecta imports en archivos .js del proyecto."""

    def test_detects_js_require_in_project(self, tmp_path):
        """JS file con require(dep) -> reachable=True (lines 96-98)."""
        src_js = tmp_path / "app.js"
        # Use single-quote require pattern
        src_js.write_text("const m = require" + chr(40) + chr(39) + "jslib" + chr(39) + chr(41) + ";" + chr(10))

        finding = _finding(dep_name="jslib")
        reachable, call_path = _check_reachability(finding, tmp_path)

        assert reachable is True
        assert "app.js" in call_path

    def test_secops_js_file_excluded(self, tmp_path):
        """JS files dentro de secops/ se excluyen del scan (line 91)."""
        secops_dir = tmp_path / "secops" / "scanner"
        secops_dir.mkdir(parents=True)
        js_file = secops_dir / "main.js"
        js_file.write_text("const m = require" + chr(40) + chr(39) + "excluded_pkg" + chr(39) + chr(41) + ";" + chr(10))

        finding = _finding(dep_name="excluded_pkg")
        reachable, _ = _check_reachability(finding, tmp_path)

        # secops/ is excluded
        assert reachable is False
