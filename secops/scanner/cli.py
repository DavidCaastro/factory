"""
RF-13: CLI con tres niveles de granularidad.
  python -m secops scan                           → scan completo
  python -m secops scan --dep axios               → solo esa dependencia
  python -m secops scan --dep axios --method buildFullPath  → solo ese método
  python -m secops t0                             → leer payload (T0)
  python -m secops check --component axios        → consulta T1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .progress import ConsoleProgressRenderer, ProgressEvent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="secops",
        description="SecOps Scanner — análisis de seguridad local sin herramientas de terceros",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # scan
    scan_p = sub.add_parser("scan", help="Ejecutar scan de seguridad")
    scan_p.add_argument("--dep", metavar="NOMBRE", help="Limitar scan a una dependencia específica")
    scan_p.add_argument("--method", metavar="FUNCIÓN", help="Limitar scan a una función/método (requiere --dep)")
    scan_p.add_argument("--root", metavar="PATH", default=".", help="Raíz del proyecto (default: directorio actual)")
    scan_p.add_argument("--json", action="store_true", help="Output en JSON")
    _add_progress_flags(scan_p)

    # t0
    t0_p = sub.add_parser("t0", help="Leer payload.json (T0 session start, solo lectura)")
    _add_progress_flags(t0_p)

    # check (T1)
    check_p = sub.add_parser("check", help="Consultar riesgo de un componente (T1)")
    check_p.add_argument("--component", metavar="NOMBRE", required=True, help="Nombre de la dependencia a consultar")
    _add_progress_flags(check_p)

    return parser


def run(argv: list[str] | None = None) -> int:
    """Punto de entrada principal de la CLI.

    Returns:
        Exit code: 0=OK, 1=hallazgos críticos/altos, 2=error.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "t0":
        return _cmd_t0(args)
    if args.command == "check":
        return _cmd_check(args)
    if args.command == "scan":
        return _cmd_scan(args)

    parser.print_help()
    return 2


def _cmd_t0(args) -> int:
    from .main import t0_session_read

    renderer = ConsoleProgressRenderer(enabled=_should_show_progress(args, is_json=False))
    renderer.update(ProgressEvent(1, 2, "read", "Leyendo payload de seguridad"))
    payload = t0_session_read()
    renderer.update(ProgressEvent(2, 2, "done", "Payload cargado"))
    renderer.finish()
    _print_t0(payload)
    return 1 if payload.get("action_required") else 0


def _cmd_check(args) -> int:
    from .main import t1_component_check

    renderer = ConsoleProgressRenderer(enabled=_should_show_progress(args, is_json=False))
    renderer.update(ProgressEvent(1, 2, "read", f"Consultando riesgo de {args.component}"))
    result = t1_component_check(args.component)
    renderer.update(ProgressEvent(2, 2, "done", "Consulta completada"))
    renderer.finish()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    risk = result.get("risk_level", "UNKNOWN")
    if risk in ("CRITICAL", "HIGH"):
        return 1
    return 0


def _cmd_scan(args) -> int:
    if args.method and not args.dep:
        print("ERROR: --method requiere --dep", file=sys.stderr)
        return 2

    project_root = Path(args.root).resolve()
    if not project_root.exists():
        print(f"ERROR: --root '{project_root}' no existe", file=sys.stderr)
        return 2

    print(f"SecOpsScanner v0.1 — iniciando scan en {project_root}")
    if args.dep:
        print(f"  → Dependencia: {args.dep}")
    if args.method:
        print(f"  → Método: {args.method}")
    if not _should_show_progress(args, is_json=getattr(args, "json", False)):
        print()

    from .main import run_full_scan

    renderer = ConsoleProgressRenderer(enabled=_should_show_progress(args, is_json=getattr(args, "json", False)))
    result = run_full_scan(
        project_root,
        dep_filter=args.dep,
        method_filter=args.method,
        on_progress=renderer.update,
    )
    renderer.finish()

    if getattr(args, "json", False):
        print(json.dumps(result, indent=2))
    else:
        _print_scan_result(result)

    risk = result.get("risk_level", "CLEAN")
    return 1 if risk in ("CRITICAL", "HIGH") else 0


def _print_t0(payload: dict) -> None:
    risk = payload.get("risk_level", "UNKNOWN")
    stale = payload.get("stale", False)
    summary = payload.get("summary_for_agent", "")
    stale_warn = " [STALE — scan desactualizado]" if stale else ""

    print(f"[SecOps T0] Risk Level: {risk}{stale_warn}")
    print(f"[SecOps T0] {summary}")
    if payload.get("action_required"):
        print("[SecOps T0] ⚠️  action_required=True — revisar antes de Gate 2")


def _print_scan_result(result: dict) -> None:
    print("✅ Scan completado")
    print(f"   Risk Level:       {result['risk_level']}")
    print(f"   Hallazgos totales:{result['findings_count']}")
    print(f"   Dependencias:     {result['deps_analyzed']}")
    print(f"   Reporte:          {result['report_path']}")
    if result["risk_level"] in ("CRITICAL", "HIGH"):
        print("\n⚠️  Hallazgos críticos detectados. Revisar reporte y impact_analysis.jsonl.")


def _add_progress_flags(subparser: argparse.ArgumentParser) -> None:
    grp = subparser.add_mutually_exclusive_group()
    grp.add_argument("--progress", dest="progress", action="store_true", help="Forzar barra de progreso")
    grp.add_argument("--no-progress", dest="progress", action="store_false", help="Desactivar barra de progreso")
    subparser.set_defaults(progress=None)


def _should_show_progress(args, is_json: bool) -> bool:
    if is_json:
        return False
    if getattr(args, "progress", None) is True:
        return True
    if getattr(args, "progress", None) is False:
        return False
    return sys.stdout.isatty()
