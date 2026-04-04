"""
RF-03: AST Engine — parseo de código fuente a árbol sintáctico navegable.
Soporta Python (ast stdlib) y JavaScript (parser propio sobre texto).
NUNCA ejecuta el código analizado. Solo lectura de texto → árbol.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Schema de nodo AST unificado (independiente del lenguaje)
# ---------------------------------------------------------------------------

@dataclass
class ASTNode:
    """Nodo del árbol sintáctico normalizado, independiente del lenguaje."""
    node_type: str          # "function", "call", "assignment", "import", "property_access", "literal", "if", "return"
    name: str | None        # Nombre del nodo si aplica
    value: str | None       # Valor literal o expresión como string
    children: list[ASTNode] = field(default_factory=list)
    file_path: str = ""
    line: int = 0
    language: str = ""
    raw: object = field(default=None, repr=False)  # Nodo original del parser


@dataclass
class ParseResult:
    """Resultado del parseo de un archivo."""
    file_path: str
    language: str
    nodes: list[ASTNode]
    parse_error: str | None = None  # None = éxito


# ---------------------------------------------------------------------------
# Punto de entrada principal
# ---------------------------------------------------------------------------

def parse_source_tree(source_dir: Path, language: str) -> list[ParseResult]:
    """Parsea todos los archivos de código fuente en un directorio.

    Args:
        source_dir: Directorio con el código fuente de la dependencia.
        language: 'python' o 'javascript'.

    Returns:
        Lista de ParseResult, uno por archivo. Archivos con error de parseo
        incluyen parse_error != None — no se lanzan excepciones.
    """
    extensions = {
        "python": [".py"],
        "javascript": [".js", ".mjs", ".cjs"],
    }
    exts = extensions.get(language, [])
    results = []

    for file_path in source_dir.rglob("*"):
        if file_path.suffix not in exts:
            continue
        if _should_skip(file_path):
            continue
        results.append(parse_file(file_path, language))

    return results


def parse_file(file_path: Path, language: str) -> ParseResult:
    """Parsea un único archivo a lista de ASTNode.

    Args:
        file_path: Path al archivo de código fuente.
        language: 'python' o 'javascript'.

    Returns:
        ParseResult con nodes o parse_error.
    """
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return ParseResult(str(file_path), language, [], parse_error=str(e))

    if language == "python":
        return _parse_python(file_path, source)
    if language == "javascript":
        return _parse_javascript(file_path, source)

    return ParseResult(str(file_path), language, [], parse_error=f"Lenguaje no soportado: {language}")


# ---------------------------------------------------------------------------
# Parser Python (ast stdlib)
# ---------------------------------------------------------------------------

def _parse_python(file_path: Path, source: str) -> ParseResult:
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        return ParseResult(str(file_path), "python", [], parse_error=str(e))

    visitor = _PythonVisitor(str(file_path))
    visitor.visit(tree)
    return ParseResult(str(file_path), "python", visitor.nodes)


class _PythonVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.nodes: list[ASTNode] = []

    def _node(self, node_type: str, name=None, value=None, line=0, raw=None, children=None) -> ASTNode:
        return ASTNode(
            node_type=node_type,
            name=name,
            value=value,
            children=children or [],
            file_path=self.file_path,
            line=line,
            language="python",
            raw=raw,
        )

    def visit_FunctionDef(self, node: ast.FunctionDef):
        n = self._node("function", name=node.name, line=node.lineno, raw=node)
        self.nodes.append(n)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        n = self._node("function", name=node.name, line=node.lineno, raw=node)
        self.nodes.append(n)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        name = _py_call_name(node)
        n = self._node("call", name=name, line=node.lineno, raw=node)
        self.nodes.append(n)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        targets = [ast.unparse(t) for t in node.targets]
        value = ast.unparse(node.value)
        n = self._node("assignment", name=",".join(targets), value=value, line=node.lineno, raw=node)
        self.nodes.append(n)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            n = self._node("import", name=alias.name, line=node.lineno, raw=node)
            self.nodes.append(n)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            n = self._node("import", name=f"{module}.{alias.name}", line=node.lineno, raw=node)
            self.nodes.append(n)

    def visit_Attribute(self, node: ast.Attribute):
        n = self._node("property_access", name=node.attr, value=ast.unparse(node), line=node.lineno, raw=node)
        self.nodes.append(n)
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        cond = ast.unparse(node.test)
        n = self._node("if", value=cond, line=node.lineno, raw=node)
        self.nodes.append(n)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        value = ast.unparse(node.value) if node.value else None
        n = self._node("return", value=value, line=node.lineno, raw=node)
        self.nodes.append(n)
        self.generic_visit(node)


def _py_call_name(node: ast.Call) -> str:
    """Extrae el nombre de una llamada como string legible."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return f"{ast.unparse(func.value)}.{func.attr}"
    return ast.unparse(func)


