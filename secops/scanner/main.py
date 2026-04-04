"""
RF-10, RF-11, RF-12: Orquestador de triggers T0, T1 y T2.
T0: solo lectura de payload.json (<1s, no escanea).
T1: consulta component_risk.json para un componente específico.
T2: scan completo en background.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

SECOPS_DIR = Path(__file__).parent.parent
BRIDGE_DIR = SECOPS_DIR / "bridge"
RECORDS_DIR = SECOPS_DIR / "records"
REPORTS_DIR = SECOPS_DIR / "reports"
DEPS_CACHE = SECOPS_DIR / "deps_cache"
PAYLOAD_FILE = BRIDGE_DIR / "payload.json"
COMPONENT_RISK_FILE = BRIDGE_DIR / "component_risk.json"
IMPACT_FILE = RECORDS_DIR / "impact_analysis.jsonl"
MAX_PAYLOAD_AGE_HOURS = 24


# ---------------------------------------------------------------------------
# T0 — Session start: solo lectura, sin escaneo
# ---------------------------------------------------------------------------


def t0_session_read() -> dict:
    """RF-10: Lee payload.json sin ejecutar ningún scanner.

    Returns:
        Dict con risk_level, summary_for_agent y stale flag.
        Nunca lanza excepción — retorna UNKNOWN si el archivo no existe.
    """
    if not PAYLOAD_FILE.exists():
        return {
            "risk_level": "UNKNOWN",
            "action_required": False,
            "summary_for_agent": (
                "SecOpsScanner: payload.json no encontrado. "
                "Ejecutar 'python -m secops scan' para generar el primer reporte."
            ),
            "stale": True,
        }

    try:
        payload = json.loads(PAYLOAD_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {
            "risk_level": "UNKNOWN",
            "action_required": False,
            "summary_for_agent": "SecOpsScanner: payload.json corrompido. Re-ejecutar scan.",
            "stale": True,
        }

    payload["stale"] = _is_stale(payload.get("scan_timestamp", ""))
    return payload


def _is_stale(timestamp_iso: str) -> bool:
    """Retorna True si el scan tiene más de MAX_PAYLOAD_AGE_HOURS horas."""
    if not timestamp_iso:
        return True
    from datetime import datetime, timezone, timedelta

    try:
        ts = datetime.fromisoformat(timestamp_iso)
        age = datetime.now(timezone.utc) - ts
        return age > timedelta(hours=MAX_PAYLOAD_AGE_HOURS)
    except ValueError:
        return True


# ---------------------------------------------------------------------------
# T1 — Pre-component: consulta de riesgo por componente
# ---------------------------------------------------------------------------


def t1_component_check(component_name: str) -> dict:
    """RF-12: Consulta riesgo de un componente/dependencia específica.

    Args:
        component_name: Nombre de la dependencia a consultar.

    Returns:
        Dict con risk_level, max_severity, reachable_critical, finding_types.
        risk_level='UNKNOWN' si no hay datos.
    """
    if not COMPONENT_RISK_FILE.exists():
        return {
            "risk_level": "UNKNOWN",
            "component": component_name,
            "message": "Sin datos de riesgo. Ejecutar scan primero.",
        }

    try:
        data = json.loads(COMPONENT_RISK_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"risk_level": "UNKNOWN", "component": component_name, "message": "component_risk.json corrompido."}

    result = data.get(component_name, {})
    if not result:
        return {"risk_level": "CLEAN", "component": component_name, "message": "Sin hallazgos para esta dependencia."}

    return {"component": component_name, **result}


# ---------------------------------------------------------------------------
# T2 — Background scan completo
# ---------------------------------------------------------------------------


def t2_background_scan(project_root: Path) -> subprocess.Popen:
    """RF-11: Lanza scan completo en proceso hijo sin bloquear la sesión.

    Args:
        project_root: Raíz del proyecto a analizar.

    Returns:
        Popen del proceso hijo. El llamador puede ignorarlo — corre en background.
    """
    return subprocess.Popen(
        [sys.executable, "-m", "secops", "scan", "--root", str(project_root)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


# ---------------------------------------------------------------------------
# Scan completo (llamado por T2 y CLI)
# ---------------------------------------------------------------------------


def run_full_scan(
    project_root: Path,
    dep_filter: str | None = None,
    method_filter: str | None = None,
    on_progress: Callable[[object], None] | None = None,
) -> dict:
    """Ejecuta el scan completo: detect → fetch → parse → analizar → output.

    Args:
        project_root: Raíz del proyecto.
        dep_filter: Si se especifica, solo escanea esta dependencia.
        method_filter: Si se especifica con dep_filter, solo analiza este método/función.
        on_progress: Callback opcional para actualizaciones de progreso.

    Returns:
        Dict con resumen del scan: findings_count, risk_level, report_path.
    """
    from .detect import detect_languages, extract_dependencies
    from .fetcher import fetch_dependency, FetchError, FetchIntegrityError
    from .ast_engine import parse_source_tree
    from .taint_analyzer import analyze as taint_analyze
    from .contract_verifier import analyze as contract_analyze
    from .behavioral_delta import analyze as delta_analyze, build_call_graph
    from .report import generate_report
    from .impact import write_impact
    from .bridge import write_payload
    from .progress import ProgressEvent

    all_findings = []
    dep_summary: dict[str, str] = {}
    languages_detected = []

    def emit(completed_steps: int, total_steps: int, phase: str, message: str) -> None:
        if on_progress is not None:
            on_progress(
                ProgressEvent(
                    completed_steps=completed_steps,
                    total_steps=total_steps,
                    phase=phase,
                    message=message,
                )
            )

    # Detección
    lang_map = detect_languages(project_root)
    languages_detected = list(lang_map.keys())

    # Extraer dependencias de todos los manifests
    all_deps: list[dict] = []
    for lang, manifests in lang_map.items():
        for manifest in manifests:
            try:
                deps = extract_dependencies(manifest)
                all_deps.extend(deps)
            except Exception:
                continue

    # Filtrar si se especifica dep
    if dep_filter:
        all_deps = [d for d in all_deps if d["name"].lower() == dep_filter.lower()]

    processable_deps: list[tuple[dict, str]] = []
    skipped_unpinned = 0
    for dep in all_deps:
        name = dep["name"]
        version_spec = dep.get("version_spec") or ""
        version = version_spec.lstrip("=><~!").strip().split(",")[0] if version_spec else "latest"
        if not version or version == "latest":
            skipped_unpinned += 1
            continue
        processable_deps.append((dep, version))

    total_steps = 3 + (len(processable_deps) * 3)
    step = 1
    emit(step, total_steps, "detect", "Detectando lenguajes y manifests")
    step += 1
    emit(
        step,
        total_steps,
        "deps",
        f"Dependencias detectadas: {len(all_deps)} (analizables: {len(processable_deps)}, sin version fija: {skipped_unpinned})",
    )

    for idx, (dep, version) in enumerate(processable_deps, start=1):
        name = dep["name"]
        language = dep["language"]

        dep_summary[name] = version
        step += 1
        emit(step, total_steps, "fetch", f"Descargando {name}@{version} ({idx}/{len(processable_deps)})")

        try:
            source_dir = fetch_dependency(name, version, language, DEPS_CACHE)
        except (FetchError, FetchIntegrityError) as e:
            # Hallazgo de integridad si es FetchIntegrityError
            if "SUPPLY CHAIN" in str(e) or "Hash" in str(e):
                from .taint_analyzer import Finding

                all_findings.append(
                    Finding(
                        finding_type="BEHAVIORAL_ANOMALY",
                        severity="CRITICAL",
                        dep_name=name,
                        dep_version=version,
                        file_path="",
                        line=0,
                        title=f"INTEGRITY_FAILURE: hash inválido al descargar {name}@{version}",
                        description=str(e),
                        evidence=str(e),
                        motor="fetcher",
                    )
                )
            step += 1
            emit(step, total_steps, "parse", f"Omitiendo parse para {name}@{version} por error de descarga")
            step += 1
            emit(step, total_steps, "analyze", f"Omitiendo analisis para {name}@{version}")
            continue

        step += 1
        emit(step, total_steps, "parse", f"Parseando codigo fuente de {name}@{version}")
        parse_results = parse_source_tree(source_dir, language)

        # Filtrar por método si se especifica
        if method_filter:
            parse_results = _filter_by_method(parse_results, method_filter)

        # Buscar versión anterior en caché para delta
        cached_versions = _get_cached_versions(name, version)
        parse_results_old = None
        version_old = None
        if cached_versions:
            version_old = cached_versions[-1]
            old_dir = DEPS_CACHE / name / version_old
            if old_dir.exists():
                parse_results_old = parse_source_tree(old_dir, language)

        # Ejecutar los tres motores
        step += 1
        emit(step, total_steps, "analyze", f"Ejecutando motores en {name}@{version}")
        all_findings.extend(taint_analyze(parse_results, name, version))
        all_findings.extend(contract_analyze(parse_results, name, version))
        all_findings.extend(delta_analyze(parse_results_old, parse_results, name, version_old, version))

    # Output
    step += 1
    emit(step, total_steps, "output", "Generando reporte y archivos de salida")
    report_path = generate_report(all_findings, dep_summary, languages_detected, REPORTS_DIR)
    write_impact(all_findings, project_root, IMPACT_FILE)
    write_payload(all_findings, BRIDGE_DIR, dep_summary)

    return {
        "findings_count": len(all_findings),
        "risk_level": _risk_from_findings(all_findings),
        "report_path": str(report_path),
        "deps_analyzed": len(dep_summary),
    }


def _filter_by_method(parse_results, method_name: str):
    """Filtra ParseResults para incluir solo nodos relacionados con el método especificado."""
    from .ast_engine import ParseResult

    filtered = []
    for result in parse_results:
        relevant_nodes = [
            n for n in result.nodes if n.name == method_name or (n.value and method_name in (n.value or ""))
        ]
        if relevant_nodes:
            filtered.append(ParseResult(result.file_path, result.language, relevant_nodes, result.parse_error))
    return filtered


def _get_cached_versions(dep_name: str, current_version: str) -> list[str]:
    """Retorna versiones anteriores cacheadas de una dependencia, excluyendo la actual."""
    dep_cache = DEPS_CACHE / dep_name
    if not dep_cache.exists():
        return []
    versions = [d.name for d in dep_cache.iterdir() if d.is_dir() and d.name != current_version]
    return sorted(versions)


def _risk_from_findings(findings) -> str:
    if any(f.severity == "CRITICAL" for f in findings):
        return "CRITICAL"
    if any(f.severity == "HIGH" for f in findings):
        return "HIGH"
    if any(f.severity == "MEDIUM" for f in findings):
        return "MEDIUM"
    if any(f.severity == "LOW" for f in findings):
        return "LOW"
    return "CLEAN"
