"""
RF-08: Impact Analysis — registro append-only de hallazgos con reachability.
Evidencia para responsible disclosure y prevención interna.
Nunca modifica entradas existentes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .taint_analyzer import Finding


def write_impact(
    findings: list[Finding],
    project_root: Path,
    impact_file: Path,
) -> int:
    """Escribe hallazgos nuevos en impact_analysis.jsonl (append-only).

    Args:
        findings: Hallazgos de los tres motores.
        project_root: Raíz del proyecto para calcular reachability.
        impact_file: Path al archivo impact_analysis.jsonl.

    Returns:
        Número de entradas nuevas escritas.
    """
    impact_file.parent.mkdir(parents=True, exist_ok=True)
    existing_keys = _load_existing_keys(impact_file)

    now = datetime.now(timezone.utc).isoformat()
    written = 0

    with impact_file.open("a", encoding="utf-8") as f:
        for finding in findings:
            reachable, call_path = _check_reachability(finding, project_root)
            entry = {
                "date": now,
                "dep": finding.dep_name,
                "version": finding.dep_version,
                "finding_type": finding.finding_type,
                "severity": finding.severity,
                "motor": finding.motor,
                "file": _relative_path(finding.file_path, project_root),
                "line": finding.line,
                "title": finding.title,
                "reachable": reachable,
                "call_path": call_path,
                "evidence": finding.evidence,
                "action": _suggest_action(finding, reachable),
            }
            key = _entry_key(entry)
            if key not in existing_keys:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                existing_keys.add(key)
                written += 1

    return written


def _check_reachability(finding: Finding, project_root: Path) -> tuple[bool | None, str]:
    """Verifica si el hallazgo es alcanzable desde el código del proyecto.

    Returns:
        (reachable, call_path): reachable=True/False/None(no determinado), call_path como string.
    """
    if not project_root.exists():
        return None, "project_root no disponible"

    dep_name = finding.dep_name.lower().replace("-", "_").replace(".", "_")

    # Buscar imports de la dependencia en el proyecto
    import_lines = []
    for src_file in project_root.rglob("*.py"):
        if "secops" in str(src_file) or "deps_cache" in str(src_file):
            continue
        try:
            text = src_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            line_lower = line.lower()
            if f"import {dep_name}" in line_lower or f"from {dep_name}" in line_lower:
                import_lines.append(f"{_relative_path(str(src_file), project_root)}:{i}")

    for src_file in project_root.rglob("*.js"):
        if "secops" in str(src_file) or "deps_cache" in str(src_file):
            continue
        try:
            text = src_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if f"require('{dep_name}')" in line or f'require("{dep_name}")' in line or f"from '{dep_name}'" in line:
                import_lines.append(f"{_relative_path(str(src_file), project_root)}:{i}")

    if not import_lines:
        return False, f"Dependencia '{finding.dep_name}' no importada en el proyecto"

    call_path = f"Importada en: {', '.join(import_lines[:3])}"
    if len(import_lines) > 3:
        call_path += f" (+{len(import_lines) - 3} más)"

    return True, call_path


def _suggest_action(finding: Finding, reachable: bool | None) -> str:
    """Sugiere acción basada en tipo de hallazgo y reachability."""
    if finding.severity == "INFO":
        return "monitor"
    if finding.finding_type == "BEHAVIORAL_ANOMALY" and finding.severity in ("CRITICAL", "HIGH"):
        return "URGENT: revisar cambios de versión — posible supply chain attack"
    if reachable is True and finding.severity in ("CRITICAL", "HIGH"):
        return "upgrade_required: dependencia usada en proyecto y tiene hallazgo crítico"
    if reachable is False:
        return "monitor: hallazgo presente pero dependencia no usada directamente"
    if reachable is None:
        return "investigate: no se pudo determinar reachability"
    return "review"


def _load_existing_keys(impact_file: Path) -> set[str]:
    """Carga claves de entradas existentes para evitar duplicados."""
    if not impact_file.exists():
        return set()
    keys = set()
    for line in impact_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            keys.add(_entry_key(entry))
        except json.JSONDecodeError:
            continue
    return keys


def _entry_key(entry: dict) -> str:
    """Clave única de una entrada: dep+version+finding_type+file+line."""
    return f"{entry['dep']}|{entry['version']}|{entry['finding_type']}|{entry.get('file','')}|{entry.get('line',0)}"


def _relative_path(path: str, root: Path) -> str:
    """Convierte path absoluto a relativo desde root."""
    try:
        return str(Path(path).relative_to(root))
    except ValueError:
        return path.split("/")[-1].split("\\")[-1] if path else ""
