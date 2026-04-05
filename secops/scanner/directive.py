"""
Directive mode — output segmentado por dependencia para la rama sec-ops pasiva.
Escribe reports/<dep>/latest.json + reports/<dep>/YYYY-MM-DD.json + reports/index.json.
Consumido por SecurityAgent en FASE 0 via: git show sec-ops:reports/index.json.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SCANNER_VERSION = "0.1"


def write_segmented_reports(
    findings: list,
    dep_summary: dict[str, str],
    reports_dir: Path,
) -> Path:
    """Escribe reportes segmentados por dependencia.

    Estructura de salida:
        reports/<dep>/latest.json      — sobreescrito en cada scan
        reports/<dep>/YYYY-MM-DD.json  — snapshot diario (sobreescrito si corre 2x/día)
        reports/index.json             — inventario de todos los deps escaneados

    El index.json se fusiona con runs anteriores: deps de scans previos se preservan
    hasta que sean re-escaneados (conserva historial de deps que ya no están en manifest).

    Args:
        findings: Lista de Finding de todos los motores.
        dep_summary: {dep_name: version} — deps procesados en el scan.
        reports_dir: Ruta base para reportes (normalmente <repo_root>/reports/).

    Returns:
        Path al index.json generado/actualizado.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    date_str = timestamp.strftime("%Y-%m-%d")

    # Agrupar hallazgos por dep
    findings_by_dep: dict[str, list] = {dep: [] for dep in dep_summary}
    for f in findings:
        if f.dep_name in findings_by_dep:
            findings_by_dep[f.dep_name].append(f)

    new_index_entries: dict[str, dict] = {}

    for dep_name, version in dep_summary.items():
        dep_findings = findings_by_dep.get(dep_name, [])
        risk_level = _risk_from_findings(dep_findings)

        report = {
            "dep_name": dep_name,
            "dep_version": version,
            "scan_timestamp": timestamp.isoformat(),
            "scanner_version": SCANNER_VERSION,
            "risk_level": risk_level,
            "findings_count": len(dep_findings),
            "critical_count": sum(1 for f in dep_findings if f.severity == "CRITICAL"),
            "high_count": sum(1 for f in dep_findings if f.severity == "HIGH"),
            "medium_count": sum(1 for f in dep_findings if f.severity == "MEDIUM"),
            "low_count": sum(1 for f in dep_findings if f.severity == "LOW"),
            "findings": [_finding_to_dict(f) for f in dep_findings],
        }

        dep_dir = reports_dir / dep_name
        dep_dir.mkdir(parents=True, exist_ok=True)

        report_json = json.dumps(report, indent=2, ensure_ascii=False)
        (dep_dir / "latest.json").write_text(report_json, encoding="utf-8")
        (dep_dir / f"{date_str}.json").write_text(report_json, encoding="utf-8")

        new_index_entries[dep_name] = {
            "version": version,
            "last_scan": timestamp.isoformat(),
            "risk_level": risk_level,
            "findings_count": len(dep_findings),
            "report_path": f"reports/{dep_name}/latest.json",
        }

    # Merge con index existente: preserva entradas de runs anteriores
    index_path = reports_dir / "index.json"
    merged_deps: dict[str, dict] = {}
    if index_path.exists():
        try:
            existing = json.loads(index_path.read_text(encoding="utf-8"))
            merged_deps = existing.get("deps", {})
        except (json.JSONDecodeError, OSError):
            pass
    merged_deps.update(new_index_entries)

    index_payload = {
        "last_updated": timestamp.isoformat(),
        "scanner_version": SCANNER_VERSION,
        "deps_count": len(merged_deps),
        "deps": merged_deps,
    }

    index_path.write_text(json.dumps(index_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return index_path


def _risk_from_findings(findings: list) -> str:
    if any(f.severity == "CRITICAL" for f in findings):
        return "CRITICAL"
    if any(f.severity == "HIGH" for f in findings):
        return "HIGH"
    if any(f.severity == "MEDIUM" for f in findings):
        return "MEDIUM"
    if any(f.severity == "LOW" for f in findings):
        return "LOW"
    return "CLEAN"


def _finding_to_dict(f) -> dict:
    return {
        "finding_type": f.finding_type,
        "severity": f.severity,
        "file_path": f.file_path,
        "line": f.line,
        "title": f.title,
        "description": f.description,
        "evidence": f.evidence,
        "motor": f.motor,
    }
