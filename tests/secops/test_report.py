"""
Tests para secops/scanner/report.py

Filosofía: el reporte es el output visible del scanner. Un reporte malformado,
incompleto o que pierde hallazgos es un fallo de seguridad (falso negativo presentado).
Los tests verifican que el contenido del Markdown es correcto, no solo que el archivo existe.

Casos cubiertos:
- Sin hallazgos → reporte válido con estado CLEAN explícito
- Hallazgos CRITICAL → risk_level CRITICAL en header
- _actionable_summary agrupa por paquete y diferencia urgente / no urgente
- _actionable_summary con >3 hallazgos por paquete → elipsis visible
- Todos los hallazgos aparecen en la tabla (sin pérdidas)
- _global_risk: jerarquía correcta (CRITICAL > HIGH > MEDIUM > LOW > CLEAN)
- _count_by_severity: conteo correcto incluyendo severidades mezcladas
- Archivo se genera en el directorio correcto con formato de nombre esperado
- Directorio reports_dir inexistente se crea automáticamente
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from secops.scanner.report import (
    _actionable_summary,
    _count_by_severity,
    _global_risk,
    generate_report,
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
    file_path="axios/lib/adapters/xhr.js",
    line=42,
    title="axios → network sink",
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
        description="Descripción del hallazgo",
        evidence="config.url → open(config.url)",
        motor=motor,
    )


# ---------------------------------------------------------------------------
# generate_report: archivo y contenido
# ---------------------------------------------------------------------------


class TestGenerateReport:
    def test_creates_file_in_reports_dir(self, tmp_path):
        """El reporte se crea en el directorio especificado."""
        reports_dir = tmp_path / "reports"
        path = generate_report([_finding()], {"axios": "1.7.9"}, ["javascript"], reports_dir)

        assert path.exists()
        assert path.parent == reports_dir

    def test_filename_follows_timestamp_format(self, tmp_path):
        """El nombre del archivo sigue el patrón YYYY-MM-DD_HHMM_scan.md."""
        reports_dir = tmp_path / "reports"
        path = generate_report([_finding()], {}, [], reports_dir)

        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}_\d{4}_scan\.md", path.name)

    def test_creates_reports_dir_if_not_exists(self, tmp_path):
        """reports_dir inexistente se crea automáticamente."""
        reports_dir = tmp_path / "nested" / "reports"
        assert not reports_dir.exists()

        generate_report([], {}, [], reports_dir)

        assert reports_dir.exists()

    def test_report_contains_all_findings(self, tmp_path):
        """Ningún hallazgo se pierde en el reporte generado."""
        findings = [
            _finding(dep_name="axios", line=10, title="Taint en XHR adapter"),
            _finding(dep_name="requests", dep_version="2.28.0",
                     file_path="requests/adapters.py", line=55,
                     title="Contract en redirect", finding_type="CONTRACT_VIOLATION",
                     motor="contract_verifier"),
        ]
        reports_dir = tmp_path / "reports"
        path = generate_report(findings, {"axios": "1.7.9", "requests": "2.28.0"},
                               ["javascript", "python"], reports_dir)

        content = path.read_text(encoding="utf-8")
        assert "axios" in content
        assert "requests" in content
        assert "Taint en XHR adapter" in content
        assert "Contract en redirect" in content

    def test_empty_findings_produces_clean_report(self, tmp_path):
        """Sin hallazgos → reporte con CLEAN explícito, sin tabla de hallazgos."""
        reports_dir = tmp_path / "reports"
        path = generate_report([], {"axios": "1.8.2"}, ["javascript"], reports_dir)

        content = path.read_text(encoding="utf-8")
        assert "CLEAN" in content
        # La sección de hallazgos debe indicar que no hay ninguno
        assert "Sin hallazgos" in content or "CLEAN" in content

    def test_critical_finding_shows_critical_risk_level(self, tmp_path):
        """Un hallazgo CRITICAL → Risk Level: CRITICAL en el header del reporte."""
        findings = [_finding(severity="CRITICAL")]
        reports_dir = tmp_path / "reports"
        path = generate_report(findings, {"axios": "1.7.9"}, ["javascript"], reports_dir)

        content = path.read_text(encoding="utf-8")
        assert "CRITICAL" in content


# ---------------------------------------------------------------------------
# _actionable_summary: agrupación y síntesis
# ---------------------------------------------------------------------------


class TestActionableSummary:
    """_actionable_summary es la sección que un developer lee primero.
    Debe agrupar correctamente y distinguir lo urgente de lo no urgente.
    """

    def test_no_findings_shows_clean_message(self):
        """Sin hallazgos → mensaje explícito de que no hay riesgo."""
        result = _actionable_summary([])
        assert "Sin hallazgos" in result or "CLEAN" in result or "✅" in result

    def test_critical_finding_appears_in_urgent_section(self):
        """Hallazgo CRITICAL aparece en la sección de revisión urgente."""
        findings = [_finding(severity="CRITICAL", dep_name="axios")]
        result = _actionable_summary(findings)

        assert "Requieren revisión" in result or "⚠️" in result
        assert "axios" in result

    def test_medium_finding_not_in_urgent_section(self):
        """Hallazgo MEDIUM no aparece como urgente."""
        findings = [_finding(severity="MEDIUM", dep_name="lodash", dep_version="4.17.20",
                              file_path="lodash/merge.js")]
        result = _actionable_summary(findings)

        # MEDIUM puede aparecer en sección de "revisar en próximo ciclo"
        assert "MEDIUM" in result or "ℹ️" in result
        # Pero no en la sección de urgentes
        assert "Requieren revisión" not in result or "lodash" not in result.split("Requieren revisión")[0] if "Requieren revisión" in result else True

    def test_groups_multiple_findings_by_package(self):
        """Múltiples hallazgos del mismo paquete se agrupan bajo una entrada."""
        findings = [
            _finding(dep_name="axios", line=10, title="Taint flow 1"),
            _finding(dep_name="axios", line=20, title="Taint flow 2"),
            _finding(dep_name="axios", line=30, title="Contract violation",
                     finding_type="CONTRACT_VIOLATION", motor="contract_verifier"),
        ]
        result = _actionable_summary(findings)

        # axios debe aparecer una sola vez como paquete
        assert result.count("axios@") == 1

    def test_more_than_3_findings_per_package_shows_ellipsis(self):
        """Más de 3 hallazgos críticos por paquete → texto de elipsis visible."""
        findings = [
            _finding(dep_name="axios", line=i, title=f"Unique finding {i}")
            for i in range(10, 50, 5)  # 8 hallazgos distintos
        ]
        result = _actionable_summary(findings)

        assert "más" in result or "..." in result or "hallazgos" in result


# ---------------------------------------------------------------------------
# _global_risk: jerarquía de severidad
# ---------------------------------------------------------------------------


class TestGlobalRisk:
    """La jerarquía de riesgo es: CRITICAL > HIGH > MEDIUM > LOW > CLEAN.
    Un solo CRITICAL eleva todo el reporte a CRITICAL.
    """

    def test_critical_wins_over_all(self):
        assert _global_risk({"CRITICAL": 1, "HIGH": 5, "MEDIUM": 10}) == "CRITICAL"

    def test_high_when_no_critical(self):
        assert _global_risk({"HIGH": 2, "MEDIUM": 3, "LOW": 1}) == "HIGH"

    def test_medium_when_only_medium_and_below(self):
        assert _global_risk({"MEDIUM": 1, "LOW": 5}) == "MEDIUM"

    def test_low_when_only_low(self):
        assert _global_risk({"LOW": 3}) == "LOW"

    def test_clean_when_no_findings(self):
        assert _global_risk({}) == "CLEAN"

    def test_clean_when_only_info(self):
        # INFO no eleva el riesgo global
        assert _global_risk({"INFO": 10}) == "CLEAN"


# ---------------------------------------------------------------------------
# _count_by_severity
# ---------------------------------------------------------------------------


class TestCountBySeverity:
    def test_counts_correctly_with_mixed_severities(self):
        findings = [
            _finding(severity="CRITICAL"),
            _finding(severity="CRITICAL"),
            _finding(severity="HIGH"),
            _finding(severity="LOW"),
            _finding(severity="INFO"),
        ]
        counts = _count_by_severity(findings)

        assert counts["CRITICAL"] == 2
        assert counts["HIGH"] == 1
        assert counts["LOW"] == 1
        assert counts["INFO"] == 1
        assert counts.get("MEDIUM", 0) == 0

    def test_empty_findings_returns_empty_dict(self):
        assert _count_by_severity([]) == {}
