"""
RF-09: SecurityAgent Bridge — genera payload.json para consumo en sesión.
SecurityAgent lee este archivo en T0. Sin datos sensibles. Sin paths absolutos.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .taint_analyzer import Finding

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def write_payload(
    findings: list[Finding],
    bridge_dir: Path,
    dep_summary: dict[str, str],
) -> Path:
    """Genera bridge/payload.json y bridge/component_risk.json.

    Args:
        findings: Todos los hallazgos de los tres motores.
        bridge_dir: Directorio secops/bridge/.
        dep_summary: {dep_name: version} analizados.

    Returns:
        Path al payload.json generado.
    """
    bridge_dir.mkdir(parents=True, exist_ok=True)

    counts = _count_by_severity(findings)
    risk_level = _global_risk(counts)
    action_required = counts.get("CRITICAL", 0) > 0 or counts.get("HIGH", 0) > 0

    # Agrupar hallazgos por severidad para summary
    critical_titles = [f.title for f in findings if f.severity == "CRITICAL"][:3]
    high_titles = [f.title for f in findings if f.severity == "HIGH"][:3]

    summary = _build_summary(risk_level, counts, critical_titles, high_titles)

    payload = {
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "scanner_version": "0.1",
        "risk_level": risk_level,
        "critical_count": counts.get("CRITICAL", 0),
        "high_count": counts.get("HIGH", 0),
        "medium_count": counts.get("MEDIUM", 0),
        "low_count": counts.get("LOW", 0),
        "info_count": counts.get("INFO", 0),
        "total_findings": len(findings),
        "deps_analyzed": len(dep_summary),
        "action_required": action_required,
        "component_risk": _build_component_risk(findings),
        "summary_for_agent": summary,
    }

    payload_path = bridge_dir / "payload.json"
    payload_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # component_risk.json separado para T1 (consulta pre-componente)
    component_risk_path = bridge_dir / "component_risk.json"
    component_risk_path.write_text(
        json.dumps(payload["component_risk"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return payload_path


def _build_component_risk(findings: list[Finding]) -> dict[str, dict]:
    """Agrupa riesgo por dependencia para consulta T1."""
    components: dict[str, dict] = {}
    for f in findings:
        dep = f.dep_name
        if dep not in components:
            components[dep] = {
                "risk_level": "CLEAN",
                "finding_types": [],
                "max_severity": "INFO",
                "reachable_critical": False,
            }
        comp = components[dep]
        if f.finding_type not in comp["finding_types"]:
            comp["finding_types"].append(f.finding_type)
        if SEVERITY_ORDER.get(f.severity, 99) < SEVERITY_ORDER.get(comp["max_severity"], 99):
            comp["max_severity"] = f.severity
            comp["risk_level"] = f.severity
        if f.severity in ("CRITICAL", "HIGH") and f.finding_type == "BEHAVIORAL_ANOMALY":
            comp["reachable_critical"] = True
    return components


def _build_summary(
    risk_level: str,
    counts: dict[str, int],
    critical_titles: list[str],
    high_titles: list[str],
) -> str:
    """Construye el texto summary_for_agent legible por SecurityAgent."""
    if risk_level == "CLEAN":
        return "SecOpsScanner: sin hallazgos. Todas las dependencias analizadas están limpias."

    parts = [f"SecOpsScanner detectó risk_level={risk_level}."]

    if counts.get("CRITICAL", 0):
        parts.append(f"{counts['CRITICAL']} hallazgo(s) CRITICAL:")
        parts.extend(f"  - {t}" for t in critical_titles)

    if counts.get("HIGH", 0):
        parts.append(f"{counts['HIGH']} hallazgo(s) HIGH:")
        parts.extend(f"  - {t}" for t in high_titles)

    if counts.get("MEDIUM", 0):
        parts.append(f"{counts['MEDIUM']} hallazgo(s) MEDIUM. Ver impact_analysis.jsonl para detalle.")

    parts.append("Acción recomendada: revisar impact_analysis.jsonl y reporte .md más reciente antes de Gate 2.")
    return " ".join(parts)


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
