"""
PIV/OAC EngramStore — read/write engram atoms with SHA-256 integrity.

Engram atoms are Markdown files stored under engram/.  Each atom may carry a
header comment that embeds the SHA-256 of its content body:

    <!-- sha256: <hex_digest> -->

On read, the store verifies this digest if present.
On write, only AuditAgent is permitted to create or modify atoms.  A snapshot
of the previous content is saved under engram/snapshots/ before any write.

Write protocol:
1. Reject write if agent_identity != "AuditAgent".
2. If the atom already exists, snapshot it to engram/snapshots/<stem>_v<N>.md.
3. Compute SHA-256 of the new content body.
4. Write the atom with the updated header and an incremented version counter.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from piv_oac.exceptions import PIVOACError

logger = logging.getLogger(__name__)

_SHA256_HEADER_PATTERN = re.compile(r"<!--\s*sha256:\s*([0-9a-f]{64})\s*-->")
_VERSION_HEADER_PATTERN = re.compile(r"<!--\s*version:\s*(\d+)\s*-->")

# Only this identity is authorised to write atoms.
_WRITE_AUTHORIZED_AGENT = "AuditAgent"


class EngramStore:
    """
    Manages read and write access to PIV/OAC engram atoms.

    Parameters
    ----------
    engram_dir:
        Absolute path to the root engram directory (e.g. ``Path("engram")``).
    """

    def __init__(self, engram_dir: Path) -> None:
        self._root = Path(engram_dir).resolve()
        self._snapshots_dir = self._root / "snapshots"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_atom(self, atom_path: str) -> str:
        """
        Read an engram atom and verify its SHA-256 digest if the header is present.

        Parameters
        ----------
        atom_path:
            Path to the atom relative to ``engram_dir``
            (e.g. ``"atoms/sprint_12_backend_audit.md"``).

        Returns
        -------
        str
            Full raw content of the atom file.

        Raises
        ------
        PIVOACError
            If the file does not exist or if the SHA-256 digest mismatches.
        """
        full_path = self._resolve(atom_path)
        if not full_path.exists():
            raise PIVOACError(f"Engram atom not found: {full_path}")

        content = full_path.read_text(encoding="utf-8")
        self._verify_sha256(content, atom_path)
        return content

    def write_atom(
        self,
        atom_path: str,
        content: str,
        agent_identity: str,
    ) -> None:
        """
        Write (create or update) an engram atom.

        Parameters
        ----------
        atom_path:
            Path relative to ``engram_dir``.
        content:
            New body content for the atom (without headers; headers are managed
            by the store).
        agent_identity:
            The ``agent_type`` string of the calling agent.  Only "AuditAgent"
            is authorised.

        Raises
        ------
        PIVOACError
            If *agent_identity* is not authorised.
        """
        if agent_identity != _WRITE_AUTHORIZED_AGENT:
            raise PIVOACError(
                f"Write authorisation denied: agent '{agent_identity}' is not "
                f"permitted to write engram atoms. Only '{_WRITE_AUTHORIZED_AGENT}' "
                f"may write atoms."
            )

        full_path = self._resolve(atom_path)

        # Ensure parent directories exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)

        # Snapshot existing atom before overwriting
        version = 1
        if full_path.exists():
            existing = full_path.read_text(encoding="utf-8")
            version = self._read_version(existing) + 1
            snapshot_path = self._snapshot_path(atom_path, version - 1)
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(existing, encoding="utf-8")
            logger.info(
                "[EngramStore] snapshot written: %s (v%d)", snapshot_path, version - 1
            )

        # Build new atom with updated headers
        new_content = self._build_atom(content, version)
        full_path.write_text(new_content, encoding="utf-8")
        logger.info("[EngramStore] atom written: %s (v%d)", full_path, version)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, atom_path: str) -> Path:
        """Resolve *atom_path* relative to the engram root."""
        resolved = (self._root / atom_path).resolve()
        # Security: ensure the resolved path stays inside _root
        try:
            resolved.relative_to(self._root)
        except ValueError as exc:
            raise PIVOACError(
                f"Atom path '{atom_path}' escapes the engram root directory."
            ) from exc
        return resolved

    def _snapshot_path(self, atom_path: str, version: int) -> Path:
        """Return the snapshot path for a given atom version."""
        stem = Path(atom_path).stem
        suffix = Path(atom_path).suffix or ".md"
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{stem}_v{version}_{ts}{suffix}"
        # Mirror the atom's subdirectory structure under snapshots/
        rel_dir = Path(atom_path).parent
        return self._snapshots_dir / rel_dir / filename

    @staticmethod
    def _compute_sha256(body: str) -> str:
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_atom(body: str, version: int) -> str:
        """Wrap *body* with SHA-256 and version headers."""
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        header = (
            f"<!-- sha256: {digest} -->\n"
            f"<!-- version: {version} -->\n"
        )
        return header + body

    @staticmethod
    def _verify_sha256(content: str, atom_path: str) -> None:
        """Check the embedded SHA-256 header against the content body."""
        match = _SHA256_HEADER_PATTERN.search(content)
        if not match:
            # No header present — skip verification (legacy atom)
            return

        stored_digest = match.group(1)
        # Body is everything after the last header comment line
        body_start = content.find("\n", content.rfind("-->")) + 1
        body = content[body_start:]
        actual_digest = hashlib.sha256(body.encode("utf-8")).hexdigest()

        if actual_digest != stored_digest:
            raise PIVOACError(
                f"SHA-256 mismatch for atom '{atom_path}': "
                f"stored={stored_digest}, computed={actual_digest}. "
                f"Atom may have been modified outside the EngramStore."
            )

    @staticmethod
    def _read_version(content: str) -> int:
        """Extract the version counter from the atom header, defaulting to 0."""
        match = _VERSION_HEADER_PATTERN.search(content)
        return int(match.group(1)) if match else 0