# ---------------------------------------------------------------------------
# Parser JavaScript (implementación propia sobre texto)
# ---------------------------------------------------------------------------

def _parse_javascript(file_path: Path, source: str) -> ParseResult:
    """Parser JS basado en análisis de texto + regex sobre patrones conocidos.

    No es un parser completo — extrae los nodos relevantes para análisis de seguridad:
    funciones, llamadas, imports, asignaciones y accesos a propiedades.
    Suficiente para Taint Analysis, Contract Verification y Behavioral Delta.
    """
    nodes: list[ASTNode] = []
    lines = source.splitlines()

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        fp = str(file_path)

        # Imports: require() y ES modules
        for m in re.finditer(r'require\(["\']([^"\']+)["\']\)', line):
            nodes.append(ASTNode("import", name=m.group(1), value=None, file_path=fp, line=i, language="javascript"))

        for m in re.finditer(r'import\s+.*?\s+from\s+["\']([^"\']+)["\']', line):
            nodes.append(ASTNode("import", name=m.group(1), value=None, file_path=fp, line=i, language="javascript"))

        # Definiciones de función + parámetros (los parámetros son fuentes potenciales de taint)
        for m in re.finditer(r'function\s+(\w+)\s*\(([^)]*)\)', line):
            fname = m.group(1)
            params = m.group(2)
            nodes.append(ASTNode("function", name=fname, value=None, file_path=fp, line=i, language="javascript"))
            # Registrar cada parámetro como asignación/source potencial
            for param in params.split(","):
                param = param.strip()
                if param and param != "":
                    nodes.append(ASTNode("assignment", name=param, value="__param__", file_path=fp, line=i, language="javascript"))
        # Funciones arrow / const
        for m in re.finditer(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)', line):
            name = m.group(1)
            if name:
                nodes.append(ASTNode("function", name=name, value=None, file_path=fp, line=i, language="javascript"))

        # Llamadas a función/método relevantes para seguridad
        for m in re.finditer(r'([\w.]+)\s*\(', line):
            call_name = m.group(1)
            if not _is_keyword(call_name):
                nodes.append(ASTNode("call", name=call_name, value=None, file_path=fp, line=i, language="javascript"))

        # Asignaciones de configuración (patrón clave para Contract Verifier)
        for m in re.finditer(r'([\w.]+)\s*=\s*(.+?)(?:;|$)', line):
            nodes.append(ASTNode("assignment", name=m.group(1).strip(), value=m.group(2).strip(), file_path=fp, line=i, language="javascript"))

        # Accesos a propiedad config (allow*, max*, limit*)
        for m in re.finditer(r'(?:config|options|opts)\.(allow\w+|max\w+|limit\w+|restrict\w+|safe\w+|block\w+)', line):
            nodes.append(ASTNode("property_access", name=m.group(1), value=m.group(0), file_path=fp, line=i, language="javascript"))

        # Condicionales con config
        if re.search(r'\bif\s*\(', line):
            nodes.append(ASTNode("if", name=None, value=stripped, file_path=fp, line=i, language="javascript"))

    return ParseResult(str(file_path), "javascript", nodes)


def _should_skip(path: Path) -> bool:
    """Retorna True si el archivo debe ignorarse en el análisis."""
    skip_parts = {"node_modules", "__pycache__", ".git", "test", "tests", "spec", "specs", "dist", "build"}
    return any(part in skip_parts for part in path.parts)


def _is_keyword(name: str) -> bool:
    """Retorna True si el nombre es una palabra clave JS que no es una llamada real."""
    keywords = {"if", "for", "while", "switch", "catch", "return", "typeof", "instanceof", "new"}
    return name.split(".")[-1] in keywords
