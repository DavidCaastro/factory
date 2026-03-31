"""Environment validation script — PIV/OAC pre-flight check.

Verifies that all tools required by Gate 2b (SecurityAgent) and Gate 2
(StandardsAgent) are available and functional before the framework creates
any agents. Run this before starting a Nivel 2 objective.

Exit codes:
  0 — all required tools available
  1 — one or more required tools missing or broken
"""

import subprocess
import sys
import shutil

REQUIRED = [
    ("ruff",       ["ruff", "--version"],                    "pip install ruff"),
    ("pytest",     ["pytest", "--version"],                  "pip install pytest"),
    ("pytest-cov", ["python", "-c", "import pytest_cov; print(pytest_cov.__version__)"], "pip install pytest-cov"),
]

SECURITY_REQUIRED = [
    ("grep",       ["grep", "--version"],                    "built-in (install git-for-windows on Windows)"),
]

CONDITIONAL = [
    ("pip-audit",  ["pip-audit", "--version"],               "pip install pip-audit"),
]

WIDTH = 60


def check(name: str, cmd: list[str]) -> tuple[bool, str]:
    if shutil.which(cmd[0]) is None:
        return False, "NOT FOUND in PATH"
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            timeout=15,
            env={**__import__("os").environ, "PYTHONUTF8": "1"},
        )
        if r.returncode != 0:
            return False, f"EXIT {r.returncode}"
        first_line = (r.stdout or r.stderr or b"").decode("utf-8", errors="replace").splitlines()
        return True, first_line[0] if first_line else "ok"
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)


def section(title: str, tools: list) -> list[str]:
    failures = []
    print(f"\n{'─' * WIDTH}")
    print(f"  {title}")
    print(f"{'─' * WIDTH}")
    for name, cmd, install in tools:
        ok, msg = check(name, cmd)
        status = "✓" if ok else "✗"
        print(f"  [{status}] {name:<20} {msg}")
        if not ok:
            print(f"        → Install: {install}")
            failures.append(name)
    return failures


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"\n{'═' * WIDTH}")
    print("  PIV/OAC Environment Validation")
    print(f"  Python {sys.version.split()[0]}")
    print(f"{'═' * WIDTH}")

    required_failures  = section("Required tools (gate blockers)", REQUIRED)
    security_failures  = section("Security tools (Gate 2b)", SECURITY_REQUIRED)
    conditional_issues = section("Conditional tools (pip-audit — MINIMAL/FULL scope)", CONDITIONAL)

    print(f"\n{'═' * WIDTH}")
    total_blocking = len(required_failures) + len(security_failures)

    if total_blocking == 0 and not conditional_issues:
        print("  RESULT: ALL TOOLS AVAILABLE — ready to start Nivel 2 objective")
    elif total_blocking == 0 and conditional_issues:
        print("  RESULT: CONDITIONAL WARNING")
        print(f"  pip-audit unavailable. Gates will emit BLOQUEADO_POR_HERRAMIENTA")
        print(f"  if compliance_scope is MINIMAL or FULL.")
        print(f"  Workaround: set PYTHONUTF8=1 before running pip-audit,")
        print(f"  or use: pip install pip-audit --upgrade")
    else:
        print(f"  RESULT: BLOCKED — {total_blocking} required tool(s) missing")
        print(f"  Fix all required tools before starting a Nivel 2 objective.")
    print(f"{'═' * WIDTH}\n")

    return 1 if total_blocking > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
