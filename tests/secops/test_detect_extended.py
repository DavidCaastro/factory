"""
Tests para secops/scanner/detect.py — casos no cubiertos por test_detect.py existente.

Filosofía: detect.py es la entrada del pipeline. Un manifest no detectado = dependencia
no escaneada = posible vulnerabilidad invisible. Se testean los parsers omitidos
y la función primary_manifests() que tenía 0% de cobertura.

Casos cubiertos:
- primary_manifests(): prioridad correcta (pyproject.toml gana sobre requirements.txt)
- primary_manifests(): solo un manifest por lenguaje
- primary_manifests(): proyecto sin manifests → {} vacío
- _parse_cargo_toml: extrae deps de [dependencies] y [dev-dependencies]
- _parse_go_mod: extrae deps del bloque require()
- _parse_go_mod: ignora comentarios // indirect
- _parse_pyproject_toml: extrae deps de la sección dependencies
- extract_dependencies: formato no soportado lanza ValueError
- _parse_requirements_txt: operadores > y < sin = funcionan
- _parse_requirements_txt: líneas con -r se ignoran sin error
"""

from pathlib import Path

import pytest

from secops.scanner.detect import (
    extract_dependencies,
    primary_manifests,
)


# ---------------------------------------------------------------------------
# primary_manifests — 0% cobertura original
# ---------------------------------------------------------------------------


class TestPrimaryManifests:
    """primary_manifests() retorna el manifest de mayor prioridad por lenguaje.
    Evitar combinar pyproject.toml con requirements.txt es crítico para
    evitar falsos positivos masivos del entorno pip completo.
    """

    def test_pyproject_toml_wins_over_requirements_txt(self, tmp_path):
        """pyproject.toml tiene prioridad sobre requirements.txt para Python."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")

        result = primary_manifests(tmp_path)

        assert "python" in result
        assert len(result["python"]) == 1
        assert result["python"][0].name == "pyproject.toml"

    def test_returns_requirements_txt_when_no_pyproject(self, tmp_path):
        """Sin pyproject.toml → requirements.txt es el manifest Python."""
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")

        result = primary_manifests(tmp_path)

        assert result["python"][0].name == "requirements.txt"

    def test_only_one_manifest_per_language(self, tmp_path):
        """Siempre retorna una sola entry por lenguaje, nunca una lista con múltiples."""
        (tmp_path / "pyproject.toml").write_text("")
        (tmp_path / "requirements.txt").write_text("")
        (tmp_path / "package.json").write_text('{"dependencies": {}}')

        result = primary_manifests(tmp_path)

        for lang, paths in result.items():
            assert len(paths) == 1, f"{lang} tiene {len(paths)} manifests, se esperaba 1"

    def test_empty_project_returns_empty_dict(self, tmp_path):
        """Proyecto sin manifests → {} sin error."""
        result = primary_manifests(tmp_path)
        assert result == {}

    def test_detects_javascript_and_python_independently(self, tmp_path):
        """Proyecto full-stack → detecta ambos lenguajes."""
        (tmp_path / "requirements.txt").write_text("django==4.2.0\n")
        (tmp_path / "package.json").write_text('{"dependencies": {"axios": "^1.7.9"}}')

        result = primary_manifests(tmp_path)

        assert "python" in result
        assert "javascript" in result


# ---------------------------------------------------------------------------
# _parse_cargo_toml
# ---------------------------------------------------------------------------


class TestParseCargo:
    def test_parses_dependencies_section(self, tmp_path):
        """Extrae deps de la sección [dependencies]."""
        cargo = tmp_path / "Cargo.toml"
        cargo.write_text(
            '[package]\nname = "myapp"\n\n'
            '[dependencies]\nserde = "1.0"\ntokio = "1.35.0"\n'
        )

        deps = extract_dependencies(cargo)
        names = [d["name"] for d in deps]

        assert "serde" in names
        assert "tokio" in names
        assert all(d["language"] == "rust" for d in deps)

    def test_parses_dev_dependencies_section(self, tmp_path):
        """Extrae deps de [dev-dependencies] también."""
        cargo = tmp_path / "Cargo.toml"
        cargo.write_text(
            '[dependencies]\nserde = "1.0"\n\n'
            '[dev-dependencies]\ncargo-test = "0.1"\n'
        )

        deps = extract_dependencies(cargo)
        names = [d["name"] for d in deps]

        assert "serde" in names
        assert "cargo-test" in names

    def test_ignores_comments_in_cargo(self, tmp_path):
        """Líneas comentadas en Cargo.toml no generan deps."""
        cargo = tmp_path / "Cargo.toml"
        cargo.write_text(
            '[dependencies]\n# serde = "1.0"  # commented out\ntokio = "1.35.0"\n'
        )

        deps = extract_dependencies(cargo)
        names = [d["name"] for d in deps]

        assert "serde" not in names
        assert "tokio" in names


# ---------------------------------------------------------------------------
# _parse_go_mod
# ---------------------------------------------------------------------------


class TestParseGoMod:
    def test_parses_require_block(self, tmp_path):
        """Extrae deps del bloque require() de go.mod."""
        go_mod = tmp_path / "go.mod"
        go_mod.write_text(
            "module github.com/myapp\n\ngo 1.21\n\n"
            "require (\n"
            "\tgithub.com/gin-gonic/gin v1.9.1\n"
            "\tgithub.com/stretchr/testify v1.8.4\n"
            ")\n"
        )

        deps = extract_dependencies(go_mod)
        names = [d["name"] for d in deps]

        assert "github.com/gin-gonic/gin" in names
        assert "github.com/stretchr/testify" in names
        assert all(d["language"] == "go" for d in deps)

    def test_ignores_indirect_comment(self, tmp_path):
        """Líneas con // indirect se incluyen como deps (son deps reales del módulo)."""
        go_mod = tmp_path / "go.mod"
        go_mod.write_text(
            "module github.com/myapp\n\n"
            "require (\n"
            "\tgithub.com/direct/pkg v1.0.0\n"
            "\tgithub.com/indirect/pkg v2.0.0 // indirect\n"
            ")\n"
        )

        deps = extract_dependencies(go_mod)
        names = [d["name"] for d in deps]

        # Ambas se detectan — el scanner decide si las analiza según configuración
        assert "github.com/direct/pkg" in names
        assert "github.com/indirect/pkg" in names

    def test_ignores_pure_comment_lines(self, tmp_path):
        """Líneas que son solo comentarios no generan deps."""
        go_mod = tmp_path / "go.mod"
        go_mod.write_text(
            "module myapp\n\n"
            "require (\n"
            "\t// this is a comment\n"
            "\tgithub.com/real/pkg v1.0.0\n"
            ")\n"
        )

        deps = extract_dependencies(go_mod)
        names = [d["name"] for d in deps]

        assert "github.com/real/pkg" in names
        # Los comentarios puros no deben generar entradas
        assert not any("//" in d["name"] for d in deps)


