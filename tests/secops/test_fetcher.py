"""
Tests para secops/scanner/fetcher.py

Filosofía: cada test verifica un comportamiento de seguridad real.
No se mockea la lógica interna del fetcher. Las llamadas de red se mockean
en la frontera del sistema (urllib.request.urlopen) para no depender de PyPI/npm.

Casos cubiertos:
- Rechazo de hash SHA-256 manipulado (supply chain detection)
- Rechazo de symlinks en tarball (zip-slip / supply chain vector)
- Rechazo de path traversal en tarball (../../etc/passwd)
- Rechazo de path traversal en zip
- Cache hit: no re-descarga si ya existe
- Lenguaje no soportado lanza FetchError
- Metadata PyPI sin distribución disponible lanza FetchError
- Metadata npm sin tarball lanza FetchError
- Error de red lanza FetchError, no silencia el fallo
"""

import hashlib
import io
import json
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from secops.scanner.fetcher import (
    FetchError,
    FetchIntegrityError,
    _download_and_verify,
    _extract,
    _verify_tar_members,
    _verify_zip_members,
    fetch_dependency,
)


# ---------------------------------------------------------------------------
# Helpers para construir artefactos reales de test
# ---------------------------------------------------------------------------


def _make_tarball(tmp_path: Path, members: list[dict]) -> Path:
    """Construye un tarball real con los miembros especificados.

    members: lista de dicts con claves:
        - name: path dentro del tarball
        - content: bytes del archivo (opcional)
        - symlink_target: str → crea symlink (opcional)
        - hardlink_target: str → crea hardlink (opcional)
    """
    archive = tmp_path / "test.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        for m in members:
            info = tarfile.TarInfo(name=m["name"])
            if "symlink_target" in m:
                info.type = tarfile.SYMTYPE
                info.linkname = m["symlink_target"]
                tf.addfile(info)
            elif "hardlink_target" in m:
                info.type = tarfile.LNKTYPE
                info.linkname = m["hardlink_target"]
                tf.addfile(info)
            else:
                content = m.get("content", b"# safe content\n")
                info.size = len(content)
                tf.addfile(info, io.BytesIO(content))
    return archive


def _make_zip(tmp_path: Path, members: list[tuple[str, bytes]]) -> Path:
    """Construye un zip real con los miembros especificados."""
    archive = tmp_path / "test.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for name, content in members:
            zf.writestr(name, content)
    return archive


def _make_pypi_response(name: str, version: str, content: bytes) -> dict:
    """Construye respuesta JSON de PyPI con un sdist cuyo hash coincide con content."""
    sha256 = hashlib.sha256(content).hexdigest()
    return {
        "urls": [
            {
                "packagetype": "sdist",
                "filename": f"{name}-{version}.tar.gz",
                "url": f"https://files.pypi.org/{name}-{version}.tar.gz",
                "digests": {"sha256": sha256},
            }
        ]
    }


# ---------------------------------------------------------------------------
# P1-A: Seguridad — verificación de integridad SHA-256
# ---------------------------------------------------------------------------


