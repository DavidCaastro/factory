#!/usr/bin/env python3
"""
tools/validate-specs.py — Valida frontmatter YAML de specs/ contra JSON Schemas.
Uso: python tools/validate-specs.py [specs/active/] [--schema-dir specs/schemas/]

Dependencias: pyyaml, jsonschema (en sdk/pyproject.toml)

Comportamiento:
  - Lee cada archivo specs/active/*.md
  - Extrae el bloque YAML frontmatter (entre --- al inicio del archivo)
  - Valida el frontmatter contra el JSON Schema correspondiente en
    specs/schemas/<tipo>.schema.json
  - El tipo se determina por el campo spec_name dentro del frontmatter,
    o como fallback por el nombre del archivo sin extensión
  - Imprime PASS/FAIL por archivo con detalle de errores
  - Exit code 0 si todo pasa, 1 si hay errores
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml no está instalado. Instálalo con: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    import jsonschema
    from jsonschema import Draft7Validator, ValidationError
except ImportError:
    print("ERROR: jsonschema no está instalado. Instálalo con: pip install jsonschema", file=sys.stderr)
    sys.exit(1)


# ──────────────────────────────────────────────
# Colores ANSI (deshabilitados si no es TTY)
# ──────────────────────────────────────────────

_USE_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


GREEN  = lambda t: _c("32", t)
RED    = lambda t: _c("31", t)
YELLOW = lambda t: _c("33", t)
CYAN   = lambda t: _c("36", t)
BOLD   = lambda t: _c("1",  t)


# ──────────────────────────────────────────────
# Extracción de frontmatter
# ──────────────────────────────────────────────

def extract_frontmatter(text: str) -> tuple[dict | None, str]:
    """
    Extrae el bloque YAML frontmatter de un archivo Markdown.

    Retorna (frontmatter_dict, error_message).
    Si no hay frontmatter retorna (None, "").
    Si el YAML es inválido retorna (None, mensaje_de_error).
    """
    lines = text.splitlines()

    # El frontmatter debe comenzar con '---' en la primera línea no vacía
    start_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---":
            start_idx = i
            break
        elif stripped:
            # Hay contenido antes del primer '---': sin frontmatter
            return None, ""

    if start_idx is None:
        return None, ""

    # Buscar el cierre '---'
    end_idx = None
    for i in range(start_idx + 1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return None, "Frontmatter abierto: se encontró '---' de apertura pero no de cierre"

    yaml_block = "\n".join(lines[start_idx + 1:end_idx])

    try:
        data = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        return None, f"YAML inválido en frontmatter: {exc}"

    if not isinstance(data, dict):
        return None, "El frontmatter no es un objeto YAML (dict)"

    return data, ""


# ──────────────────────────────────────────────
# Carga de schemas
# ──────────────────────────────────────────────

def load_schema(schema_dir: Path, spec_type: str) -> tuple[dict | None, str]:
    """
    Carga el JSON Schema para un tipo de spec.

    Retorna (schema_dict, error_message).
    Si el archivo no existe retorna (None, "").  ← SKIP, no error
    Si el JSON es inválido retorna (None, mensaje_de_error).
    """
    schema_path = schema_dir / f"{spec_type}.schema.json"

    if not schema_path.exists():
        return None, ""  # SKIP — schema no encontrado

    try:
        with schema_path.open(encoding="utf-8") as f:
            schema = json.load(f)
        return schema, ""
    except json.JSONDecodeError as exc:
        return None, f"JSON inválido en schema '{schema_path}': {exc}"


# ──────────────────────────────────────────────
# Validación principal
# ──────────────────────────────────────────────

def validate_file(spec_path: Path, schema_dir: Path) -> tuple[str, list[str]]:
    """
    Valida un archivo spec individual.

    Retorna (estado, lista_de_mensajes) donde estado es:
      "PASS"    — frontmatter válido contra schema
      "FAIL"    — frontmatter inválido
      "SKIP"    — schema no encontrado para este tipo
      "WARNING" — sin frontmatter (no es error, pero no se puede verificar)
      "ERROR"   — fallo inesperado (YAML inválido, JSON inválido, etc.)
    """
    try:
        content = spec_path.read_text(encoding="utf-8")
    except OSError as exc:
        return "ERROR", [f"No se pudo leer el archivo: {exc}"]

    frontmatter, fm_error = extract_frontmatter(content)

    if frontmatter is None:
        if fm_error:
            return "ERROR", [fm_error]
        # Sin frontmatter: WARNING — spec válido pero no verificable
        return "WARNING", ["No tiene bloque frontmatter YAML — no se puede validar contra schema"]

    # Determinar el tipo de spec:
    # 1. Usar campo spec_name del propio frontmatter (fuente de verdad)
    # 2. Fallback: nombre del archivo sin extensión
    spec_type = frontmatter.get("spec_name")
    if not spec_type or not isinstance(spec_type, str):
        spec_type = spec_path.stem

    spec_type = spec_type.strip().lower()

    schema, schema_error = load_schema(schema_dir, spec_type)

    if schema is None:
        if schema_error:
            return "ERROR", [schema_error]
        # Schema no encontrado para este tipo: SKIP
        return "SKIP", [f"No existe schema para tipo '{spec_type}' en {schema_dir}"]

    # Validar con jsonschema Draft7Validator
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(frontmatter), key=lambda e: list(e.path))

    if not errors:
        return "PASS", []

    messages = []
    for error in errors:
        path = " → ".join(str(p) for p in error.absolute_path) if error.absolute_path else "(raíz)"
        messages.append(f"  Campo '{path}': {error.message}")

    return "FAIL", messages


# ──────────────────────────────────────────────
# Formateo de resultados
# ──────────────────────────────────────────────

_STATUS_LABELS = {
    "PASS":    ("PASS   ", GREEN),
    "FAIL":    ("FAIL   ", RED),
    "SKIP":    ("SKIP   ", YELLOW),
    "WARNING": ("WARNING", YELLOW),
    "ERROR":   ("ERROR  ", RED),
}


def format_result(spec_path: Path, status: str, messages: list[str], base_dir: Path) -> str:
    label_text, color_fn = _STATUS_LABELS.get(status, ("UNKNOWN", BOLD))
    label = color_fn(f"[{label_text}]")
    rel_path = spec_path.relative_to(base_dir) if spec_path.is_relative_to(base_dir) else spec_path
    line = f"{label}  {rel_path}"
    if messages:
        detail = "\n".join(messages)
        line = f"{line}\n{detail}"
    return line


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida frontmatter YAML de specs/ contra JSON Schemas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python tools/validate-specs.py
  python tools/validate-specs.py specs/active/
  python tools/validate-specs.py specs/active/ --schema-dir specs/schemas/
  python tools/validate-specs.py --quiet
""",
    )
    parser.add_argument(
        "specs_dir",
        nargs="?",
        default="specs/active",
        help="Directorio con archivos spec .md (default: specs/active)",
    )
    parser.add_argument(
        "--schema-dir",
        default="specs/schemas",
        help="Directorio con JSON Schemas (default: specs/schemas)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suprimir output de archivos PASS/SKIP/WARNING; solo mostrar FAIL y ERROR",
    )
    args = parser.parse_args()

    specs_dir  = Path(args.specs_dir)
    schema_dir = Path(args.schema_dir)
    quiet      = args.quiet

    # ── Verificar directorios ──────────────────

    if not specs_dir.exists():
        print(
            YELLOW(f"ADVERTENCIA: El directorio '{specs_dir}' no existe. "
                   "Puede que sea un proyecto nuevo sin specs activos."),
            file=sys.stderr,
        )
        print(GREEN("Sin specs que validar — OK"))
        return 0

    if not specs_dir.is_dir():
        print(RED(f"ERROR: '{specs_dir}' no es un directorio"), file=sys.stderr)
        return 1

    if not schema_dir.exists() or not schema_dir.is_dir():
        print(
            YELLOW(f"ADVERTENCIA: El directorio de schemas '{schema_dir}' no existe o no es un directorio. "
                   "Todos los specs serán SKIP."),
            file=sys.stderr,
        )

    # ── Recolectar archivos spec ───────────────

    spec_files = sorted(specs_dir.glob("*.md"))

    if not spec_files:
        print(YELLOW(f"Sin archivos .md encontrados en '{specs_dir}'"))
        return 0

    # ── Ejecutar validaciones ──────────────────

    # Directorio raíz del proyecto (para rutas relativas en el output)
    # Intentar detectar la raíz como padre común de specs_dir y schema_dir
    try:
        project_root = Path.cwd()
    except Exception:
        project_root = specs_dir.parent

    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0, "WARNING": 0, "ERROR": 0}
    results = []

    for spec_path in spec_files:
        status, messages = validate_file(spec_path, schema_dir)
        counts[status] = counts.get(status, 0) + 1
        results.append((spec_path, status, messages))

    # ── Imprimir resultados ────────────────────

    print(BOLD(f"\nValidando specs en '{specs_dir}' contra schemas en '{schema_dir}'\n"))

    for spec_path, status, messages in results:
        if quiet and status in ("PASS", "SKIP", "WARNING"):
            continue
        print(format_result(spec_path, status, messages, project_root))

    # ── Resumen ───────────────────────────────

    total = len(spec_files)
    summary_parts = [
        GREEN(f"PASS: {counts['PASS']}"),
        RED(f"FAIL: {counts['FAIL']}"),
        YELLOW(f"SKIP: {counts['SKIP']}"),
        YELLOW(f"WARNING: {counts['WARNING']}"),
    ]
    if counts.get("ERROR", 0) > 0:
        summary_parts.append(RED(f"ERROR: {counts['ERROR']}"))

    print(f"\n{BOLD('Resumen')} ({total} archivo{'s' if total != 1 else ''} procesado{'s' if total != 1 else ''}):")
    print("  " + "  |  ".join(summary_parts))

    # ── Exit code ─────────────────────────────

    has_failures = counts["FAIL"] > 0 or counts.get("ERROR", 0) > 0
    if has_failures:
        print(RED("\nResultado: FAIL — uno o más specs no pasaron la validación."))
        return 1

    print(GREEN("\nResultado: PASS — todos los specs validados correctamente."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
