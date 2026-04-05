"""Tests RF-03: ast_engine.py — parseo de código fuente a AST."""
from pathlib import Path
from unittest.mock import patch
import pytest
from secops.scanner.ast_engine import parse_file, parse_source_tree, ASTNode


def test_parse_python_function(tmp_path):
    src = tmp_path / "test.py"
    src.write_text("def my_func(x):\n    return x + 1\n")
    result = parse_file(src, "python")
    assert result.parse_error is None
    functions = [n for n in result.nodes if n.node_type == "function"]
    assert any(n.name == "my_func" for n in functions)


def test_parse_python_call(tmp_path):
    src = tmp_path / "test.py"
    src.write_text("import os\nos.system('ls')\n")
    result = parse_file(src, "python")
    assert result.parse_error is None
    calls = [n for n in result.nodes if n.node_type == "call"]
    assert any("system" in (n.name or "") for n in calls)


def test_parse_python_import(tmp_path):
    src = tmp_path / "test.py"
    src.write_text("import requests\nfrom os import environ\n")
    result = parse_file(src, "python")
    imports = [n for n in result.nodes if n.node_type == "import"]
    names = [n.name for n in imports]
    assert "requests" in names
    assert "os.environ" in names


def test_parse_python_syntax_error(tmp_path):
    src = tmp_path / "bad.py"
    src.write_text("def broken(\n    return None\n")
    result = parse_file(src, "python")
    assert result.parse_error is not None
    assert result.nodes == []


def test_parse_javascript_function(tmp_path):
    src = tmp_path / "test.js"
    src.write_text("function buildFullPath(baseURL, url) {\n  return baseURL + url;\n}\n")
    result = parse_file(src, "javascript")
    assert result.parse_error is None
    functions = [n for n in result.nodes if n.node_type == "function"]
    assert any(n.name == "buildFullPath" for n in functions)


def test_parse_javascript_require(tmp_path):
    src = tmp_path / "test.js"
    src.write_text("const axios = require('axios');\nconst url = require('url');\n")
    result = parse_file(src, "javascript")
    imports = [n for n in result.nodes if n.node_type == "import"]
    names = [n.name for n in imports]
    assert "axios" in names
    assert "url" in names


def test_parse_javascript_config_access(tmp_path):
    """Detecta accesos a config.allowAbsoluteUrls (clave para CVE-2025-27152)."""
    src = tmp_path / "adapter.js"
    src.write_text(
        "function dispatchRequest(config) {\n"
        "  if (config.allowAbsoluteUrls === false) { return; }\n"
        "  return buildFullPath(config.baseURL, config.url);\n"
        "}\n"
    )
    result = parse_file(src, "javascript")
    assert result.parse_error is None
    property_accesses = [n for n in result.nodes if n.node_type == "property_access"]
    names = [n.name for n in property_accesses]
    assert "allowAbsoluteUrls" in names


