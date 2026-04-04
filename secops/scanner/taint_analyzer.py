"""
RF-04: Taint Analyzer — detecta flujo de datos no confiables hacia sinks peligrosos.
No depende de patrones predefinidos de vulnerabilidades conocidas.
Razona desde la estructura del flujo: fuente → [sanitización?] → sink.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ast_engine import ASTNode, ParseResult

# ---------------------------------------------------------------------------
# Definición de fuentes y sinks (principios, no patrones de CVEs)
# ---------------------------------------------------------------------------

# Fuentes: orígenes de datos no confiables
SOURCES_PYTHON = {
    # Input de usuario / red
    "request", "args", "form", "json", "data", "body", "params", "query",
    "environ", "stdin", "input",
    # Variables de entorno
    "os.environ", "os.getenv", "environ.get",
    # Archivos externos
    "open", "read", "readline", "readlines",
    # Red
    "recv", "recvfrom", "socket",
}

SOURCES_JS = {
    # Input de red / HTTP
    "req.body", "req.query", "req.params", "req.headers", "request.body",
    "event.data", "message.data",
    # URLs y configs externas — incluyendo parámetros de función que reciben URLs
    "config.url", "options.url", "baseURL", "url", "uri",
    # Parámetros genéricos de función que reciben datos externos
    "body", "data", "input", "payload", "content",
    # Transformaciones de datos externos sin validación de tamaño
    "decodeURIComponent", "atob",
    # Variables de entorno
    "process.env",
    # Almacenamiento
    "localStorage", "sessionStorage", "document.cookie",
}

# Sinks: operaciones peligrosas si reciben datos no sanitizados
SINKS_PYTHON = {
    # Ejecución de código / procesos
    "eval", "exec", "compile", "subprocess.run", "subprocess.call",
    "subprocess.Popen", "os.system", "os.popen",
    # Allocación sin límite
    "Buffer.from",  # Python no tiene esto pero lo incluimos para cobertura
    # Red (puede enviar datos a destinos no validados)
    "requests.get", "requests.post", "requests.request", "urllib.request.urlopen",
    "httpx.get", "httpx.post", "aiohttp",
    # Filesystem
    "open", "write", "shutil.copy", "os.rename",
    # Deserialización
    "pickle.loads", "yaml.load", "marshal.loads",
    # SQL
    "execute", "cursor.execute",
}

SINKS_JS = {
    # Ejecución
    "eval", "Function", "setTimeout", "setInterval",
    "child_process.exec", "child_process.spawn", "exec", "spawn",
    # Allocación sin límite
    "Buffer.from", "Buffer.alloc", "Buffer.allocUnsafe",
    "decodeURIComponent",  # puede recibir payloads masivos
    # Red (destino no validado)
    "fetch", "axios", "http.request", "https.request", "XMLHttpRequest",
    "buildFullPath",  # función específica de axios — construye URL final
    # DOM (XSS)
    "innerHTML", "outerHTML", "document.write", "insertAdjacentHTML",
    # Filesystem (Node)
    "fs.writeFile", "fs.appendFile", "fs.readFile",
}

# Paquetes donde ciertos sinks son patrones de diseño esperados (no vulnerabilidades).
# Clave: prefijo de nombre de paquete (lowercase). Valor: sinks que son diseño normal.
# Estos hallazgos se etiquetan DESIGN_PATTERN y se excluyen del conteo de riesgo real.
KNOWN_DESIGN_PATTERNS: dict[str, set[str]] = {
    # ORMs y drivers de base de datos — execute ES la API segura parametrizada
    "sqlalchemy": {"execute", "cursor.execute"},
    "alembic": {"execute", "cursor.execute"},
    "asyncpg": {"execute", "cursor.execute"},
    "aiosqlite": {"execute", "cursor.execute"},
    "psycopg2": {"execute", "cursor.execute"},
    "pymysql": {"execute", "cursor.execute"},
    # Motores de templates — eval/exec son su razón de existir
    "mako": {"eval", "exec", "compile"},
    "jinja2": {"eval", "exec", "compile"},
    "chameleon": {"eval", "exec", "compile"},
    # Syntax highlighters — compilan regex sobre datos de entrada por diseño
    "pygments": {"compile", "re.compile", "exec"},
    # Librerías de serialización / parsing — procesan datos externos por diseño
    "pyyaml": {"yaml.load"},
    # Frameworks HTTP — el sink es su API pública
    "aiohttp": {"aiohttp"},
    "httpx": {"httpx.get", "httpx.post"},
}


# Nodos que indican sanitización / validación entre fuente y sink
SANITIZERS_PYTHON = {
    "isinstance", "validate", "sanitize", "escape", "quote", "encode",
    "re.match", "re.fullmatch", "urllib.parse.quote",
    "startswith", "endswith",  # validaciones de dominio/protocolo
}

SANITIZERS_JS = {
    "isAbsoluteURL", "isURLSameOrigin", "validator", "escape", "encodeURIComponent",
    "startsWith", "includes",  # validaciones de dominio
    "allowAbsoluteUrls",  # config check de axios
    "maxContentLength", "maxBodyLength",  # config checks de axios
    "typeof", "instanceof",
}


# ---------------------------------------------------------------------------
# Schema de hallazgo (compartido con contract_verifier y behavioral_delta)
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """Hallazgo de seguridad normalizado. Schema idéntico en los tres motores."""
    finding_type: str          # TAINT_FLOW | CONTRACT_VIOLATION | BEHAVIORAL_ANOMALY
    severity: str              # CRITICAL | HIGH | MEDIUM | LOW | INFO
    dep_name: str
    dep_version: str
    file_path: str
    line: int
    title: str
    description: str
    evidence: str              # fragmento de código o call path
    motor: str                 # taint_analyzer | contract_verifier | behavioral_delta


# ---------------------------------------------------------------------------
# Análisis principal
# ---------------------------------------------------------------------------

def analyze(
    parse_results: list[ParseResult],
    dep_name: str,
    dep_version: str,
) -> list[Finding]:
    """Ejecuta taint analysis sobre los resultados de parseo de una dependencia.

    Args:
        parse_results: Lista de ParseResult de ast_engine.parse_source_tree().
        dep_name: Nombre de la dependencia analizada.
        dep_version: Versión de la dependencia analizada.

    Returns:
        Lista de Finding deduplicada. Vacía si no se detectan flujos taint.
    """
    raw: list[Finding] = []
    for result in parse_results:
        if result.parse_error:
            continue
        raw.extend(_analyze_file(result, dep_name, dep_version))

    # Deduplicar por (file_path, line, sink_base) donde sink_base es el último
    # componente del nombre del sink (ej: "cursor.execute" y "execute" → mismo sink_base
    # "execute"; pero "Buffer.from" y "decodeURIComponent" → bases distintas, se conservan).
    seen: dict[tuple[str, int, str], Finding] = {}
    for f in raw:
        sink_part = f.title.split("→")[-1].strip().split(".")[-1].lower() if "→" in f.title else f.title.lower()
        key = (f.file_path, f.line, sink_part)
        if key not in seen or len(f.title) > len(seen[key].title):
            seen[key] = f
    return list(seen.values())


def _analyze_file(result: ParseResult, dep_name: str, dep_version: str) -> list[Finding]:
    findings = []
    nodes = result.nodes
    language = result.language

    sources = SOURCES_JS if language == "javascript" else SOURCES_PYTHON
    sinks = SINKS_JS if language == "javascript" else SINKS_PYTHON
    sanitizers = SANITIZERS_JS if language == "javascript" else SANITIZERS_PYTHON

    # Indexar nodos por línea para ventana de análisis
    nodes_by_line: dict[int, list[ASTNode]] = {}
    for node in nodes:
        nodes_by_line.setdefault(node.line, []).append(node)

    # Para cada sink encontrado, buscar si hay fuente alcanzable sin sanitización
    for node in nodes:
        if node.node_type not in ("call", "property_access", "assignment"):
            continue

        node_name = node.name or ""
        if not _matches_any(node_name, sinks):
            continue

        # Buscar fuentes en ventana de contexto [línea-30, línea]
        window_start = max(1, node.line - 30)
        found_source = None
        found_sanitizer = False

        for line_num in range(window_start, node.line + 1):
            for ctx_node in nodes_by_line.get(line_num, []):
                ctx_name = ctx_node.name or ctx_node.value or ""
                if _matches_any(ctx_name, sources):
                    found_source = ctx_node
                if _matches_any(ctx_name, sanitizers):
                    found_sanitizer = True

        if found_source and not found_sanitizer:
            # Excluir si es patrón de diseño conocido del paquete
            if _is_known_design_pattern(dep_name, node_name):
                continue
            severity = _infer_severity_taint(node_name, found_source.name or "")
            findings.append(Finding(
                finding_type="TAINT_FLOW",
                severity=severity,
                dep_name=dep_name,
                dep_version=dep_version,
                file_path=result.file_path,
                line=node.line,
                title=f"Taint flow: {found_source.name} → {node_name}",
                description=(
                    f"Datos de fuente no confiable '{found_source.name}' (línea {found_source.line}) "
                    f"alcanzan sink peligroso '{node_name}' (línea {node.line}) "
                    f"sin nodo de sanitización/validación intermedio."
                ),
                evidence=f"{result.file_path}:{found_source.line} → {result.file_path}:{node.line}",
                motor="taint_analyzer",
            ))

    return findings


def _is_known_design_pattern(dep_name: str, sink_name: str) -> bool:
    """Retorna True si el sink es un patrón de diseño esperado para este paquete."""
    dep_lower = dep_name.lower().replace("-", "_").replace(".", "_")
    for pkg_prefix, expected_sinks in KNOWN_DESIGN_PATTERNS.items():
        if dep_lower.startswith(pkg_prefix):
            sink_lower = sink_name.lower()
            for expected in expected_sinks:
                if sink_lower == expected or sink_lower.endswith("." + expected):
                    return True
    return False


def _matches_any(name: str, pool: set[str]) -> bool:
    """Verifica si el nombre coincide con algún elemento del pool (exacto o sufijo)."""
    if not name:
        return False
    name_lower = name.lower()
    for item in pool:
        item_lower = item.lower()
        if name_lower == item_lower or name_lower.endswith("." + item_lower):
            return True
    return False


def _infer_severity_taint(sink_name: str, source_name: str) -> str:
    """Infiere severidad del hallazgo basándose en el tipo de sink y fuente."""
    sink_lower = sink_name.lower()
    # Ejecución de código → siempre CRITICAL
    if any(s in sink_lower for s in ("eval", "exec", "spawn", "system", "compile")):
        return "CRITICAL"
    # Llamadas de red con posible SSRF → HIGH
    if any(s in sink_lower for s in ("fetch", "request", "urlopen", "buildfullpath", "axios")):
        return "HIGH"
    # Allocación sin límite → HIGH
    if any(s in sink_lower for s in ("buffer", "alloc", "decode")):
        return "HIGH"
    # Deserialización → HIGH
    if any(s in sink_lower for s in ("pickle", "yaml.load", "marshal")):
        return "HIGH"
    # SQL → HIGH
    if "execute" in sink_lower:
        return "HIGH"
    # DOM → MEDIUM
    if any(s in sink_lower for s in ("innerhtml", "document.write")):
        return "MEDIUM"
    return "MEDIUM"
