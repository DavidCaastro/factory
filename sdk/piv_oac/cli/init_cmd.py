"""
piv init — Bootstrap a new PIV/OAC project via the 7Q interview.

Reads templates from specs/_templates/ and generates specs/active/ with
the answers provided interactively. Unanswered questions are left as [PENDIENTE].
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import click

_TEMPLATES_SUBPATH = Path("specs") / "_templates"
_ACTIVE_SUBPATH = Path("specs") / "active"

# 7Q interview — maps question label to (INDEX.md field, prompt text)
_QUESTIONS: list[tuple[str, str]] = [
    ("Nombre", "Q1. Project name"),
    ("Stack principal", "Q2. Main technology stack (e.g. Python/FastAPI/PostgreSQL)"),
    ("Mercado objetivo", "Q3. Target market / intended users"),
    ("Tipo de producto", "Q4. Product type (e.g. API, CLI, web app, SDK)"),
    ("execution_mode", "Q5. Execution mode [DEVELOPMENT / RESEARCH / MIXED / INIT]"),
    ("compliance_scope", "Q6. Compliance scope [FULL / MINIMAL / NONE]"),
    ("Objetivo en curso", "Q7. First objective description (e.g. OBJ-001 — Build auth module)"),
]

_VALID_EXECUTION_MODES = {"DEVELOPMENT", "RESEARCH", "MIXED", "INIT"}
_VALID_COMPLIANCE_SCOPES = {"FULL", "MINIMAL", "NONE"}


def _find_root() -> Path:
    """Walk up from cwd to find the repo root (contains CLAUDE.md or .git)."""
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "CLAUDE.md").exists() or (candidate / ".git").exists():
            return candidate
    return cwd


def _apply_answers(text: str, answers: dict[str, str]) -> str:
    """Replace table row values in INDEX.md with user answers.

    Replaces any existing value (including [PENDIENTE] or defaults like INIT)
    in rows matching the field name.
    """
    import re

    for field, value in answers.items():
        if not value:
            continue  # Skip empty answers — leave template value as-is
        # Match table row: | FieldName | <any value> |
        pattern = re.compile(
            rf"(\|\s*{re.escape(field)}\s*\|\s*)([^\|]+?)(\s*\|)",
            re.IGNORECASE,
        )
        text = pattern.sub(rf"\g<1>{value}\3", text)
    return text


@click.command("init")
@click.option(
    "--answers",
    type=click.Path(exists=True),
    default=None,
    help="Path to a YAML file with pre-filled answers (for non-interactive use).",
)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Project root directory. Defaults to auto-detected repo root (contains CLAUDE.md/.git).",
)
def init(answers: str | None, root: str | None) -> None:
    """Bootstrap a PIV/OAC project: run the 7Q interview and generate specs/active/.

    Templates are read from specs/_templates/. Generated files are written to
    specs/active/ (which is gitignored in agent-configs by design).
    """
    root_path = Path(root).resolve() if root else _find_root()
    templates_dir = root_path / _TEMPLATES_SUBPATH
    active_dir = root_path / _ACTIVE_SUBPATH

    if not templates_dir.is_dir():
        click.echo(
            f"[ERROR] Templates directory not found at {templates_dir}. "
            "Are you running piv init from the PIV/OAC repo root? "
            "Use --root to specify the project root explicitly.",
            err=True,
        )
        sys.exit(1)

    if active_dir.exists() and any(active_dir.iterdir()):
        click.echo(f"specs/active/ already exists at {active_dir}.")
        if not click.confirm("Overwrite existing specs/active/?", default=False):
            click.echo("Aborted.")
            sys.exit(0)
        shutil.rmtree(active_dir)

    active_dir.mkdir(parents=True, exist_ok=True)

    # ── Load pre-filled answers if --answers given ───────────────────────────
    prefilled: dict[str, str] = {}
    if answers:
        import yaml  # type: ignore[import-untyped]

        with open(answers, encoding="utf-8") as f:
            prefilled = yaml.safe_load(f) or {}

    # ── Run interview ────────────────────────────────────────────────────────
    click.echo("\nPIV/OAC Project Bootstrap — 7Q Interview\n")
    collected: dict[str, str] = {}

    for field, prompt in _QUESTIONS:
        if field in prefilled:
            collected[field] = str(prefilled[field])
            click.echo(f"{prompt}: {collected[field]}  (pre-filled)")
            continue

        value = click.prompt(prompt, default="", show_default=False).strip()

        # Validate constrained fields
        if field == "execution_mode" and value and value.upper() not in _VALID_EXECUTION_MODES:
            click.echo(
                f"  [WARN] '{value}' is not a valid execution_mode. "
                f"Valid values: {', '.join(sorted(_VALID_EXECUTION_MODES))}. "
                "Leaving as [PENDIENTE]."
            )
            value = ""
        elif field == "compliance_scope" and value and value.upper() not in _VALID_COMPLIANCE_SCOPES:
            click.echo(
                f"  [WARN] '{value}' is not a valid compliance_scope. "
                f"Valid values: {', '.join(sorted(_VALID_COMPLIANCE_SCOPES))}. "
                "Leaving as [PENDIENTE]."
            )
            value = ""

        collected[field] = value.upper() if field in ("execution_mode", "compliance_scope") and value else value

    # ── Copy templates → active/ and apply answers ───────────────────────────
    template_files = ["INDEX.md", "functional.md", "architecture.md", "quality.md", "security.md", "compliance.md"]

    for filename in template_files:
        src = templates_dir / filename
        dst = active_dir / filename
        if not src.exists():
            click.echo(f"  [SKIP] Template {filename} not found in {templates_dir}")
            continue
        text = src.read_text(encoding="utf-8")
        text = _apply_answers(text, collected)
        dst.write_text(text, encoding="utf-8")

    # Also copy research.md template if present (for RESEARCH/MIXED modes)
    research_src = templates_dir / "research.md"
    if research_src.exists():
        research_dst = active_dir / "research.md"
        text = research_src.read_text(encoding="utf-8")
        text = _apply_answers(text, collected)
        research_dst.write_text(text, encoding="utf-8")

    click.echo(f"\nspecs/active/ generated at {active_dir}")
    click.echo("Next: review specs/active/INDEX.md and fill any remaining [PENDIENTE] fields.")
    click.echo("Then run: piv validate .")
