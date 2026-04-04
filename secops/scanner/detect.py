"""
RF-01: Detección de lenguajes por manifests.
Lee el directorio del proyecto y detecta lenguajes presentes.
No descarga, no analiza — solo detecta.
"""

from pathlib import Path

MANIFEST_MAP = {
    "python": ["requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile"],
    "javascript": ["package.json"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
}

# Orden de prioridad: el primer manifest encontrado es la fuente autoritativa.
# pyproject.toml gana sobre requirements.txt (evita escanear el env completo).
MANIFEST_PRIORITY = {
    "python": ["pyproject.toml", "setup.cfg", "setup.py", "Pipfile", "requirements.txt"],
    "javascript": ["package.json"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
}


def primary_manifests(project_root: str | Path) -> dict[str, list[Path]]:
    """Retorna únicamente el manifest de mayor prioridad por lenguaje.

    Evita combinar pyproject.toml (deps declaradas) con requirements.txt
    (entorno pip completo), que causa ruido masivo de falsos positivos.

    Returns:
        Dict {lenguaje: [path al manifest prioritario]}.
    """
    root = Path(project_root)
    result: dict[str, list[Path]] = {}
    for language, priority_list in MANIFEST_PRIORITY.items():
        for name in priority_list:
            path = root / name
            if path.exists():
                result[language] = [path]
                break
    return result


def detect_languages(project_root: str | Path) -> dict[str, list[Path]]:
    """Detecta lenguajes presentes en el proyecto a partir de manifests.

    Args:
        project_root: Ruta raíz del proyecto a analizar.

    Returns:
        Dict {lenguaje: [paths de manifests encontrados]}.
        Solo incluye lenguajes con al menos un manifest presente.
    """
    root = Path(project_root)
    result: dict[str, list[Path]] = {}

    for language, manifest_names in MANIFEST_MAP.items():
        found = [root / name for name in manifest_names if (root / name).exists()]
        if found:
            result[language] = found

    return result


def extract_dependencies(manifest_path: Path) -> list[dict]:
    """Extrae lista de dependencias desde un manifest.

    Args:
        manifest_path: Path al archivo de manifest.

    Returns:
        Lista de dicts {name, version_spec, language}.

    Raises:
        ValueError: Si el formato del manifest no es reconocido.
    """
    name = manifest_path.name

    if name == "requirements.txt":
        return _parse_requirements_txt(manifest_path)
    if name == "package.json":
        return _parse_package_json(manifest_path)
    if name == "Cargo.toml":
        return _parse_cargo_toml(manifest_path)
    if name == "go.mod":
        return _parse_go_mod(manifest_path)
    if name == "pyproject.toml":
        return _parse_pyproject_toml(manifest_path)

    raise ValueError(f"Manifest no soportado: {name}")


def _parse_requirements_txt(path: Path) -> list[dict]:
    deps = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Separar nombre de version spec (==, >=, <=, ~=, !=)
        for sep in ("==", ">=", "<=", "~=", "!=", ">", "<"):
            if sep in line:
                name, version_spec = line.split(sep, 1)
                deps.append({"name": name.strip(), "version_spec": sep + version_spec.strip(), "language": "python"})
                break
        else:
            deps.append({"name": line, "version_spec": None, "language": "python"})
    return deps


def _parse_package_json(path: Path) -> list[dict]:
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    deps = []
    for section in ("dependencies", "devDependencies"):
        for name, version_spec in data.get(section, {}).items():
            deps.append({"name": name, "version_spec": version_spec, "language": "javascript"})
    return deps


def _parse_cargo_toml(path: Path) -> list[dict]:
    deps = []
    in_deps = False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line in ("[dependencies]", "[dev-dependencies]"):
            in_deps = True
            continue
        if line.startswith("[") and in_deps:
            in_deps = False
        if in_deps and "=" in line and not line.startswith("#"):
            name, version_spec = line.split("=", 1)
            deps.append({"name": name.strip(), "version_spec": version_spec.strip().strip('"'), "language": "rust"})
    return deps


def _parse_go_mod(path: Path) -> list[dict]:
    deps = []
    in_require = False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line == "require (":
            in_require = True
            continue
        if line == ")" and in_require:
            in_require = False
        if in_require and line and not line.startswith("//"):
            parts = line.split()
            if len(parts) >= 2:
                deps.append({"name": parts[0], "version_spec": parts[1], "language": "go"})
    return deps


def _parse_pyproject_toml(path: Path) -> list[dict]:
    deps = []
    text = path.read_text(encoding="utf-8")
    in_deps = False
    for line in text.splitlines():
        line = line.strip()
        if line == "dependencies = [" or line.startswith("dependencies"):
            in_deps = True
            continue
        if in_deps and line.startswith("]"):
            in_deps = False
        if in_deps and line.startswith('"'):
            dep = line.strip('",').strip()
            for sep in (">=", "==", "<=", "~="):
                if sep in dep:
                    name, version_spec = dep.split(sep, 1)
                    deps.append({"name": name.strip(), "version_spec": sep + version_spec.strip(), "language": "python"})
                    break
            else:
                deps.append({"name": dep, "version_spec": None, "language": "python"})
    return deps
