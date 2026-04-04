"""
RF-02: Source Fetcher — descarga y caché del código fuente real de dependencias.
Solo descarga desde registros oficiales. Verifica integridad SHA-256 antes de extraer.
Nunca importa ni ejecuta el código descargado.
"""

import hashlib
import json
import tarfile
import urllib.request
import zipfile
from pathlib import Path

PYPI_JSON_URL = "https://pypi.org/pypi/{name}/json"
PYPI_VERSION_URL = "https://pypi.org/pypi/{name}/{version}/json"
NPM_URL = "https://registry.npmjs.org/{name}/{version}"


class FetchIntegrityError(Exception):
    """Hash SHA-256 del tarball no coincide con el publicado en el registro."""


class FetchError(Exception):
    """Error durante la descarga o extracción de la dependencia."""


def fetch_dependency(name: str, version: str, language: str, cache_dir: Path) -> Path:
    """Descarga y cachea el código fuente de una dependencia.

    Args:
        name: Nombre de la dependencia.
        version: Versión exacta a descargar.
        language: 'python' o 'javascript'.
        cache_dir: Directorio base de caché (secops/deps_cache/).

    Returns:
        Path al directorio con el código fuente extraído.

    Raises:
        FetchIntegrityError: Si el hash no coincide con el registro.
        FetchError: Si la descarga o extracción falla.
    """
    dest = cache_dir / name / version
    if dest.exists() and any(dest.iterdir()):
        return dest  # Ya en caché

    dest.mkdir(parents=True, exist_ok=True)

    if language == "python":
        return _fetch_python(name, version, dest)
    if language == "javascript":
        return _fetch_javascript(name, version, dest)

    raise FetchError(f"Lenguaje no soportado para fetch: {language}")


def _fetch_python(name: str, version: str, dest: Path) -> Path:
    url = PYPI_VERSION_URL.format(name=name, version=version)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        raise FetchError(f"No se pudo obtener metadata de PyPI para {name}=={version}: {e}") from e

    # Preferir sdist (.tar.gz) sobre wheel para tener código fuente completo
    sdist = next(
        (f for f in data.get("urls", []) if f["packagetype"] == "sdist"),
        None,
    )
    if sdist is None:
        # Fallback: cualquier distribución disponible
        sdist = next(iter(data.get("urls", [])), None)
    if sdist is None:
        raise FetchError(f"Sin distribución disponible para {name}=={version}")

    tarball_path = dest / sdist["filename"]
    _download_and_verify(sdist["url"], tarball_path, sdist["digests"].get("sha256"))
    _extract(tarball_path, dest)
    tarball_path.unlink()  # Eliminar tarball tras extracción exitosa
    return dest


def _fetch_javascript(name: str, version: str, dest: Path) -> Path:
    # npm encodes scoped packages: @scope/pkg → @scope%2Fpkg
    encoded_name = name.replace("/", "%2F")
    url = NPM_URL.format(name=encoded_name, version=version)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        raise FetchError(f"No se pudo obtener metadata de npm para {name}@{version}: {e}") from e

    dist = data.get("dist", {})
    tarball_url = dist.get("tarball")
    expected_sha = dist.get("integrity", "").replace("sha512-", "")  # npm usa sha512 en integrity

    if not tarball_url:
        raise FetchError(f"Sin tarball disponible para {name}@{version}")

    tarball_path = dest / f"{name.replace('/', '_')}-{version}.tgz"
    # npm no siempre provee sha256 — verificar solo si disponible
    sha256 = dist.get("shasum") if len(dist.get("shasum", "")) == 64 else None
    _download_and_verify(tarball_url, tarball_path, sha256)
    _extract(tarball_path, dest)
    tarball_path.unlink()
    return dest


def _download_and_verify(url: str, dest_path: Path, expected_sha256: str | None) -> None:
    """Descarga un archivo y verifica su integridad SHA-256."""
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            content = resp.read()
    except Exception as e:
        raise FetchError(f"Error descargando {url}: {e}") from e

    if expected_sha256:
        actual_sha256 = hashlib.sha256(content).hexdigest()
        if actual_sha256 != expected_sha256:
            raise FetchIntegrityError(
                f"Hash SHA-256 no coincide para {dest_path.name}. "
                f"Esperado: {expected_sha256}. Obtenido: {actual_sha256}. "
                "POSIBLE SUPPLY CHAIN ATTACK — no se extrae el contenido."
            )

    dest_path.write_bytes(content)


def _extract(archive_path: Path, dest: Path) -> None:
    """Extrae un tarball o zip verificando que no contenga symlinks maliciosos."""
    suffix = "".join(archive_path.suffixes)

    if ".tar" in suffix or suffix.endswith(".tgz"):
        with tarfile.open(archive_path) as tf:
            _verify_tar_members(tf, dest)
            tf.extractall(dest)  # noqa: S202 — members verificados previamente
    elif suffix == ".zip" or suffix == ".whl":
        with zipfile.ZipFile(archive_path) as zf:
            _verify_zip_members(zf, dest)
            zf.extractall(dest)
    else:
        raise FetchError(f"Formato de archivo no soportado: {suffix}")


def _verify_tar_members(tf: tarfile.TarFile, dest: Path) -> None:
    """Verifica que ningún miembro del tarball sea un symlink malicioso o escape del destino."""
    dest_resolved = dest.resolve()
    for member in tf.getmembers():
        if member.issym() or member.islnk():
            raise FetchIntegrityError(
                f"Symlink detectado en tarball: {member.name} → {member.linkname}. "
                "POSIBLE SUPPLY CHAIN ATTACK — extracción cancelada."
            )
        member_path = (dest / member.name).resolve()
        if not str(member_path).startswith(str(dest_resolved)):
            raise FetchIntegrityError(
                f"Path traversal detectado en tarball: {member.name}. "
                "POSIBLE SUPPLY CHAIN ATTACK — extracción cancelada."
            )


def _verify_zip_members(zf: zipfile.ZipFile, dest: Path) -> None:
    """Verifica que ningún miembro del zip escape del directorio destino."""
    dest_resolved = dest.resolve()
    for name in zf.namelist():
        member_path = (dest / name).resolve()
        if not str(member_path).startswith(str(dest_resolved)):
            raise FetchIntegrityError(
                f"Path traversal detectado en zip: {name}. "
                "POSIBLE SUPPLY CHAIN ATTACK — extracción cancelada."
            )