# ---------------------------------------------------------------------------
# _parse_pyproject_toml
# ---------------------------------------------------------------------------


class TestParsePyprojectToml:
    def test_parses_dependencies_list(self, tmp_path):
        """Extrae deps de la sección dependencies = [...] de pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "myapp"\n\n'
            'dependencies = [\n'
            '    "django>=4.2.0",\n'
            '    "requests==2.31.0",\n'
            '    "pydantic",\n'
            ']\n'
        )

        deps = extract_dependencies(pyproject)
        names = [d["name"] for d in deps]

        assert "django" in names
        assert "requests" in names
        assert "pydantic" in names
        assert all(d["language"] == "python" for d in deps)

    def test_version_specs_extracted_correctly(self, tmp_path):
        """Los version specs se extraen con su operador."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            'dependencies = [\n'
            '    "django>=4.2.0",\n'
            '    "requests==2.31.0",\n'
            ']\n'
        )

        deps = extract_dependencies(pyproject)
        by_name = {d["name"]: d for d in deps}

        assert by_name["django"]["version_spec"].startswith(">=")
        assert by_name["requests"]["version_spec"].startswith("==")


# ---------------------------------------------------------------------------
# _parse_requirements_txt — operadores adicionales
# ---------------------------------------------------------------------------


class TestRequirementsTxtExtended:
    def test_greater_than_without_equal(self, tmp_path):
        """Operador > (sin =) se parsea correctamente."""
        req = tmp_path / "requirements.txt"
        req.write_text("django>4.0\n")

        deps = extract_dependencies(req)
        assert len(deps) == 1
        assert deps[0]["name"] == "django"
        assert ">4.0" in deps[0]["version_spec"]

    def test_less_than_without_equal(self, tmp_path):
        """Operador < (sin =) se parsea correctamente."""
        req = tmp_path / "requirements.txt"
        req.write_text("django<5.0\n")

        deps = extract_dependencies(req)
        assert len(deps) == 1
        assert deps[0]["name"] == "django"

    def test_lines_with_dash_r_are_ignored(self, tmp_path):
        """Líneas -r other.txt se ignoran sin error (son includes, no deps)."""
        req = tmp_path / "requirements.txt"
        req.write_text("-r base.txt\nrequests==2.31.0\n")

        deps = extract_dependencies(req)
        names = [d["name"] for d in deps]

        # Solo la dep real, no la línea -r
        assert "requests" in names
        assert not any("-r" in n or "base.txt" in n for n in names)


# ---------------------------------------------------------------------------
# extract_dependencies: formato no soportado
# ---------------------------------------------------------------------------


class TestUnsupportedManifest:
    def test_unsupported_manifest_raises_value_error(self, tmp_path):
        """Manifest no reconocido → ValueError explícito."""
        unsupported = tmp_path / "Gemfile"
        unsupported.write_text("gem 'rails', '~> 7.0'\n")

        with pytest.raises(ValueError) as exc_info:
            extract_dependencies(unsupported)

        assert "Gemfile" in str(exc_info.value) or "no soportado" in str(exc_info.value)
