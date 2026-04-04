"""
SafeLocalExecutor — lets agents delegate tasks to local scripts.

Offloads work from the LLM to the local machine through a strict allowlist
of pre-approved scripts. All arguments are filtered through ExecutionDataFilter
before execution to block credentials, PII, and shell injection.

Allowlisted scripts (defined in ALLOWED_COMMANDS):
    "worktree_init"    → tools/worktree-init.sh  (create / list / cleanup)
    "validate_specs"   → tools/validate-specs.py (JSON schema validation)
    "run_pytest"       → pytest with coverage (Gate 2b Fase 1 mandatory)

Usage
-----
    executor = SafeLocalExecutor(project_root=Path("."))
    result = await executor.run("worktree_init", ["create", "task-auth", "SpecialistAgent"])
    print(result.stdout)
    print(result.returncode)   # 0 = success

    # Gate 2b — run pytest before invoking StandardsAgent
    result = await executor.run("run_pytest", ["--cov=src"])
    if not result.success:
        # emit BLOQUEADO_POR_HERRAMIENTA — do NOT invoke StandardsAgent
        ...
    standards_prompt = f"pytest output:\\n{result.to_agent_summary()}"
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from piv_oac.tools.filter import ExecutionDataFilter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowlisted commands
# ---------------------------------------------------------------------------

_ALLOWED_COMMANDS: dict[str, list[str]] = {
    "worktree_init": ["bash", "tools/worktree-init.sh"],
    "validate_specs": ["python", "tools/validate-specs.py"],
    # Gate 2b — mandatory pytest before StandardsAgent LLM invocation
    # Extra args (e.g. "--cov=src") are appended and filtered before execution.
    "run_pytest": ["python", "-m", "pytest"],
}

_DEFAULT_TIMEOUT = 60.0   # seconds
_MAX_OUTPUT_BYTES = 32_768  # 32 KB — truncate large outputs before sending to LLM


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionResult:
    """Structured result of a local script execution."""

    command: str
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    truncated: bool = False

    @property
    def success(self) -> bool:
        return self.returncode == 0

    def to_agent_summary(self) -> str:
        """
        Return a compact summary safe to embed in an agent prompt.

        Includes command, exit code, and output — truncated to _MAX_OUTPUT_BYTES
        to avoid bloating the LLM context window.
        """
        status = "SUCCESS" if self.success else f"FAILED (exit {self.returncode})"
        trunc_note = " [OUTPUT TRUNCATED]" if self.truncated else ""
        return (
            f"LOCAL_EXEC: {self.command} {' '.join(self.args)}\n"
            f"STATUS: {status}{trunc_note}\n"
            f"STDOUT:\n{self.stdout}\n"
            f"STDERR:\n{self.stderr}"
        ).strip()


# ---------------------------------------------------------------------------
# SafeLocalExecutor
# ---------------------------------------------------------------------------

class SafeLocalExecutor:
    """
    Executes pre-approved local scripts on behalf of agents.

    Security guarantees:
    - Only commands in ALLOWED_COMMANDS may be invoked.
    - All arguments are validated by ExecutionDataFilter before execution.
    - Subprocess runs with a hard wall-clock timeout.
    - Output is truncated to MAX_OUTPUT_BYTES before returning to agents,
      preventing context pollution.
    - No shell=True — arguments are passed as a list, eliminating injection.

    Parameters
    ----------
    project_root:
        Root directory of the project. Used to locate tools/ scripts and
        as the base for path validation in ExecutionDataFilter.
    timeout:
        Wall-clock timeout per execution in seconds. Defaults to 60 s.
    """

    ALLOWED_COMMANDS = _ALLOWED_COMMANDS

    def __init__(
        self,
        project_root: Path | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._root = (project_root or Path.cwd()).resolve()
        self._timeout = timeout
        self._filter = ExecutionDataFilter(base_dir=self._root)

    async def run(self, command: str, args: list[str]) -> ExecutionResult:
        """
        Execute an allowlisted command with validated arguments.

        Parameters
        ----------
        command:
            One of the keys in ALLOWED_COMMANDS (e.g. "worktree_init").
        args:
            Arguments to pass to the script. Each is validated by
            ExecutionDataFilter before execution.

        Returns
        -------
        ExecutionResult
            Structured result including returncode, stdout, stderr.

        Raises
        ------
        ValueError
            If *command* is not in ALLOWED_COMMANDS or any argument fails
            the filter.
        asyncio.TimeoutError
            If the script exceeds *timeout* seconds.
        """
        if command not in _ALLOWED_COMMANDS:
            raise ValueError(
                f"Command '{command}' is not in the allowlist. "
                f"Allowed: {sorted(_ALLOWED_COMMANDS)}"
            )

        # Filter all arguments — raises ValueError on any violation
        filtered = self._filter.validate_all(args)
        clean_args = [f.value for f in filtered]

        base_cmd = _ALLOWED_COMMANDS[command]
        full_cmd = base_cmd + clean_args

        logger.info("[SafeLocalExecutor] Running: %s", " ".join(full_cmd))

        proc = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self._root),
        )

        try:
            raw_out, raw_err = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            logger.error(
                "[SafeLocalExecutor] Timeout after %.1fs: %s", self._timeout, command
            )
            raise

        stdout, truncated = self._truncate(raw_out.decode(errors="replace"))
        stderr, _ = self._truncate(raw_err.decode(errors="replace"))

        result = ExecutionResult(
            command=command,
            args=clean_args,
            returncode=proc.returncode or 0,
            stdout=stdout,
            stderr=stderr,
            truncated=truncated,
        )

        log_level = logging.INFO if result.success else logging.WARNING
        logger.log(
            log_level,
            "[SafeLocalExecutor] %s exit=%d",
            command, result.returncode,
        )
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _truncate(text: str) -> tuple[str, bool]:
        encoded = text.encode()
        if len(encoded) <= _MAX_OUTPUT_BYTES:
            return text, False
        truncated = encoded[:_MAX_OUTPUT_BYTES].decode(errors="replace")
        return truncated + "\n[... OUTPUT TRUNCATED ...]", True
