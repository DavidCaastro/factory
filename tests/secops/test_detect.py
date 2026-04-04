"""Tests RF-01: detect.py — detección de lenguajes por manifests."""
import json
from pathlib import Path
import pytest
from secops.scanner.detect import detect_languages, extract_dependencies


@pytest.fixture
def tmp_project(tmp_path):
    return tmp_path


def test_detect_python_requirements(tmp_project):
    (tmp_project / "requirements.txt").write_text("requests==2.31.0\nflask>=2.0\n")
    result = detect_languages(tmp_project)
    assert "python" in result
    assert any("requirements.txt" in str(p) for p in result["python"])


def test_detect_javascript_package_json(tmp_project):
    (tmp_project / "package.json").write_text(json.dumps({"dependencies": {"axios": "^1.7.9"}}))
    result = detect_languages(tmp_project)
    assert "javascript" in result


def test_detect_multiple_languages(tmp_project):
    (tmp_project / "requirements.txt").write_text("flask==2.0.0\n")
    (tmp_project / "package.json").write_text(json.dumps({"dependencies": {"axios": "1.7.9"}}))
    result = detect_languages(tmp_project)
    assert "python" in result
    assert "javascript" in result


def test_detect_empty_project(tmp_project):
    result = detect_languages(tmp_project)
    assert result == {}


def test_detect_rust_cargo(tmp_project):
    (tmp_project / "Cargo.toml").write_text("[dependencies]\nserde = \"1.0\"\n")
    result = detect_languages(tmp_project)
    assert "rust" in result


def test_extract_requirements_txt(tmp_project):
    (tmp_project / "requirements.txt").write_text(
        "requests==2.31.0\nflask>=2.0\n# comentario\n-r other.txt\n"
    )
    deps = extract_dependencies(tmp_project / "requirements.txt")
    names = [d["name"] for d in deps]
    assert "requests" in names
    assert "flask" in names
    assert all(d["language"] == "python" for d in deps)


def test_extract_package_json(tmp_project):
    pkg = {
        "dependencies": {"axios": "^1.7.9", "lodash": "4.17.21"},
        "devDependencies": {"jest": "^29.0.0"},
    }
    (tmp_project / "package.json").write_text(json.dumps(pkg))
    deps = extract_dependencies(tmp_project / "package.json")
    names = [d["name"] for d in deps]
    assert "axios" in names
    assert "lodash" in names
    assert "jest" in names
    assert all(d["language"] == "javascript" for d in deps)