class TestHashIntegrity:
    """El fetcher es la primera línea de defensa contra supply chain attacks.
    Un tarball con hash manipulado debe ser rechazado ANTES de extraer su contenido.
    Caso real: axios@1.14.1 fue distribuido con un RAT en el tarball.
    """

    def test_rejects_tampered_hash(self, tmp_path):
        """Hash SHA-256 del tarball no coincide → FetchIntegrityError antes de escritura."""
        content = b"legitimate package content"
        wrong_hash = "a" * 64  # hash fabricado

        dest = tmp_path / "pkg.tar.gz"
        with pytest.raises(FetchIntegrityError) as exc_info:
            _download_and_verify.__wrapped__ if hasattr(_download_and_verify, "__wrapped__") else None
            # Simular descarga exitosa pero con hash incorrecto
            with patch("urllib.request.urlopen") as mock_open:
                mock_resp = MagicMock()
                mock_resp.read.return_value = content
                mock_resp.__enter__ = lambda s: s
                mock_resp.__exit__ = MagicMock(return_value=False)
                mock_open.return_value = mock_resp
                _download_and_verify("https://example.com/pkg.tar.gz", dest, wrong_hash)

        assert "Hash SHA-256 no coincide" in str(exc_info.value)
        # El archivo NO debe haber sido escrito cuando el hash falla
        assert not dest.exists()

    def test_accepts_correct_hash(self, tmp_path):
        """Hash correcto → archivo escrito sin excepción."""
        content = b"legitimate package content"
        correct_hash = hashlib.sha256(content).hexdigest()
        dest = tmp_path / "pkg.tar.gz"

        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.read.return_value = content
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_resp
            _download_and_verify("https://example.com/pkg.tar.gz", dest, correct_hash)

        assert dest.exists()
        assert dest.read_bytes() == content

    def test_skips_verification_when_no_hash_provided(self, tmp_path):
        """Sin hash esperado → se descarga sin verificar (comportamiento documentado)."""
        content = b"content without hash check"
        dest = tmp_path / "pkg.tar.gz"

        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.read.return_value = content
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_resp
            _download_and_verify("https://example.com/pkg.tar.gz", dest, None)

        assert dest.exists()

    def test_network_error_raises_fetch_error(self, tmp_path):
        """Error de red → FetchError, nunca silenciado."""
        dest = tmp_path / "pkg.tar.gz"

        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            with pytest.raises(FetchError) as exc_info:
                _download_and_verify("https://example.com/pkg.tar.gz", dest, None)

        assert "connection refused" in str(exc_info.value).lower() or "Error" in str(exc_info.value)
        assert not dest.exists()


# ---------------------------------------------------------------------------
# P1-B: Seguridad — verificación de miembros de tarball
# ---------------------------------------------------------------------------


class TestTarballSecurity:
    """Tarballs maliciosos son un vector real de supply chain attacks.
    Un tarball puede contener symlinks que apuntan a /etc/passwd o paths
    que escapan del directorio de destino (../../).
    El fetcher debe rechazar estos antes de llamar a extractall().
    """

    def test_rejects_symlink_in_tarball(self, tmp_path):
        """Symlink en tarball → FetchIntegrityError (posible supply chain attack)."""
        archive = _make_tarball(tmp_path, [
            {"name": "pkg/safe.py", "content": b"x = 1"},
            {"name": "pkg/evil_link", "symlink_target": "/etc/passwd"},
        ])
        dest = tmp_path / "extracted"
        dest.mkdir()

        with tarfile.open(archive) as tf:
            with pytest.raises(FetchIntegrityError) as exc_info:
                _verify_tar_members(tf, dest)

        assert "Symlink" in str(exc_info.value)
        assert "SUPPLY CHAIN" in str(exc_info.value)

    def test_rejects_hardlink_in_tarball(self, tmp_path):
        """Hardlink en tarball → FetchIntegrityError."""
        archive = _make_tarball(tmp_path, [
            {"name": "pkg/safe.py", "content": b"x = 1"},
            {"name": "pkg/hard_link", "hardlink_target": "pkg/safe.py"},
        ])
        dest = tmp_path / "extracted"
        dest.mkdir()

        with tarfile.open(archive) as tf:
            with pytest.raises(FetchIntegrityError) as exc_info:
                _verify_tar_members(tf, dest)

        assert "Symlink" in str(exc_info.value) or "link" in str(exc_info.value).lower()

    def test_rejects_path_traversal_in_tarball(self, tmp_path):
        """Path traversal (../../) en tarball → FetchIntegrityError."""
        archive = tmp_path / "traversal.tar.gz"
        # Construir tarball con path traversal manualmente
        with tarfile.open(archive, "w:gz") as tf:
            info = tarfile.TarInfo(name="../../evil.py")
            content = b"malicious = True"
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))

        dest = tmp_path / "extracted"
        dest.mkdir()

        with tarfile.open(archive) as tf:
            with pytest.raises(FetchIntegrityError) as exc_info:
                _verify_tar_members(tf, dest)

        assert "Path traversal" in str(exc_info.value) or "traversal" in str(exc_info.value).lower()
        assert "SUPPLY CHAIN" in str(exc_info.value)

    def test_accepts_clean_tarball(self, tmp_path):
        """Tarball sin symlinks ni traversal → no lanza excepción."""
        archive = _make_tarball(tmp_path, [
            {"name": "pkg/module.py", "content": b"def hello(): pass"},
            {"name": "pkg/utils.py", "content": b"CONSTANT = 42"},
            {"name": "pkg/__init__.py", "content": b""},
        ])
        dest = tmp_path / "extracted"
        dest.mkdir()

        with tarfile.open(archive) as tf:
            _verify_tar_members(tf, dest)  # No debe lanzar


