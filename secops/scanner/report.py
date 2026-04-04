"""
RF-07: Report Generator — genera reporte Markdown con todos los hallazgos.
Sin filtros por severidad. Sin herramientas externas. Template strings Python puro.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .taint_analyzer import Finding

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def generate_report(
    findings: list[Finding],
    dep_summary: dict[str, str],  # {dep_name: version}
    languages_detected: list[str],
    reports_dir: Path,
) -> Path:
    """Genera el reporte Markdown del scan.

    Args:
        findings: Todos los hallazgos de los tres motores.
        dep_summary: Dependencias analizadas con sus versiones.
        languages_detected: Lenguajes detectados en el proyecto.
        reports_dir: Directorio donde guardar el reporte.

    Returns:
        Path al archivo .md generado.
    """
    now = datetime.now(timezone.utc)
    filename = now.strftime("%Y-%m-%d_%H%M_scan.md")
    report_path = reports_dir / filename
    reports_dir.mkdir(parents=True, exist_ok=True)

    content = _build_report(findings, dep_summary, languages_detected, now)
    report_path.write_text(content, encoding="utf-8")
    return report_path


def _build_report(
    findings: list[Finding],
    dep_summary: dict[str, str],
    languages_detected: list[str],
    timestamp: datetime,
) -> str:
    sorted_findings = sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 99), f.dep_name))

    counts = _count_by_severity(findings)
    risk_level = _global_risk(counts)

    sections = [
        _header(timestamp, risk_level, counts),
        _stack_section(languages_detected, dep_summary),
        _summary_table(sorted_findings),
        _findings_detail(sorted_findings),
        _footer(timestamp),
    ]
    return "\n\n".join(s for s in sections if s)


def _header(timestamp: datetime, risk_level: str, counts: dict) -> str:
    return f"""# SecOps Scan Report
> Generado: {timestamp.strftime('%Y-%m-%d %H:%M UTC')} | Risk Level: **{risk_level}**
> Motor: SecOpsScanner v0.1 | Análisis local sin herramientas de terceros

## Resumen ejecutivo

| Severidad | Hallazgos |
|---|---|
| CRITICAL | {counts.get('CRITICAL', 0)} |
| HIGH | {counts.get('HIGH', 0)} |
| MEDIUM | {counts.get('MEDIUM', 0)} |
| LOW | {counts.get('LOW', 0)} |
| INFO | {counts.get('INFO', 0)} |
| **Total** | **{sum(counts.values())}** |"""


def _stack_section(languages: list[str], deps: dict[str, str]) -> str:
    langs = ", ".join(languages) if languages else "No detectado"
    deps_list = "\n".join(f"- `{name}` @ `{ver}`" for name, ver in deps.items())
    return f"""## Stack analizado

**Lenguajes detectados:** {langs}

**Dependencias analizadas:**
{deps_list if deps_list else '- Ninguna'}"""


def _summary_table(findings: list[Finding]) -> str:
    if not findings:
        return "## Hallazgos\n\n✅ Sin hallazgos detectados."

    rows = "\n".join(
        f"| {f.severity} | {f.dep_name}@{f.dep_version} | {f.finding_type} | {f.title[:60]}... | {f.file_path.split(chr(47))[-1].split(chr(92))[-1]}:{f.line} |"
        for f in findings
    )
    return f"""## Tabla de hallazgos

| Severidad | Dependencia | Tipo | Título | Ubicación |
|---|---|---|---|---|
{rows}"""


def _findings_detail(findings: list[Finding]) -> str:
    if not findings:
        return ""

    blocks = []
    for i, f in enumerate(findings, start=1):
        block = f"""### [{f.severity}] {i}. {f.title}

| Atributo | Valor |
|---|---|
| Tipo | `{f.finding_type}` |
| Dependencia | `{f.dep_name}@{f.dep_version}` |
| Motor | `{f.motor}` |
| Ubicación | `{f.file_path}:{f.line}` |

**Descripción:** {f.description}

**Evidencia:** `{f.evidence}`"""
        blocks.append(block)

    return "## Detalle de hallazgos\n\n" + "\n\n---\n\n".join(blocks)


def _footer(timestamp: datetime) -> str:
    return f"""---
*Reporte generado por SecOpsScanner v0.1 — {timestamp.strftime('%Y-%m-%d %H:%M UTC')}*
*Análisis semántico propio: Taint Analysis + Contract Verification + Behavioral Delta*
*Sin dependencias de terceros. Sin bases de datos de CVEs. Sin LLM.*"""


def _count_by_severity(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts


def _global_risk(counts: dict[str, int]) -> str:
    if counts.get("CRITICAL", 0) > 0:
        return "CRITICAL"
    if counts.get("HIGH", 0) > 0:
        return "HIGH"
    if counts.get("MEDIUM", 0) > 0:
        return "MEDIUM"
    if counts.get("LOW", 0) > 0:
        return "LOW"
    return "CLEAN"
