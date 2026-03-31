"""
piv validate — Check framework specs integrity.

Performs the 4 checks from skills/framework-quality.md:
  1. Cross-reference integrity  (all referenced files exist)
  2. specs/active/INDEX.md has no [PENDIENTE] in required fields
  3. execution_mode is a known valid value
  4. compliance_scope is a known valid value

Exit codes:
  0 — all checks passed
  1 — one or more checks failed
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click


_VALID_EXECUTION_MODES = {"DEVELOPMENT", "RESEARCH", "MIXED", "INIT"}
_VALID_COMPLIANCE_SCOPES = {"FULL", "MINIMAL", "NONE"}

# Fields in INDEX.md that must NOT be [PENDIENTE] to be runnable
_REQUIRED_INDEX_FIELDS = {
    "Nombre",
    "Stack principal",
    "execution_mode",
    "compliance_scope",
    "Objetivo en curso",
}


def _check_cross_references(root: Path) -> list[str]:
    """Return list of broken cross-references found in registry/ and skills/ files."""
    errors: list[str] = []
    search_dirs = [root / "registry", root / "skills"]
    pattern = re.compile(r"`([a-zA-Z0-9_/.-]+\.md)`")

    trusted_prefixes = ("skills/", "registry/", "engram/", "tools/", "sdk/", "contracts/")

    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        for md_file in search_dir.rglob("*.md"):
            text = md_file.read_text(encoding="utf-8", errors="replace")
            for match in pattern.finditer(text):
                ref = match.group(1)
                if not any(ref.startswith(p) for p in trusted_prefixes):
                    continue
                if "specs/active/" in ref:
                    continue
                target = root / ref
                if not target.exists():
                    errors.append(f"  [FAIL] {md_file.relative_to(root)} → `{ref}` NOT FOUND")

    return errors


def _check_index(index_path: Path) -> list[str]:
    """Return list of issues found in specs/active/INDEX.md."""
    errors: list[str] = []
    if not index_path.exists():
        return ["  [FAIL] specs/active/INDEX.md — file not found"]

    text = index_path.read_text(encoding="utf-8", errors="replace")

    # Check required fields not [PENDIENTE]
    for field in _REQUIRED_INDEX_FIELDS:
        pattern = re.compile(rf"\|\s*{re.escape(field)}\s*\|\s*(\[PENDIENTE\])")
        if pattern.search(text):
            errors.append(f"  [FAIL] INDEX.md — field '{field}' is [PENDIENTE]")

    # Check execution_mode value
    mode_match = re.search(r"\|\s*execution_mode\s*\|\s*([^\|\n]+)\s*\|", text)
    if mode_match:
        mode = mode_match.group(1).strip()
        if mode not in _VALID_EXECUTION_MODES:
            errors.append(
                f"  [FAIL] INDEX.md — execution_mode '{mode}' is not a valid value "
                f"(valid: {', '.join(sorted(_VALID_EXECUTION_MODES))})"
            )

    # Check compliance_scope value
    scope_match = re.search(r"\|\s*compliance_scope\s*\|\s*([^\|\n]+)\s*\|", text)
    if scope_match:
        scope = scope_match.group(1).strip()
        if scope not in _VALID_COMPLIANCE_SCOPES:
            errors.append(
                f"  [FAIL] INDEX.md — compliance_scope '{scope}' is not a valid value "
                f"(valid: {', '.join(sorted(_VALID_COMPLIANCE_SCOPES))})"
            )

    return errors


@click.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--cross-refs/--no-cross-refs", default=True, help="Run cross-reference check.")
@click.option("--index/--no-index", default=True, help="Run INDEX.md completeness check.")
@click.option("--dry-run", is_flag=True, default=False, help="Report issues but always exit 0 (preview mode).")
def validate(path: str, cross_refs: bool, index: bool, dry_run: bool) -> None:
    """Validate PIV/OAC framework specs in PATH (default: current directory).

    Checks:
      1. Cross-reference integrity — all referenced .md files exist on disk
      2. specs/active/INDEX.md — no [PENDIENTE] in required fields, valid mode/scope

    Exits with code 1 if any check fails (unless --dry-run is set).
    """
    root = Path(path).resolve()
    total_failures = 0

    # ── Check 1: cross-references ───────────────────────────────────────────
    if cross_refs:
        click.echo("Check 1 — Cross-Reference Integrity:")
        errors = _check_cross_references(root)
        if errors:
            for e in errors:
                click.echo(e)
            click.echo(f"  Result: FAIL ({len(errors)} broken references)")
            total_failures += len(errors)
        else:
            click.echo("  [OK]  All cross-references valid")

    # ── Check 2: INDEX.md completeness ──────────────────────────────────────
    if index:
        click.echo("Check 2 — specs/active/INDEX.md Completeness:")
        index_path = root / "specs" / "active" / "INDEX.md"
        errors = _check_index(index_path)
        if errors:
            for e in errors:
                click.echo(e)
            click.echo(f"  Result: FAIL ({len(errors)} issues)")
            total_failures += len(errors)
        else:
            click.echo("  [OK]  INDEX.md is complete and valid")

    # ── Summary ─────────────────────────────────────────────────────────────
    click.echo("")
    if total_failures == 0:
        click.echo("PASS: All checks passed.")
    else:
        if dry_run:
            click.echo(f"DRY-RUN: {total_failures} issue(s) found (exit 0 — dry-run mode).")
        else:
            click.echo(f"FAIL: {total_failures} issue(s) found. Fix before proceeding.")
            sys.exit(1)
