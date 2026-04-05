"""
RF-06: Behavioral Delta — detecta comportamientos nuevos entre versiones de una dependencia.
Construye call graphs desde AST y compara edges entre v_anterior y v_nueva.
Edges nuevos hacia operaciones privilegiadas → BEHAVIORAL_ANOMALY.
Principal defensa contra supply chain attacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .ast_engine import ParseResult
from .taint_analyzer import Finding

# Operaciones privilegiadas: si aparecen como edges NUEVOS en v_nueva → anomalía
PRIVILEGED_OPERATIONS = {
    # Red externa (potencial exfiltración / C2)
    "net_external": {
        "fetch", "XMLHttpRequest", "http.request", "https.request",
        "axios", "urllib.request.urlopen", "requests.get", "requests.post",
        "socket.connect", "net.connect",
    },
    # Ejecución de procesos
    "process_exec": {
        "exec", "eval", "spawn", "fork", "child_process.exec",
        "subprocess.run", "subprocess.Popen", "os.system", "os.popen",
        "shell.exec",
    },
    # Acceso a variables de entorno (posible recolección de credenciales)
    "env_access": {
        "process.env", "os.environ", "os.getenv", "environ.get",
        "dotenv",
    },
    # Filesystem fuera de scope esperado
    "fs_write": {
        "fs.writeFile", "fs.appendFile", "fs.writeFileSync",
        "open",  # modo write
        "shutil.copy", "os.rename", "os.remove",
    },
    # Codificación/decodificación base64 (común en payloads de malware)
    "encoding": {
        "atob", "btoa", "Buffer.from",
        "base64.b64decode", "base64.b64encode",
        "decodeURIComponent",
    },
}

# Categorías que generan CRITICAL vs HIGH
CRITICAL_CATEGORIES = {"net_external", "process_exec"}
HIGH_CATEGORIES = {"env_access", "fs_write", "encoding"}


@dataclass
class CallGraph:
    """Grafo de llamadas construido desde AST."""
    # edges: {caller_function: set of called_functions}
    edges: dict[str, set[str]] = field(default_factory=dict)
    # all_calls: lista plana de todas las llamadas detectadas
    all_calls: list[tuple[str, str, int]] = field(default_factory=list)  # (caller, callee, line)


def build_call_graph(parse_results: list[ParseResult]) -> CallGraph:
    """Construye el call graph de una versión de dependencia desde sus ParseResults.

    Args:
        parse_results: Lista de ParseResult de ast_engine.parse_source_tree().

    Returns:
        CallGraph con edges y all_calls.
    """
    graph = CallGraph()
    current_function = "__module__"

    for result in parse_results:
        if result.parse_error:
            continue
        for node in result.nodes:
            if node.node_type == "function" and node.name:
                current_function = node.name
                if current_function not in graph.edges:
                    graph.edges[current_function] = set()

            elif node.node_type == "call" and node.name:
                if current_function not in graph.edges:
                    graph.edges[current_function] = set()
                graph.edges[current_function].add(node.name)
                graph.all_calls.append((current_function, node.name, node.line))

    return graph


def analyze(
    parse_results_old: list[ParseResult] | None,
    parse_results_new: list[ParseResult],
    dep_name: str,
    version_old: str | None,
    version_new: str,
) -> list[Finding]:
    """Compara call graphs entre versión anterior y nueva.

    Args:
        parse_results_old: ParseResults de v_anterior. None si no hay baseline.
        parse_results_new: ParseResults de v_nueva.
        dep_name: Nombre de la dependencia.
        version_old: Versión anterior. None si no hay baseline.
        version_new: Versión nueva.

    Returns:
        Lista de Finding. BEHAVIORAL_ANOMALY para edges nuevos privilegiados.
        Si no hay baseline → retorna INFO con NO_BASELINE.
    """
    if parse_results_old is None:
        # Sin baseline — registrar pero no bloquear
        return [Finding(
            finding_type="BEHAVIORAL_ANOMALY",
            severity="INFO",
            dep_name=dep_name,
            dep_version=version_new,
            file_path="",
            line=0,
            title=f"NO_BASELINE: sin versión anterior cacheada para {dep_name}",
            description=(
                f"Primera vez que se analiza {dep_name}@{version_new}. "
                "No hay versión anterior en caché para comparar. "
                "El análisis de delta comenzará en el próximo scan con esta versión como baseline."
            ),
            evidence="",
            motor="behavioral_delta",
        )]

    graph_old = build_call_graph(parse_results_old)
    graph_new = build_call_graph(parse_results_new)

    new_edges = _find_new_privileged_edges(graph_old, graph_new)
    findings = []

    for caller, callee, category, line_hint in new_edges:
        severity = "CRITICAL" if category in CRITICAL_CATEGORIES else "HIGH"
        findings.append(Finding(
            finding_type="BEHAVIORAL_ANOMALY",
            severity=severity,
            dep_name=dep_name,
            dep_version=version_new,
            file_path="",
            line=line_hint,
            title=f"BEHAVIORAL_ANOMALY: nueva llamada privilegiada '{callee}' en {dep_name}@{version_new}",
            description=(
                f"La función '{caller}' en {dep_name}@{version_new} llama a '{callee}' "
                f"(categoría: {category}), comportamiento que NO existía en "
                f"{dep_name}@{version_old}. "
                "Esto puede indicar un supply chain attack o un cambio de comportamiento no documentado."
            ),
            evidence=(
                f"{dep_name}@{version_old}: '{caller}' NO llama a '{callee}' | "
                f"{dep_name}@{version_new}: '{caller}' SÍ llama a '{callee}'"
            ),
            motor="behavioral_delta",
        ))

    # Si hay nuevas llamadas pero no privilegiadas → hallazgo informativo
    all_new_edges = _find_all_new_edges(graph_old, graph_new)
    non_privileged_new = len(all_new_edges) - len(new_edges)
    if non_privileged_new > 0 and not findings:
        findings.append(Finding(
            finding_type="BEHAVIORAL_ANOMALY",
            severity="INFO",
            dep_name=dep_name,
            dep_version=version_new,
            file_path="",
            line=0,
            title=f"INFO: {non_privileged_new} nuevos edges en call graph de {dep_name}@{version_new} (no privilegiados)",
            description=(
                f"{dep_name}@{version_new} tiene {non_privileged_new} nuevas llamadas internas "
                f"respecto a {dep_name}@{version_old}. Ninguna es hacia operaciones privilegiadas. "
                "Posiblemente fix o refactor legítimo."
            ),
            evidence=f"Nuevos edges totales: {len(all_new_edges)} | Privilegiados: {len(new_edges)}",
            motor="behavioral_delta",
        ))

    return findings


def _find_new_privileged_edges(
    graph_old: CallGraph,
    graph_new: CallGraph,
) -> list[tuple[str, str, str, int]]:
    """Retorna edges nuevos en graph_new que apuntan a operaciones privilegiadas."""
    privileged_results = []

    for caller, callees_new in graph_new.edges.items():
        callees_old = graph_old.edges.get(caller, set())
        truly_new = callees_new - callees_old

        for callee in truly_new:
            category = _categorize_call(callee)
            if category:
                # Buscar línea aproximada en all_calls
                line_hint = next(
                    (line for c, ce, line in graph_new.all_calls if c == caller and ce == callee),
                    0,
                )
                privileged_results.append((caller, callee, category, line_hint))

    return privileged_results


def _find_all_new_edges(graph_old: CallGraph, graph_new: CallGraph) -> list[tuple[str, str]]:
    """Retorna todos los edges que existen en graph_new pero no en graph_old."""
    new_edges = []
    for caller, callees_new in graph_new.edges.items():
        callees_old = graph_old.edges.get(caller, set())
        for callee in callees_new - callees_old:
            new_edges.append((caller, callee))
    return new_edges


def _categorize_call(callee: str) -> str | None:
    """Determina si una llamada es privilegiada y su categoría. None si no lo es."""
    callee_lower = callee.lower()
    for category, operations in PRIVILEGED_OPERATIONS.items():
        for op in operations:
            if callee_lower == op.lower() or callee_lower.endswith("." + op.lower()):
                return category
    return None
