"""
RF-05: Contract Verifier — detecta opciones de configuración con semántica
de restricción que no están enforceadas en todos los code paths.

Principio: si una opción se llama allow*, max*, limit*, restrict*, safe*, block*,
el módulo que la declara debe verificarla en TODOS los paths que ejecutan
el comportamiento que dice restringir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .ast_engine import ASTNode, ParseResult
from .taint_analyzer import Finding

# Prefijos que indican semántica de restricción
RESTRICTION_PREFIXES = (
    "allow", "max", "limit", "restrict", "safe", "block",
    "enable", "disable", "require", "enforce",
)

# Operaciones que deben respetar las opciones de restricción
# Si una opción como 'maxContentLength' existe, toda allocación de buffer debe verificarla
GUARDED_OPERATIONS = {
    # Operaciones de red — deben respetar allow*/restrict*
    "network": {
        "buildFullPath", "fetch", "request", "urlopen", "XMLHttpRequest",
        "http.request", "https.request", "axios",
    },
    # Allocación de memoria — deben respetar max*/limit*
    "allocation": {
        "Buffer.from", "Buffer.alloc", "Buffer.allocUnsafe",
        "bytes", "bytearray", "memoryview",
    },
    # Ejecución de procesos — deben respetar allow*
    "execution": {
        "exec", "eval", "spawn", "subprocess", "os.system",
    },
}


@dataclass
class ConfigOption:
    """Opción de configuración con semántica de restricción detectada."""
    name: str
    file_path: str
    line: int
    prefix: str       # el prefijo de restricción detectado (allow, max, etc.)
    checked_in: list[str] = field(default_factory=list)   # paths de archivo donde se verifica
    missing_in: list[str] = field(default_factory=list)   # paths donde debería verificarse


def analyze(
    parse_results: list[ParseResult],
    dep_name: str,
    dep_version: str,
) -> list[Finding]:
    """Ejecuta contract verification sobre los resultados de parseo.

    Args:
        parse_results: Lista de ParseResult de ast_engine.parse_source_tree().
        dep_name: Nombre de la dependencia analizada.
        dep_version: Versión de la dependencia analizada.

    Returns:
        Lista de Finding con CONTRACT_VIOLATION donde aplique.
    """
    findings = []

    # Paso 1: detectar todas las opciones de restricción declaradas (análisis cross-file)
    config_options = _detect_config_options(parse_results)
    if config_options:
        # Paso 2: para cada opción, verificar en qué archivos se chequea
        _map_checks(config_options, parse_results)
        # Paso 3: detectar operaciones protegidas en archivos donde la opción no se chequea
        for opt in config_options:
            findings.extend(_check_coverage(opt, parse_results, dep_name, dep_version))

    # Paso 4: análisis intra-función — función acepta options/config pero no usa options.max*/limit*
    intra = _detect_options_param_violations(parse_results, dep_name, dep_version)
    existing_keys = {(f.file_path, f.line) for f in findings}
    for f in intra:
        if (f.file_path, f.line) not in existing_keys:
            findings.append(f)

    return findings


def _detect_config_options(parse_results: list[ParseResult]) -> list[ConfigOption]:
    """Detecta opciones de configuración con semántica de restricción."""
    options: dict[str, ConfigOption] = {}

    for result in parse_results:
        if result.parse_error:
            continue
        for node in result.nodes:
            name = node.name or ""
            if not name:
                continue
            # Buscar patrón: config.allowXxx, options.maxXxx, config['maxBodyLength'], etc.
            # También declaraciones: allowAbsoluteUrls = config.allowAbsoluteUrls
            for prefix in RESTRICTION_PREFIXES:
                # Extraer la parte relevante del nombre
                parts = name.split(".")
                for part in parts:
                    part_lower = part.lower()
                    if part_lower.startswith(prefix) and len(part) > len(prefix):
                        canonical = part  # nombre canónico de la opción
                        if canonical not in options:
                            options[canonical] = ConfigOption(
                                name=canonical,
                                file_path=result.file_path,
                                line=node.line,
                                prefix=prefix,
                            )
                        break

    return list(options.values())


def _map_checks(options: list[ConfigOption], parse_results: list[ParseResult]) -> None:
    """Para cada opción, registra en qué archivos se encuentra una verificación."""
    for result in parse_results:
        if result.parse_error:
            continue
        for node in result.nodes:
            for opt in options:
                node_text = f"{node.name or ''} {node.value or ''}"
                if opt.name in node_text or opt.name.lower() in node_text.lower():
                    # Verificar que es un check (if, asignación con el valor, property_access)
                    if node.node_type in ("if", "property_access", "assignment"):
                        if result.file_path not in opt.checked_in:
                            opt.checked_in.append(result.file_path)


def _check_coverage(
    opt: ConfigOption,
    parse_results: list[ParseResult],
    dep_name: str,
    dep_version: str,
) -> list[Finding]:
    """Detecta archivos con operaciones protegidas donde la opción no se verifica."""
    findings = []

    # Determinar qué tipo de operaciones protege esta opción
    guarded = _get_guarded_ops(opt.prefix)

    for result in parse_results:
        if result.parse_error:
            continue
        if result.file_path in opt.checked_in:
            continue  # La opción se verifica aquí — OK

        # Buscar operaciones protegidas en este archivo
        for node in result.nodes:
            node_name = node.name or ""
            for op_name in guarded:
                if node_name == op_name or node_name.endswith("." + op_name):
                    severity = _infer_severity_contract(opt.name, op_name)
                    findings.append(Finding(
                        finding_type="CONTRACT_VIOLATION",
                        severity=severity,
                        dep_name=dep_name,
                        dep_version=dep_version,
                        file_path=result.file_path,
                        line=node.line,
                        title=f"CONTRACT_VIOLATION: '{opt.name}' no enforceada en {_basename(result.file_path)}",
                        description=(
                            f"La opción de configuración '{opt.name}' (declarada en "
                            f"{_basename(opt.file_path)}:{opt.line}) tiene semántica de restricción "
                            f"pero NO se verifica en '{_basename(result.file_path)}' "
                            f"antes de ejecutar '{op_name}' (línea {node.line}). "
                            f"Archivos donde sí se verifica: {opt.checked_in or ['ninguno']}."
                        ),
                        evidence=(
                            f"Opción declarada: {opt.file_path}:{opt.line} | "
                            f"Operación sin check: {result.file_path}:{node.line}"
                        ),
                        motor="contract_verifier",
                    ))
                    break  # Un hallazgo por operación por archivo

    return findings


def _detect_options_param_violations(
    parse_results: list[ParseResult],
    dep_name: str,
    dep_version: str,
) -> list[Finding]:
    """Detecta funciones que aceptan options/config como parámetro pero no usan
    options.max*/limit* antes de ejecutar operaciones de allocación o red.

    Cubre el patrón CVE-2025-58754: fromDataURI(uri, asBlob, options) ejecuta
    Buffer.from() sin consultar options.maxContentLength.
    """
    findings = []
    all_guarded: set[str] = (
        GUARDED_OPERATIONS["allocation"]
        | GUARDED_OPERATIONS["network"]
        | GUARDED_OPERATIONS["execution"]
    )
    # Nombres de parámetros que típicamente transportan opciones de configuración
    options_param_names = {"options", "config", "opts", "cfg", "settings"}
    # Regex para detectar acceso explícito a options.max*/limit*/allow*... en texto libre
    _restriction_re = re.compile(
        r"(?:options|config|opts|cfg)\."
        r"(?:max\w+|limit\w+|allow\w+|restrict\w+|block\w+|safe\w+)",
        re.IGNORECASE,
    )

    for result in parse_results:
        if result.parse_error:
            continue
        nodes = result.nodes

        # ¿Tiene un parámetro de función llamado options/config?
        has_options_param = any(
            node.node_type == "assignment"
            and node.value == "__param__"
            and (node.name or "").lower() in options_param_names
            for node in nodes
        )
        if not has_options_param:
            continue

        # ¿Contiene alguna operación protegida (allocation/network)?
        guarded_nodes = [
            node for node in nodes
            if node.node_type == "call"
            and any(
                (node.name or "") == op or (node.name or "").endswith("." + op)
                for op in all_guarded
            )
        ]
        if not guarded_nodes:
            continue

        # ¿Accede a options.max*/limit*/allow* en algún nodo?
        has_restriction_access = any(
            node.node_type == "property_access"
            and any(
                (node.name or "").lower().startswith(prefix)
                for prefix in ("allow", "max", "limit", "restrict", "safe", "block")
            )
            for node in nodes
        )
        # También buscar en texto libre de nodos if/assignment
        if not has_restriction_access:
            has_restriction_access = any(
                _restriction_re.search(node.value or "")
                for node in nodes
                if node.value
            )

        if not has_restriction_access:
            op_node = guarded_nodes[0]
            findings.append(Finding(
                finding_type="CONTRACT_VIOLATION",
                severity="HIGH",
                dep_name=dep_name,
                dep_version=dep_version,
                file_path=result.file_path,
                line=op_node.line,
                title=(
                    f"CONTRACT_VIOLATION: options.max*/limit* not enforced before {op_node.name}"
                ),
                description=(
                    f"Function accepts 'options'/'config' parameter with restriction semantics "
                    f"but never checks options.max*/limit* before executing guarded operation "
                    f"'{op_node.name}' (line {op_node.line}). "
                    f"Pattern consistent with CVE-2025-58754 (DoS via unchecked allocation)."
                ),
                evidence=f"{result.file_path}:{op_node.line}",
                motor="contract_verifier",
            ))

    return findings


def _get_guarded_ops(prefix: str) -> set[str]:
    """Retorna las operaciones que una opción con ese prefijo debería proteger."""
    if prefix in ("allow", "restrict", "block", "safe"):
        return GUARDED_OPERATIONS["network"] | GUARDED_OPERATIONS["execution"]
    if prefix in ("max", "limit"):
        return GUARDED_OPERATIONS["allocation"] | GUARDED_OPERATIONS["network"]
    if prefix in ("require", "enforce", "enable", "disable"):
        return GUARDED_OPERATIONS["network"] | GUARDED_OPERATIONS["execution"]
    return set()


def _infer_severity_contract(option_name: str, operation: str) -> str:
    """Infiere severidad de una CONTRACT_VIOLATION."""
    opt_lower = option_name.lower()
    op_lower = operation.lower()

    # Opción de URL/red no enforceada → SSRF posible → HIGH
    if any(k in opt_lower for k in ("url", "absolute", "origin", "host", "domain")):
        return "HIGH"
    # Opción de límite de memoria no enforceada → DoS posible → HIGH
    if any(k in opt_lower for k in ("max", "limit", "length", "size")):
        if any(k in op_lower for k in ("buffer", "alloc", "decode")):
            return "HIGH"
        return "MEDIUM"
    # Opción de ejecución → HIGH
    if any(k in op_lower for k in ("exec", "spawn", "eval")):
        return "HIGH"
    return "MEDIUM"


def _basename(path: str) -> str:
    """Retorna solo el nombre del archivo."""
    return path.split("/")[-1].split("\\")[-1]