# ---------------------------------------------------------------------------
# P1-C: Seguridad — verificación de miembros de zip
# ---------------------------------------------------------------------------


class TestZipSecurity:
    """Zip slip: un zip puede contener entries con paths que escapan el destino."""

    def test_rejects_path_traversal_in_zip(self, tmp_path):
        """Path traversal en zip → FetchIntegrityError."""
        archive = _make_zip(tmp_path, [
            ("pkg/safe.py", b"x = 1"),
            ("../../evil.py", b"malicious = True"),
        ])
        dest = tmp_path / "extracted"
        dest.mkdir()

        with zipfile.ZipFile(archive) as zf:
            with pytest.raises(FetchIntegrityError) as exc_info:
                _verify_zip_members(zf, dest)

        assert "Path traversal" in str(exc_info.value) or "traversal" in str(exc_info.value).lower()
        assert "SUPPLY CHAIN" in str(exc_info.value)

    def test_accepts_clean_zip(self, tmp_path):
        """Zip sin path traversal → no lanza excepción."""
        archive = _make_zip(tmp_path, [
            ("pkg/module.py", b"def hello(): pass"),
            ("pkg/__init__.py", b""),
        ])
        dest = tmp_path / "extracted"
        dest.mkdir()

        with zipfile.ZipFile(archive) as zf:
            _verify_zip_members(zf, dest)  # No debe lanzar


# ---------------------------------------------------------------------------
# P1-D: Extracción — formato no soportado
# ---------------------------------------------------------------------------


class TestExtraction:
    def test_unsupported_format_raises_fetch_error(self, tmp_path):
        """Formato .rar u otro no soportado → FetchError explícito."""
        fake_rar = tmp_path / "pkg.rar"
        fake_rar.write_bytes(b"Rar! fake content")

        with pytest.raises(FetchError) as exc_info:
            _extract(fake_rar, tmp_path / "dest")

        assert ".rar" in str(exc_info.value) or "no soportado" in str(exc_info.value)

    def test_extracts_clean_tarball(self, tmp_path):
        """Tarball limpio se extrae correctamente al destino."""
        archive = _make_tarball(tmp_path, [
            {"name": "pkg/module.py", "content": b"x = 1"},
        ])
        dest = tmp_path / "extracted"
        dest.mkdir()

        _extract(archive, dest)

        assert (dest / "pkg" / "module.py").exists()

    def test_extracts_clean_zip(self, tmp_path):
        """Zip limpio se extrae correctamente al destino."""
        archive = _make_zip(tmp_path, [
            ("pkg/module.py", b"x = 1"),
        ])
        # Renombrar a .whl con nombre simple (sufijo único)
        whl = tmp_path / "pkg.whl"
        archive.rename(whl)

        dest = tmp_path / "extracted"
        dest.mkdir()

        _extract(whl, dest)
        assert (dest / "pkg" / "module.py").exists()


