"""Tests for EngramStore — SHA-256 integrity + AuditAgent-only write."""

import hashlib
import pytest
from pathlib import Path
from piv_oac.engram.store import EngramStore
from piv_oac.exceptions import PIVOACError


@pytest.fixture
def store(tmp_path):
    return EngramStore(engram_dir=tmp_path / "engram")


class TestWriteAtom:
    def test_audit_agent_can_write(self, store):
        store.write_atom("core/test.md", "Hello engram", "AuditAgent")
        path = store._root / "core" / "test.md"
        assert path.exists()

    def test_non_audit_agent_denied(self, store):
        with pytest.raises(PIVOACError, match="authorisation denied"):
            store.write_atom("core/test.md", "Hello", "SecurityAgent")

    def test_write_adds_sha256_header(self, store):
        store.write_atom("core/test.md", "Body content", "AuditAgent")
        content = (store._root / "core" / "test.md").read_text()
        assert "<!-- sha256:" in content

    def test_write_adds_version_header(self, store):
        store.write_atom("core/test.md", "Body", "AuditAgent")
        content = (store._root / "core" / "test.md").read_text()
        assert "<!-- version: 1 -->" in content

    def test_overwrite_increments_version(self, store):
        store.write_atom("core/test.md", "v1", "AuditAgent")
        store.write_atom("core/test.md", "v2", "AuditAgent")
        content = (store._root / "core" / "test.md").read_text()
        assert "<!-- version: 2 -->" in content

    def test_overwrite_creates_snapshot(self, store):
        store.write_atom("core/test.md", "v1 content", "AuditAgent")
        store.write_atom("core/test.md", "v2 content", "AuditAgent")
        snapshots = list((store._snapshots_dir / "core").glob("test_v1_*.md"))
        assert len(snapshots) == 1

    def test_creates_parent_dirs(self, store):
        store.write_atom("deep/nested/atom.md", "content", "AuditAgent")
        assert (store._root / "deep" / "nested" / "atom.md").exists()


class TestReadAtom:
    def test_read_existing_atom(self, store):
        store.write_atom("core/test.md", "Hello read", "AuditAgent")
        content = store.read_atom("core/test.md")
        assert "Hello read" in content

    def test_read_nonexistent_raises(self, store):
        with pytest.raises(PIVOACError, match="not found"):
            store.read_atom("core/missing.md")

    def test_read_verifies_sha256(self, store):
        store.write_atom("core/test.md", "Verified body", "AuditAgent")
        # Tamper with the file directly
        path = store._root / "core" / "test.md"
        original = path.read_text()
        tampered = original.replace("Verified body", "Tampered body")
        path.write_text(tampered)
        with pytest.raises(PIVOACError, match="SHA-256 mismatch"):
            store.read_atom("core/test.md")

    def test_read_legacy_atom_without_header(self, store):
        # Atoms without SHA-256 header are allowed (legacy)
        path = store._root / "core"
        path.mkdir(parents=True, exist_ok=True)
        (path / "legacy.md").write_text("No header atom", encoding="utf-8")
        content = store.read_atom("core/legacy.md")
        assert "No header atom" in content


class TestPathTraversal:
    def test_path_traversal_rejected(self, store):
        with pytest.raises(PIVOACError, match="escapes the engram root"):
            store.read_atom("../../etc/passwd")
