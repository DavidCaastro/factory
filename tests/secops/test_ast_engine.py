"""Tests RF-03: ast_engine.py — parseo de código fuente a AST."""
from pathlib import Path
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
