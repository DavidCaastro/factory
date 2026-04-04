"""
Tests for SafeLocalExecutor and ExecutionDataFilter.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from piv_oac.tools import SafeLocalExecutor, ExecutionResult, ExecutionDataFilter


# ---------------------------------------------------------------------------
# ExecutionDataFilter
# ---------------------------------------------------------------------------

class TestExecutionDataFilter:
    def setup_method(self):
        self.f = ExecutionDataFilter(base_dir=Path("/tmp/project"))

    def test_valid_task_id(self):
        result = self.f.validate("task-auth-module")
        assert str(result) == "task-auth-module"

    def test_valid_branch_name(self):
        result = self.f.validate("feature/payments")
        assert str(result) == "feature/payments"

    def test_rejects_api_key(self):
        with pytest.raises(ValueError, match="credential"):
            self.f.validate("api_key=sk-ant-abc123xyz")

    def test_rejects_openai_key_pattern(self):
        with pytest.raises(ValueError, match="credential"):
            self.f.validate("sk-" + "A" * 25)

    def test_rejects_shell_semicolon(self):
        with pytest.raises(ValueError, match="injection"):
            self.f.validate("task; rm -rf /")

    def test_rejects_pipe(self):
        with pytest.raises(ValueError, match="injection"):
            self.f.validate("task | cat /etc/passwd")

    def test_rejects_command_substitution(self):
        with pytest.raises(ValueError, match="injection"):
            self.f.validate("$(whoami)")

    def test_rejects_path_traversal(self):
        # ../ is caught by injection check (it contains the ../ pattern)
        with pytest.raises(ValueError):
            self.f.validate("../../etc/passwd")

    def test_rejects_disallowed_chars(self):
        with pytest.raises(ValueError, match="disallowed"):
            self.f.validate("task@name!")

    def test_validate_all_stops_on_first_violation(self):
        with pytest.raises(ValueError):
            self.f.validate_all(["valid-arg", "$(inject)", "another-valid"])


# ---------------------------------------------------------------------------
# SafeLocalExecutor
# ---------------------------------------------------------------------------

class TestSafeLocalExecutor:
    def test_disallowed_command_raises(self):
        executor = SafeLocalExecutor()
        with pytest.raises(ValueError, match="allowlist"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                executor.run("rm_everything", [])
            )

    @pytest.mark.asyncio
    async def test_disallowed_command_raises_async(self):
        executor = SafeLocalExecutor()
        with pytest.raises(ValueError, match="allowlist"):
            await executor.run("shell_exec", ["-c", "whoami"])

    @pytest.mark.asyncio
    async def test_argument_with_credential_rejected_before_execution(self):
        executor = SafeLocalExecutor()
        with pytest.raises(ValueError, match="credential"):
            await executor.run("worktree_init", ["create", "api_key=secret123"])

    @pytest.mark.asyncio
    async def test_argument_with_injection_rejected_before_execution(self):
        executor = SafeLocalExecutor()
        with pytest.raises(ValueError, match="injection"):
            await executor.run("worktree_init", ["create", "task; evil"])

    def test_allowed_commands_defined(self):
        assert "worktree_init" in SafeLocalExecutor.ALLOWED_COMMANDS
        assert "validate_specs" in SafeLocalExecutor.ALLOWED_COMMANDS
        assert "run_pytest" in SafeLocalExecutor.ALLOWED_COMMANDS

    def test_execution_result_success_property(self):
        result = ExecutionResult(
            command="worktree_init",
            args=["create", "task-x", "SpecialistAgent"],
            returncode=0,
            stdout="Worktree created",
            stderr="",
        )
        assert result.success is True

    def test_execution_result_failure_property(self):
        result = ExecutionResult(
            command="worktree_init",
            args=["create", "task-x", "SpecialistAgent"],
            returncode=1,
            stdout="",
            stderr="Error: branch already exists",
        )
        assert result.success is False

    def test_to_agent_summary_success(self):
        result = ExecutionResult(
            command="worktree_init",
            args=["list"],
            returncode=0,
            stdout="task-auth/SpecialistAgent",
            stderr="",
        )
        summary = result.to_agent_summary()
        assert "SUCCESS" in summary
        assert "task-auth" in summary
        assert "STDOUT" in summary

    def test_to_agent_summary_failure(self):
        result = ExecutionResult(
            command="validate_specs",
            args=[],
            returncode=1,
            stdout="",
            stderr="Schema validation failed",
        )
        summary = result.to_agent_summary()
        assert "FAILED" in summary
        assert "exit 1" in summary

    def test_to_agent_summary_truncated(self):
        result = ExecutionResult(
            command="worktree_init",
            args=["list"],
            returncode=0,
            stdout="output",
            stderr="",
            truncated=True,
        )
        summary = result.to_agent_summary()
        assert "TRUNCATED" in summary

    @pytest.mark.asyncio
    async def test_simple_echo_execution(self):
        """Run a real subprocess (echo) to verify the execution path works."""
        import sys
        executor = SafeLocalExecutor()
        # Temporarily add 'echo_test' to the allowlist for this test
        original = dict(executor.ALLOWED_COMMANDS)
        SafeLocalExecutor.ALLOWED_COMMANDS["echo_test"] = [
            sys.executable, "-c", "import sys; print('hello')"
        ]
        try:
            result = await executor.run("echo_test", [])
            assert result.returncode == 0
            assert "hello" in result.stdout
        finally:
            SafeLocalExecutor.ALLOWED_COMMANDS.clear()
            SafeLocalExecutor.ALLOWED_COMMANDS.update(original)
