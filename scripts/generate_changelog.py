#!/usr/bin/env python3
"""
PIV/OAC Changelog Generator
Parses git log (conventional commits) and generates docs/CHANGELOG.md.

Usage:
    python scripts/generate_changelog.py              # regenerate full changelog
    python scripts/generate_changelog.py --since HEAD~10  # last 10 commits only (append)
    python scripts/generate_changelog.py --dry-run    # print to stdout without writing

Conventional commit format expected:
    type(scope): description
    Types: feat, fix, refactor, docs, test, chore, perf, ci, build, style

Exit codes:
    0 — success
    1 — git not available or no commits found
"""

import re
import sys
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

REPO_ROOT = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip())

# Use relative path to avoid encoding issues with special chars in absolute paths
CHANGELOG_PATH = Path("docs") / "CHANGELOG.md"

TYPE_LABELS = {
    "feat":     "Nuevas funcionalidades",
    "fix":      "Correcciones",
    "refactor": "Refactorizaciones",
    "docs":     "Documentación",
    "test":     "Tests",
    "perf":     "Rendimiento",
    "ci":       "CI/CD",
    "build":    "Build / Dependencias",
    "chore":    "Tareas internas",
    "style":    "Estilo de código",
    "other":    "Otros cambios",
}

TYPE_ORDER = list(TYPE_LABELS.keys())

# Conventional commit regex
CONV_COMMIT_RE = re.compile(
    r'^(?P<type>feat|fix|refactor|docs|test|perf|ci|build|chore|style)'
    r'(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<description>.+)$',
    re.IGNORECASE
)


# ── Git helpers ────────────────────────────────────────────────────────────────

def git_log(since: str | None = None) -> list[dict]:
    """Return parsed list of commits as dicts."""
    fmt = "%H%x1f%ai%x1f%s%x1f%an"
    cmd = ["git", "log", f"--format={fmt}", "--no-merges"]
    if since:
        cmd += [f"{since}..HEAD"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []

    commits = []
    for line in result.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) < 4:
            continue
        sha, date_str, subject, author = parts[:4]
        try:
            dt = datetime.fromisoformat(date_str.strip())
        except ValueError:
            dt = datetime.now(tz=timezone.utc)
        commits.append({
            "sha": sha[:8],
            "date": dt,
            "month": dt.strftime("%Y-%m"),
            "subject": subject.strip(),
            "author": author.strip(),
        })
    return commits


def parse_commit(commit: dict) -> dict:
    """Enrich a commit dict with conventional commit fields."""
    m = CONV_COMMIT_RE.match(commit["subject"])
    if m:
        commit["conv_type"] = m.group("type").lower()
        commit["conv_scope"] = m.group("scope") or ""
        commit["conv_breaking"] = bool(m.group("breaking"))
        commit["conv_description"] = m.group("description").strip()
    else:
        commit["conv_type"] = "other"
        commit["conv_scope"] = ""
        commit["conv_breaking"] = False
        commit["conv_description"] = commit["subject"]
    return commit


# ── Changelog generation ───────────────────────────────────────────────────────

def group_commits(commits: list[dict]) -> dict:
    """Group commits by month → type."""
    by_month: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for c in commits:
        by_month[c["month"]][c["conv_type"]].append(c)
    return by_month


def render_entry(commit: dict) -> str:
    scope = f"**{commit['conv_scope']}**: " if commit["conv_scope"] else ""
    breaking = " ⚠️ BREAKING" if commit["conv_breaking"] else ""
    return f"- {scope}{commit['conv_description']}{breaking} (`{commit['sha']}`)"


def render_changelog(by_month: dict, existing_header: str = "") -> str:
    lines = []
    lines.append("# CHANGELOG — PIV/OAC")
    lines.append("")
    lines.append("> Generado automáticamente por `scripts/generate_changelog.py`.")
    lines.append("> Basado en commits con formato [Conventional Commits](https://www.conventionalcommits.org/).")
    lines.append(f"> Última actualización: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for month in sorted(by_month.keys(), reverse=True):
        # Format month as readable string
        try:
            dt = datetime.strptime(month, "%Y-%m")
            month_label = dt.strftime("%B %Y").capitalize()
        except ValueError:
            month_label = month

        lines.append(f"## {month_label}")
        lines.append("")

        by_type = by_month[month]

        # Render by type in defined order
        for t in TYPE_ORDER:
            if t not in by_type:
                continue
            label = TYPE_LABELS[t]
            lines.append(f"### {label}")
            lines.append("")
            for c in sorted(by_type[t], key=lambda x: x["date"], reverse=True):
                lines.append(render_entry(c))
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    since = None
    for a in args:
        if a.startswith("--since="):
            since = a.split("=", 1)[1]
        elif a == "--since" and args.index(a) + 1 < len(args):
            since = args[args.index(a) + 1]

    print(f"[generate_changelog] Leyendo git log{' (since ' + since + ')' if since else ''}...")
    commits = git_log(since)
    if not commits:
        print("[generate_changelog] No se encontraron commits.")
        return 0

    commits = [parse_commit(c) for c in commits]
    by_month = group_commits(commits)

    content = render_changelog(by_month)

    if dry_run:
        print(content)
        return 0

    import os
    os.makedirs(str(CHANGELOG_PATH.parent), exist_ok=True)
    CHANGELOG_PATH.write_text(content, encoding="utf-8")
    print(f"[generate_changelog] OK: {CHANGELOG_PATH} actualizado "
          f"({len(commits)} commits, {len(by_month)} mes(es)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
