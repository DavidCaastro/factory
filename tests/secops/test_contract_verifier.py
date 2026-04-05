"""
Tests RF-05: contract_verifier.py
Casos de referencia obligatorios:
  - CVE-2025-27152: allowAbsoluteUrls no enforceada en XHR/Fetch adapters
  - CVE-2025-58754: maxContentLength ignorada en path data: URI
"""
from pathlib import Path
import pytest
from secops.scanner.ast_engine import ASTNode, ParseResult, parse_file
from secops.scanner.contract_verifier import (
    analyze,
    _get_guarded_ops,
    _infer_severity_contract,
    GUARDED_OPERATIONS,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# HTTP adapter SÍ verifica allowAbsoluteUrls
HTTP_ADAPTER_CHECKS = """\
// lib/adapters/http.js — verifica allowAbsoluteUrls
function httpAdapter(config) {
  var fullPath = buildFullPath(config.baseURL, config.url, config.allowAbsoluteUrls);
  return request(fullPath);
}
"""

# XHR adapter NO verifica allowAbsoluteUrls (vulnerable)
XHR_ADAPTER_NO_CHECK = """\
// lib/adapters/xhr.js — NO verifica allowAbsoluteUrls
function xhrAdapter(config) {
  var url = config.url;
  var fullPath = buildFullPath(config.baseURL, url);
  request.open(config.method, fullPath, true);
}
"""

# Fetch adapter NO verifica allowAbsoluteUrls (vulnerable)
FETCH_ADAPTER_NO_CHECK = """\
// lib/adapters/fetch.js — NO verifica allowAbsoluteUrls
function fetchAdapter(config) {
  var url = buildFullPath(config.baseURL, config.url);
  return fetch(url);
}
"""

# fromDataURI vulnerable — ignora maxContentLength
FROM_DATA_URI_NO_LIMIT = """\
// lib/helpers/fromDataURI.js — ignora maxContentLength/maxBodyLength
function fromDataURI(uri, asBlob, options) {
  var body = uri.split(',')[1];
  var buffer = Buffer.from(decodeURIComponent(body), 'base64');
  return buffer;
}
"""

# fromDataURI corregido — verifica maxContentLength
FROM_DATA_URI_WITH_LIMIT = """\
// lib/helpers/fromDataURI.js — verifica maxContentLength
function fromDataURI(uri, asBlob, options) {
  var body = uri.split(',')[1];
  if (options.maxContentLength && body.length > options.maxContentLength) {
    throw new Error('Content too large');
  }
  var buffer = Buffer.from(decodeURIComponent(body), 'base64');
  return buffer;
}
"""


def _parse(tmp_path: Path, filename: str, content: str):
    f = tmp_path / filename
    f.write_text(content)
    return parse_file(f, "javascript")


# ---------------------------------------------------------------------------
# Tests CVE-2025-27152 (RF-05 criterio de aceptación obligatorio)
# ---------------------------------------------------------------------------

class TestCVE202527152ContractViolation:
    """allowAbsoluteUrls declarada en http.js pero no enforceada en xhr.js y fetch.js."""

    def test_xhr_adapter_violates_allowAbsoluteUrls_contract(self, tmp_path):
        """RF-05: axios ≤1.7.9 — xhr adapter debe generar CONTRACT_VIOLATION."""
        http_result = _parse(tmp_path, "http.js", HTTP_ADAPTER_CHECKS)
        xhr_result = _parse(tmp_path, "xhr.js", XHR_ADAPTER_NO_CHECK)
        findings = analyze([http_result, xhr_result], "axios", "1.7.9")
        violations = [f for f in findings if f.finding_type == "CONTRACT_VIOLATION"]
        xhr_violations = [v for v in violations if "xhr" in v.file_path.lower()]
        assert len(xhr_violations) >= 1, (
            "CVE-2025-27152 no detectada (Contract): se esperaba CONTRACT_VIOLATION en xhr.js. "
            f"Hallazgos: {[f.title for f in findings]}"
        )

    def test_fetch_adapter_violates_allowAbsoluteUrls_contract(self, tmp_path):
        """RF-05: axios ≤1.7.9 — fetch adapter debe generar CONTRACT_VIOLATION."""
        http_result = _parse(tmp_path, "http.js", HTTP_ADAPTER_CHECKS)
        fetch_result = _parse(tmp_path, "fetch.js", FETCH_ADAPTER_NO_CHECK)
        findings = analyze([http_result, fetch_result], "axios", "1.7.9")
        violations = [f for f in findings if f.finding_type == "CONTRACT_VIOLATION"]
        fetch_violations = [v for v in violations if "fetch" in v.file_path.lower()]
        assert len(fetch_violations) >= 1, (
            "CVE-2025-27152 no detectada (Contract): se esperaba CONTRACT_VIOLATION en fetch.js. "
            f"Hallazgos: {[f.title for f in findings]}"
        )

    def test_violations_are_high_severity(self, tmp_path):
        http_result = _parse(tmp_path, "http.js", HTTP_ADAPTER_CHECKS)
        xhr_result = _parse(tmp_path, "xhr.js", XHR_ADAPTER_NO_CHECK)
        findings = analyze([http_result, xhr_result], "axios", "1.7.9")
        violations = [f for f in findings if f.finding_type == "CONTRACT_VIOLATION"]
        if violations:
            severities = {v.severity for v in violations}
            assert severities & {"CRITICAL", "HIGH"}


# ---------------------------------------------------------------------------
# Tests CVE-2025-58754 (RF-05 criterio de aceptación obligatorio)
# ---------------------------------------------------------------------------

class TestCVE202558754ContractViolation:
    """maxContentLength/maxBodyLength ignoradas en path data: URI."""

    def test_vulnerable_fromDataURI_violates_maxContentLength(self, tmp_path):
        """RF-05: axios ≤1.13.x — fromDataURI ignora maxContentLength → CONTRACT_VIOLATION."""
        result = _parse(tmp_path, "fromDataURI.js", FROM_DATA_URI_NO_LIMIT)
        findings = analyze([result], "axios", "1.13.0")
        violations = [f for f in findings if f.finding_type == "CONTRACT_VIOLATION"]
        assert len(violations) >= 1, (
            "CVE-2025-58754 no detectada: se esperaba CONTRACT_VIOLATION en fromDataURI.js. "
            f"Hallazgos: {[f.title for f in findings]}"
        )

    def test_fixed_fromDataURI_no_violation(self, tmp_path):
        """RF-05: axios corregido — fromDataURI con check no debe generar violación en ese archivo."""
        result = _parse(tmp_path, "fromDataURI.js", FROM_DATA_URI_WITH_LIMIT)
        findings = analyze([result], "axios", "1.12.0")
        violations = [
            f for f in findings
            if f.finding_type == "CONTRACT_VIOLATION" and "fromDataURI" in f.file_path
        ]
        assert len(violations) == 0, (
            f"axios corregido no debería tener CONTRACT_VIOLATION en fromDataURI. "
            f"Encontrados: {[f.title for f in violations]}"
        )


# ---------------------------------------------------------------------------
# Tests de principios
# ---------------------------------------------------------------------------

class TestContractPrinciples:
    def test_motor_field_is_contract_verifier(self, tmp_path):
        result = _parse(tmp_path, "test.js", XHR_ADAPTER_NO_CHECK)
        http = _parse(tmp_path, "http.js", HTTP_ADAPTER_CHECKS)
        findings = analyze([http, result], "dep", "1.0")
        for f in findings:
            assert f.motor == "contract_verifier"

    def test_no_third_party_tools_used(self):
        """RF-14: sin dependencias de terceros en contract_verifier."""
        import secops.scanner.contract_verifier as mod
        import inspect
        source = inspect.getsource(mod)
        for forbidden in ["import bandit", "import semgrep", "import safety"]:
            assert forbidden not in source


# ---------------------------------------------------------------------------
# Tests de edge cases: parse_error paths (líneas 97, 127, 152, 216)
# y early-continue paths (líneas 227, 239)
# ---------------------------------------------------------------------------

class TestContractEdgeCases:
    """Cubre paths de parse_error y early-continue en todas las funciones internas."""

    def _error_result(self, path: str) -> ParseResult:
        """Crea un ParseResult que simula un archivo que falló al parsear."""
        return ParseResult(
            file_path=path,
            language="javascript",
            nodes=[],
            parse_error="SyntaxError: unexpected token",
        )

    def test_detect_config_options_skips_parse_error(self):
        """Línea 97: _detect_config_options salta resultados con parse_error."""
        error_result = self._error_result("/lib/config.js")
        findings = analyze([error_result], "dep", "1.0")
        assert isinstance(findings, list)
        assert not any("config.js" in f.file_path for f in findings)

    def test_map_checks_skips_parse_error(self, tmp_path):
        """Línea 127: _map_checks salta resultados con parse_error sin lanzar excepción."""
        http_result = _parse(tmp_path, "http.js", HTTP_ADAPTER_CHECKS)
        error_result = self._error_result("/lib/xhr_broken.js")
        # analyze llama _map_checks internamente; el resultado con error no debe fallar
        findings = analyze([http_result, error_result], "axios", "1.7.9")
        assert not any("xhr_broken" in f.file_path for f in findings)

    def test_check_coverage_skips_parse_error(self, tmp_path):
        """Línea 152: _check_coverage salta resultados con parse_error."""
        http_result = _parse(tmp_path, "http.js", HTTP_ADAPTER_CHECKS)
        error_result = self._error_result("/lib/broken_adapter.js")
        findings = analyze([http_result, error_result], "axios", "1.7.9")
        assert not any("broken_adapter" in f.file_path for f in findings)

    def test_detect_options_param_violations_skips_parse_error(self):
        """Línea 216: _detect_options_param_violations salta resultados con parse_error."""
        error_result = self._error_result("/lib/broken_helper.js")
        findings = analyze([error_result], "dep", "1.0")
        assert isinstance(findings, list)
        assert not any("broken_helper" in f.file_path for f in findings)

    def test_analyze_all_parse_errors_returns_empty(self):
        """Cuando todos los inputs tienen parse_error, analyze devuelve lista vacía."""
        errors = [
            self._error_result("/lib/a.js"),
            self._error_result("/lib/b.js"),
            self._error_result("/lib/c.js"),
        ]
        findings = analyze(errors, "dep", "2.0")
        assert findings == []

    def test_no_options_param_skips_intra_analysis(self, tmp_path):
        """Línea 227: archivo sin parámetro options/config se salta en análisis intra-función.

        Una función que recibe solo 'data' (sin options/__param__) no debe
        generar CONTRACT_VIOLATION del análisis intra aunque use Buffer.alloc.
        """
        code_no_options_param = """\
// lib/utils.js — sin parámetro options
function processData(data) {
  var buf = Buffer.alloc(data.length);
  return buf;
}
"""
        result = _parse(tmp_path, "utils.js", code_no_options_param)
        findings = analyze([result], "dep", "1.0")
        intra_violations = [
            f for f in findings
            if f.finding_type == "CONTRACT_VIOLATION" and "utils" in f.file_path
        ]
        assert len(intra_violations) == 0

    def test_options_param_without_guarded_ops_skips_finding(self, tmp_path):
        """Línea 239: función con options/__param__ pero sin operaciones protegidas no genera finding."""
        # La función acepta options pero solo hace operaciones de string (sin red/alloc/exec)
        code_options_no_guarded = """\
// lib/formatter.js — options param pero sin operaciones protegidas
function formatData(data, options) {
  var result = data.toString();
  return result.trim();
}
"""
        result = _parse(tmp_path, "formatter.js", code_options_no_guarded)
        findings = analyze([result], "dep", "1.0")
        intra_violations = [
            f for f in findings
            if f.finding_type == "CONTRACT_VIOLATION" and "formatter" in f.file_path
        ]
        assert len(intra_violations) == 0

    def test_mixed_valid_and_error_results(self, tmp_path):
        """Flujo mixto: resultados válidos y con error coexisten sin excepción."""
        valid_result = _parse(tmp_path, "http.js", HTTP_ADAPTER_CHECKS)
        error_a = self._error_result("/lib/broken_a.js")
        error_b = self._error_result("/lib/broken_b.js")
        findings = analyze([error_a, valid_result, error_b], "axios", "1.7.9")
        assert isinstance(findings, list)
        assert not any(
            "broken_a" in f.file_path or "broken_b" in f.file_path
            for f in findings
        )


# ---------------------------------------------------------------------------
# Tests de _get_guarded_ops (líneas 285-291)
# ---------------------------------------------------------------------------

class TestGetGuardedOps:
    """Cubre la tabla completa de clasificación de operaciones por prefijo de restricción."""

    def test_allow_prefix_guards_network_and_execution(self):
        """Prefijo 'allow' protege operaciones de red y ejecución."""
        ops = _get_guarded_ops("allow")
        assert ops == GUARDED_OPERATIONS["network"] | GUARDED_OPERATIONS["execution"]

    def test_restrict_prefix_guards_network_and_execution(self):
        """Prefijo 'restrict' protege operaciones de red y ejecución."""
        ops = _get_guarded_ops("restrict")
        assert ops == GUARDED_OPERATIONS["network"] | GUARDED_OPERATIONS["execution"]

    def test_block_prefix_guards_network_and_execution(self):
        """Prefijo 'block' protege operaciones de red y ejecución."""
        ops = _get_guarded_ops("block")
        assert ops == GUARDED_OPERATIONS["network"] | GUARDED_OPERATIONS["execution"]

    def test_safe_prefix_guards_network_and_execution(self):
        """Prefijo 'safe' protege operaciones de red y ejecución."""
        ops = _get_guarded_ops("safe")
        assert ops == GUARDED_OPERATIONS["network"] | GUARDED_OPERATIONS["execution"]

    def test_max_prefix_guards_allocation_and_network(self):
        """Prefijo 'max' protege operaciones de allocación y red."""
        ops = _get_guarded_ops("max")
        assert ops == GUARDED_OPERATIONS["allocation"] | GUARDED_OPERATIONS["network"]

    def test_limit_prefix_guards_allocation_and_network(self):
        """Prefijo 'limit' protege operaciones de allocación y red."""
        ops = _get_guarded_ops("limit")
        assert ops == GUARDED_OPERATIONS["allocation"] | GUARDED_OPERATIONS["network"]

    def test_require_prefix_guards_network_and_execution(self):
        """Línea 289: prefijo 'require' protege red y ejecución."""
        ops = _get_guarded_ops("require")
        assert ops == GUARDED_OPERATIONS["network"] | GUARDED_OPERATIONS["execution"]

    def test_enforce_prefix_guards_network_and_execution(self):
        """Línea 289: prefijo 'enforce' protege red y ejecución."""
        ops = _get_guarded_ops("enforce")
        assert ops == GUARDED_OPERATIONS["network"] | GUARDED_OPERATIONS["execution"]

    def test_enable_prefix_guards_network_and_execution(self):
        """Línea 289: prefijo 'enable' protege red y ejecución."""
        ops = _get_guarded_ops("enable")
        assert ops == GUARDED_OPERATIONS["network"] | GUARDED_OPERATIONS["execution"]

    def test_disable_prefix_guards_network_and_execution(self):
        """Líneas 289-291: prefijo 'disable' protege red y ejecución."""
        ops = _get_guarded_ops("disable")
        assert ops == GUARDED_OPERATIONS["network"] | GUARDED_OPERATIONS["execution"]

    def test_require_includes_fetch_and_exec(self):
        """Invariante de contenido: require cubre fetch (red) y exec (ejecución)."""
        ops = _get_guarded_ops("require")
        assert "fetch" in ops
        assert "exec" in ops

    def test_enable_includes_eval_and_request(self):
        """Invariante de contenido: enable cubre eval (ejecución) y request (red)."""
        ops = _get_guarded_ops("enable")
        assert "eval" in ops
        assert "request" in ops

    def test_unknown_prefix_returns_empty_set(self):
        """Prefijo no registrado devuelve set vacío (no falla)."""
        ops = _get_guarded_ops("unknown_prefix")
        assert ops == set()

    def test_empty_string_prefix_returns_empty_set(self):
        """Prefijo vacío devuelve set vacío."""
        ops = _get_guarded_ops("")
        assert ops == set()


# ---------------------------------------------------------------------------
# Tests de _infer_severity_contract (líneas 296-310)
# ---------------------------------------------------------------------------

class TestSeverityInference:
    """Cubre la lógica completa de inferencia de severidad para CONTRACT_VIOLATION."""

    # -- Rama URL/red (líneas 300-301) --

    def test_url_in_option_name_is_high(self):
        """Opción con 'url' → HIGH por riesgo SSRF."""
        assert _infer_severity_contract("allowAbsoluteUrls", "fetch") == "HIGH"

    def test_absolute_in_option_name_is_high(self):
        """Opción con 'absolute' → HIGH."""
        assert _infer_severity_contract("allowAbsolute", "request") == "HIGH"

    def test_origin_in_option_name_is_high(self):
        """Opción con 'origin' → HIGH."""
        assert _infer_severity_contract("allowOrigin", "fetch") == "HIGH"

    def test_host_in_option_name_is_high(self):
        """Opción con 'host' → HIGH."""
        assert _infer_severity_contract("trustedHost", "request") == "HIGH"

    def test_domain_in_option_name_is_high(self):
        """Opción con 'domain' → HIGH."""
        assert _infer_severity_contract("allowDomain", "urlopen") == "HIGH"

    # -- Rama max/limit + buffer/alloc/decode (líneas 303-305) --

    def test_max_with_buffer_alloc_is_high(self):
        """Línea 304: opción 'max' + operación 'Buffer.alloc' → HIGH (DoS)."""
        assert _infer_severity_contract("maxContentLength", "Buffer.alloc") == "HIGH"

    def test_max_with_buffer_from_is_high(self):
        """Línea 304: opción 'max' + 'Buffer.from' → HIGH."""
        assert _infer_severity_contract("maxBodyLength", "Buffer.from") == "HIGH"

    def test_limit_with_decode_is_high(self):
        """Línea 304: opción 'limit' + 'decode' → HIGH."""
        assert _infer_severity_contract("limitSize", "decode") == "HIGH"

    def test_length_with_alloc_unsafe_is_high(self):
        """Línea 303-304: opción con 'length' + 'Buffer.allocUnsafe' → HIGH."""
        assert _infer_severity_contract("maxLength", "Buffer.allocUnsafe") == "HIGH"

    def test_size_with_alloc_is_high(self):
        """Línea 303-304: opción con 'size' + 'Buffer.alloc' → HIGH."""
        assert _infer_severity_contract("maxSize", "Buffer.alloc") == "HIGH"

    # -- Rama max/limit sin buffer/alloc/decode (línea 306) --

    def test_max_with_network_op_is_medium(self):
        """Línea 306: opción 'max' + operación de red (no buffer) → MEDIUM."""
        assert _infer_severity_contract("maxRetries", "request") == "MEDIUM"

    def test_limit_with_fetch_is_medium(self):
        """Línea 306: opción 'limit' + 'fetch' → MEDIUM."""
        assert _infer_severity_contract("limitConnections", "fetch") == "MEDIUM"

    # -- Rama exec/spawn/eval (líneas 308-309) --

    def test_exec_operation_is_high(self):
        """Línea 308: cualquier opción + operación 'exec' → HIGH."""
        assert _infer_severity_contract("enableExec", "exec") == "HIGH"

    def test_spawn_operation_is_high(self):
        """Línea 308: cualquier opción + operación 'spawn' → HIGH."""
        assert _infer_severity_contract("safeMode", "spawn") == "HIGH"

    def test_eval_operation_is_high(self):
        """Línea 308: cualquier opción + operación 'eval' → HIGH."""
        assert _infer_severity_contract("allowEval", "eval") == "HIGH"

    # -- Fallthrough MEDIUM (línea 310) --

    def test_generic_restriction_option_is_medium(self):
        """Línea 310: opción y operación sin keywords especiales → MEDIUM."""
        assert _infer_severity_contract("blockRedirects", "fetch") == "MEDIUM"

    def test_require_auth_without_special_keywords_is_medium(self):
        """Línea 310: opción 'requireAuth' + 'fetch' → MEDIUM (sin keywords URL ni exec)."""
        assert _infer_severity_contract("requireAuth", "fetch") == "MEDIUM"

    def test_enforce_policy_with_generic_op_is_medium(self):
        """Línea 310: opción 'enforcePolicy' + operación genérica → MEDIUM."""
        assert _infer_severity_contract("enforcePolicy", "axios") == "MEDIUM"