# ---------------------------------------------------------------------------
# P2: Cache — no re-descarga si ya existe
# ---------------------------------------------------------------------------


class TestCacheHit:
    """El fetcher no debe descargar si el directorio ya existe y tiene contenido.
    Esto previene tráfico innecesario y respeta el estado del cache.
    """

    def test_cache_hit_returns_immediately_without_network(self, tmp_path):
        """Directorio de caché existente con contenido → retorna sin llamada de red."""
        cache_dir = tmp_path / "deps_cache"
        dep_dir = cache_dir / "requests" / "2.31.0"
        dep_dir.mkdir(parents=True)
        (dep_dir / "module.py").write_text("x = 1")

        with patch("urllib.request.urlopen") as mock_open:
            result = fetch_dependency("requests", "2.31.0", "python", cache_dir)
            mock_open.assert_not_called()

        assert result == dep_dir

    def test_empty_cache_dir_triggers_download(self, tmp_path):
        """Directorio vacío (sin contenido) → sí intenta descarga."""
        cache_dir = tmp_path / "deps_cache"
        dep_dir = cache_dir / "requests" / "2.31.0"
        dep_dir.mkdir(parents=True)
        # Directorio vacío: no tiene contenido

        with patch("urllib.request.urlopen", side_effect=OSError("network")):
            with pytest.raises((FetchError, OSError)):
                fetch_dependency("requests", "2.31.0", "python", cache_dir)


# ---------------------------------------------------------------------------
# P3: Lenguaje no soportado
# ---------------------------------------------------------------------------


class TestUnsupportedLanguage:
    def test_unsupported_language_raises_fetch_error(self, tmp_path):
        """Lenguaje no soportado (rust, go) → FetchError explicativo."""
        cache_dir = tmp_path / "deps_cache"

        with pytest.raises(FetchError) as exc_info:
            fetch_dependency("serde", "1.0.0", "rust", cache_dir)

        assert "rust" in str(exc_info.value).lower() or "no soportado" in str(exc_info.value)


# ---------------------------------------------------------------------------
# P4: Sin distribución disponible en PyPI / npm
# ---------------------------------------------------------------------------


class TestMissingDistribution:
    def test_pypi_no_distribution_raises_fetch_error(self, tmp_path):
        """PyPI no retorna distribuciones para el paquete/versión → FetchError."""
        cache_dir = tmp_path / "deps_cache"
        empty_response = json.dumps({"urls": []}).encode()

        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.read.return_value = empty_response
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            with pytest.raises(FetchError) as exc_info:
                fetch_dependency("nonexistent-pkg", "99.0.0", "python", cache_dir)

        assert "distribución" in str(exc_info.value).lower() or "distribution" in str(exc_info.value).lower() or "disponible" in str(exc_info.value).lower()

    def test_npm_no_tarball_raises_fetch_error(self, tmp_path):
        """npm retorna metadata sin tarball → FetchError."""
        cache_dir = tmp_path / "deps_cache"
        response_no_tarball = json.dumps({"dist": {}}).encode()

        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.read.return_value = response_no_tarball
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            with pytest.raises(FetchError) as exc_info:
                fetch_dependency("nonexistent-pkg", "99.0.0", "javascript", cache_dir)

        assert "tarball" in str(exc_info.value).lower() or "disponible" in str(exc_info.value).lower()

    def test_pypi_network_error_raises_fetch_error(self, tmp_path):
        """Error de red al obtener metadata de PyPI → FetchError (no silenciado)."""
        cache_dir = tmp_path / "deps_cache"

        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            with pytest.raises(FetchError) as exc_info:
                fetch_dependency("requests", "2.31.0", "python", cache_dir)

        assert "timeout" in str(exc_info.value).lower() or "PyPI" in str(exc_info.value) or "Error" in str(exc_info.value)
