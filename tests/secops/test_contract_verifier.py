"""
Tests RF-05: contract_verifier.py
Casos de referencia obligatorios:
  - CVE-2025-27152: allowAbsoluteUrls no enforceada en XHR/Fetch adapters
  - CVE-2025-58754: maxContentLength ignorada en path data: URI
"""
from pathlib import Path
import pytest
from secops.scanner.ast_engine import parse_file
from secops.scanner.contract_verifier import analyze

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