def test_parse_source_tree_skips_test_dirs(tmp_path):
    """Verifica que parse_source_tree no analiza directorios de tests."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "main.py").write_text("def hello(): pass\n")
    (tmp_path / "tests" / "test_main.py").write_text("def test_hello(): assert True\n")
    results = parse_source_tree(tmp_path, "python")
    file_paths = [r.file_path for r in results]
    assert any("main.py" in p for p in file_paths)
    assert not any("test_main.py" in p for p in file_paths)


# ---------------------------------------------------------------------------# Nuevos tests para cubrir lineas faltantes# ---------------------------------------------------------------------------


def test_parse_file_oserror_returns_parse_error(tmp_path):
    """OSError al leer el archivo -> ParseResult con parse_error (lines 85-86)."""
    src = tmp_path / "test.py"
    src.write_text("x = 1" + chr(10))
    with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
        result = parse_file(src, "python")
    assert result.parse_error is not None
    assert "permission denied" in result.parse_error
    assert result.nodes == []


def test_parse_file_unsupported_language(tmp_path):
    """Lenguaje no soportado -> ParseResult con mensaje de error (line 93)."""
    src = tmp_path / "test.rs"
    src.write_text("fn main() {}" + chr(10))
    result = parse_file(src, "rust")
    assert result.parse_error is not None
    assert "rust" in result.parse_error.lower() or "soportado" in result.parse_error.lower()
    assert result.nodes == []


def test_parse_python_async_function(tmp_path):
    """visit_AsyncFunctionDef -> funcion async como nodo function (lines 134-136)."""
    src = tmp_path / "async_code.py"
    code = "import aiohttp" + chr(10) + "async def fetch_data(url):" + chr(10) + "    return None" + chr(10)
    src.write_text(code)
    result = parse_file(src, "python")
    assert result.parse_error is None
    functions = [n for n in result.nodes if n.node_type == "function"]
    assert any(n.name == "fetch_data" for n in functions)


def test_parse_python_assignment(tmp_path):
    """visit_Assign -> asignaciones aparecen como nodo assignment (lines 145-149)."""
    src = tmp_path / "assign_code.py"
    code = "x = 42" + chr(10) + "result_val = True" + chr(10)
    src.write_text(code)
    result = parse_file(src, "python")
    assert result.parse_error is None
    assignments = [n for n in result.nodes if n.node_type == "assignment"]
    assert len(assignments) >= 1
    names = [n.name for n in assignments]
    assert any("x" in (n or "") for n in names)


def test_parse_python_if_statement(tmp_path):
    """visit_If -> if statements aparecen como nodo if (lines 168-171)."""
    src = tmp_path / "if_code.py"
    code = "x = 5" + chr(10) + "if x > 3:" + chr(10) + "    pass" + chr(10)
    src.write_text(code)
    result = parse_file(src, "python")
    assert result.parse_error is None
    ifs = [n for n in result.nodes if n.node_type == "if"]
    assert len(ifs) >= 1
    assert any("x" in (n.value or "") for n in ifs)


def test_parse_python_call_name_simple(tmp_path):
    """_py_call_name con ast.Name -> nombre simple (line 184)."""
    src = tmp_path / "call_simple.py"
    src.write_text("system" + chr(40) + chr(39) + "ls" + chr(39) + chr(41) + chr(10))
    result = parse_file(src, "python")
    assert result.parse_error is None
    calls = [n for n in result.nodes if n.node_type == "call"]
    assert any(n.name == "system" for n in calls)


def test_parse_python_call_name_attribute(tmp_path):
    """_py_call_name con ast.Attribute -> nombre compuesto obj.method (line 187)."""
    src = tmp_path / "call_attr.py"
    code = "import os" + chr(10) + "os.system" + chr(40) + chr(39) + "ls" + chr(39) + chr(41) + chr(10)
    src.write_text(code)
    result = parse_file(src, "python")
    assert result.parse_error is None
    calls = [n for n in result.nodes if n.node_type == "call"]
    assert any("system" in (n.name or "") for n in calls)
    assert any("os" in (n.name or "") for n in calls)


def test_parse_javascript_es6_import(tmp_path):
    """Patron ES6 import X from Y -> nodo import (line 213)."""
    src = tmp_path / "module.js"
    code = "import React from " + chr(39) + "react" + chr(39) + ";" + chr(10)
    code += "import { useState } from " + chr(39) + "react" + chr(39) + ";" + chr(10)
    src.write_text(code)
    result = parse_file(src, "javascript")
    assert result.parse_error is None
    imports = [n for n in result.nodes if n.node_type == "import"]
    names = [n.name for n in imports]
    assert "react" in names


def test_parse_javascript_arrow_functions(tmp_path):
    """Arrow functions / const functions -> nodos function (lines 227-229)."""
    src = tmp_path / "arrows.js"
    code = "const handler = async (req, res) => { res.send(data); };" + chr(10)
    code += "const fn = (x) => x + 1;" + chr(10)
    src.write_text(code)
    result = parse_file(src, "javascript")
    assert result.parse_error is None
    functions = [n for n in result.nodes if n.node_type == "function"]
    func_names = [n.name for n in functions]
    assert "handler" in func_names or "fn" in func_names



def test_parse_python_call_name_subscript(tmp_path):
    """_py_call_name fallback ast.unparse para func no Name ni Attribute (line 187)."""
    src = tmp_path / "subscript_call.py"
    # funcs[0]() creates an ast.Subscript as func node
    code = "funcs = [print]" + chr(10) + "funcs[0]()" + chr(10)
    src.write_text(code)
    result = parse_file(src, "python")
    assert result.parse_error is None
    calls = [n for n in result.nodes if n.node_type == "call"]
    # The call should be recorded with some name (ast.unparse result)
    assert len(calls) >= 1
