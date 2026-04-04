"""
ExecutionDataFilter — strips non-execution data before passing arguments to scripts.

Enforces that only task-execution-relevant data (task IDs, branch names, file paths
within the project) reaches local scripts. Blocks credentials, PII, secrets,
shell injection patterns, and paths outside the allowed base directory.
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Patterns that signal sensitive / non-execution data
# ---------------------------------------------------------------------------

_CREDENTIAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token|credential|bearer|auth)[=:\s]\S+"),
    re.compile(r"sk-[A-Za-z0-9\-_]{20,}"),          # Anthropic / OpenAI key pattern
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),             # AWS access key
    re.compile(r"(?i)ghp_[A-Za-z0-9]{36}"),          # GitHub personal token
]

_SHELL_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"[;&|`$]"),                           # common injection chars
    re.compile(r"\$\("),                              # command substitution
    re.compile(r"\.\./"),                             # path traversal up
    re.compile(r"//"),                                # double slash
]

_ALLOWED_ARG_RE = re.compile(r"^[A-Za-z0-9_\-./: ]+$")  # safe argument chars


class FilteredValue:
    """Wraps a validated argument value."""

    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value


class ExecutionDataFilter:
    """
    Validates and sanitizes arguments before they are passed to local scripts.

    Rules applied (in order):
    1. Reject any argument matching credential patterns.
    2. Reject any argument containing shell injection characters.
    3. Reject file paths outside *base_dir* (path traversal protection).
    4. Reject arguments with characters outside the safe allowlist.

    Parameters
    ----------
    base_dir:
        Root directory that all file path arguments must resolve within.
        Defaults to the current working directory.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = (base_dir or Path.cwd()).resolve()

    def validate(self, arg: str) -> FilteredValue:
        """
        Validate a single argument string.

        Parameters
        ----------
        arg:
            The argument to validate.

        Returns
        -------
        FilteredValue
            The validated (safe) value wrapped in FilteredValue.

        Raises
        ------
        ValueError
            If the argument fails any security check with a description of why.
        """
        self._check_credentials(arg)
        self._check_injection(arg)
        self._check_path_traversal(arg)
        self._check_allowlist(arg)
        return FilteredValue(arg)

    def validate_all(self, args: list[str]) -> list[FilteredValue]:
        """Validate a list of arguments, raising on the first violation."""
        return [self.validate(a) for a in args]

    # ------------------------------------------------------------------
    # Internal checks
    # ------------------------------------------------------------------

    def _check_credentials(self, arg: str) -> None:
        for pattern in _CREDENTIAL_PATTERNS:
            if pattern.search(arg):
                raise ValueError(
                    f"Argument rejected: credential pattern detected. "
                    f"Pass secrets via environment variables, never as arguments."
                )

    def _check_injection(self, arg: str) -> None:
        for pattern in _SHELL_INJECTION_PATTERNS:
            if pattern.search(arg):
                raise ValueError(
                    f"Argument rejected: shell injection pattern detected in: {arg!r}"
                )

    def _check_path_traversal(self, arg: str) -> None:
        """If the argument looks like a path, verify it stays within base_dir."""
        p = Path(arg)
        if p.is_absolute() or "/" in arg or "\\" in arg:
            try:
                resolved = (self._base / arg).resolve()
                resolved.relative_to(self._base)
            except ValueError:
                raise ValueError(
                    f"Argument rejected: path {arg!r} escapes project boundary {self._base}"
                )

    def _check_allowlist(self, arg: str) -> None:
        if not _ALLOWED_ARG_RE.match(arg):
            raise ValueError(
                f"Argument rejected: contains disallowed characters in: {arg!r}. "
                f"Only alphanumerics, hyphens, underscores, dots, slashes, colons, "
                f"and spaces are permitted."
            )
