# Contributing to piv-oac

Thank you for your interest in contributing. This document covers the development workflow, coding standards, and how to submit changes.

---

## Setup

```bash
git clone https://github.com/DavidCaastro/lab.git
cd lab/sdk
pip install -e ".[dev]"
```

---

## Running Tests

```bash
# All tests
python -m pytest

# With coverage report
python -m pytest --cov=piv_oac --cov-report=term-missing

# Single file
python -m pytest tests/test_agents.py -v
```

Coverage must stay ≥ 80%. The CI gate will fail otherwise.

---

## Type Checking

```bash
python -m mypy piv_oac/
```

All public functions in `piv_oac/` must have type annotations. Tests are excluded from mypy.

---

## Code Style

```bash
# Lint + format check
python -m ruff check piv_oac/ tests/
python -m ruff format --check piv_oac/ tests/

# Auto-fix
python -m ruff format piv_oac/ tests/
```

Line length: 100. Target: Python 3.11+.

---

## Branch Conventions

| Branch type | Naming | From |
|-------------|--------|------|
| Bug fix | `fix/<short-description>` | `agent-configs` |
| Feature | `feature/<short-description>` | `agent-configs` |
| Release | `sdk-v*.*.*` tag on `main` | — |

**Never commit directly to `agent-configs` or `main`.**

---

## Pull Request Checklist

Before opening a PR, verify:

- [ ] All tests pass (`python -m pytest`)
- [ ] Coverage ≥ 80% (`python -m pytest --cov=piv_oac --cov-fail-under=80`)
- [ ] No mypy errors (`python -m mypy piv_oac/`)
- [ ] No ruff errors (`python -m ruff check piv_oac/ tests/`)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] New public functions have docstrings and type annotations

---

## Agent Contract Rules

When adding or modifying agents:

1. Every agent must inherit from `AgentBase`
2. `agent_type` class variable must be set (canonical string, e.g. `"SecurityAgent"`)
3. `_required_output_fields()` must list all fields the agent's contract requires
4. Required fields must match the naming defined in `skills/agent-contracts.md`
5. Gate-rejection logic must raise `GateRejectedError`, not return a boolean
6. Veto logic must raise `VetoError` with a plain-text reason

---

## Reporting Issues

Open an issue on GitHub with:
- Python version
- `piv-oac` version (`pip show piv-oac`)
- Minimal reproducer
- Expected vs actual behavior
