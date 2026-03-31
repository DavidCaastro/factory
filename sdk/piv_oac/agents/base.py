"""
PIV/OAC AgentBase — abstract base class for all PIV/OAC agents.

Contract enforcement follows skills/agent-contracts.md §3.3:
- Up to max_retries attempts when a MalformedOutputError is raised.
- After exhausting retries, escalates to AgentUnrecoverableError.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

import anthropic

from piv_oac.contracts.parser import ContractParser
from piv_oac.exceptions import AgentUnrecoverableError, MalformedOutputError
from piv_oac.telemetry import agent_span

logger = logging.getLogger(__name__)


class AgentBase(ABC):
    """
    Abstract base for all PIV/OAC agents.

    Subclasses must define:
    - ``agent_type`` class variable (canonical string, e.g. "SecurityAgent")
    - :meth:`_get_system_prompt` — returns the system prompt for the agent role
    - :meth:`_required_output_fields` — returns the list of required contract fields

    The :meth:`invoke` method handles the retry loop and contract parsing
    automatically.
    """

    agent_type: str  # must be set by each concrete subclass

    def __init__(self, client: anthropic.AsyncAnthropic, model: str) -> None:
        """
        Parameters
        ----------
        client:
            Async Anthropic client instance.
        model:
            Model identifier to use for completions (e.g. "claude-sonnet-4-6").
        """
        self._client = client
        self._model = model
        self._parser = ContractParser()

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Return the system prompt that defines this agent's role and behavior."""

    @abstractmethod
    def _required_output_fields(self) -> list[str]:
        """
        Return the list of field names that MUST appear in the agent's output.
        These must match the canonical fields defined in skills/agent-contracts.md.
        """

    # ------------------------------------------------------------------
    # Public invoke
    # ------------------------------------------------------------------

    async def invoke(
        self,
        prompt: str,
        max_retries: int = 2,
        objective_id: str = "unknown",
        timeout_seconds: float | None = None,
    ) -> dict[str, str]:
        """
        Send *prompt* to the model and parse the structured output contract.

        Implements the retry protocol from skills/agent-contracts.md §3.3:
        - On MalformedOutputError, retries up to *max_retries* times, including
          the missing fields in the follow-up message.
        - After exhausting retries, raises AgentUnrecoverableError.

        Opens an OpenTelemetry span for each invocation when telemetry is enabled
        (PIV_OAC_TELEMETRY_ENABLED=true). See skills/observability.md §2.

        Parameters
        ----------
        prompt:
            The user-turn message to send to the agent.
        max_retries:
            Maximum number of retry attempts after the first failure (default 2).
        objective_id:
            Identifier of the current objective — used as OTel span attribute.
        timeout_seconds:
            Optional wall-clock timeout for the entire invocation (all attempts
            combined). Defaults per skills/fault-recovery.md:
            - SpecialistAgent / concrete leaf agents: 300 s
            - Orchestrators (DomainOrchestrator, MasterOrchestrator): 600 s
            Pass ``None`` to disable timeout enforcement (not recommended in
            production).

        Returns
        -------
        dict[str, str]
            Parsed contract fields as returned by ContractParser.

        Raises
        ------
        AgentUnrecoverableError
            If the agent fails to produce valid output within the retry budget.
        asyncio.TimeoutError
            If *timeout_seconds* is set and the invocation exceeds it.
        VetoError
            Subclasses may raise this directly inside _get_system_prompt or by
            overriding invoke() — the base class does not inspect for veto fields.
        """
        with agent_span(
            agent_type=self.agent_type,
            model=self._model,
            objective_id=objective_id,
        ):
            coro = self._invoke_inner(prompt, max_retries)
            if timeout_seconds is not None:
                return await asyncio.wait_for(coro, timeout=timeout_seconds)
            return await coro

    async def _invoke_inner(self, prompt: str, max_retries: int) -> dict[str, str]:
        """Internal retry loop — called inside the OTel span."""
        messages: list[dict] = [{"role": "user", "content": prompt}]
        last_error: MalformedOutputError | None = None

        for attempt in range(max_retries + 1):
            if attempt > 0 and last_error is not None:
                # Build retry message referencing missing fields (§3.3)
                missing_str = ", ".join(last_error.missing_fields)
                retry_prompt = (
                    f"Your previous response was missing the following required "
                    f"contract fields: {missing_str}. "
                    f"Please regenerate your response and ensure every required "
                    f"field appears on its own line using the exact format: "
                    f"FIELD_NAME: value"
                )
                messages.append({"role": "assistant", "content": last_raw})
                messages.append({"role": "user", "content": retry_prompt})
                logger.warning(
                    "[%s] attempt %d/%d — retrying due to missing fields: %s",
                    self.agent_type,
                    attempt,
                    max_retries,
                    missing_str,
                )

            response = await self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=self._get_system_prompt(),
                messages=messages,
            )

            last_raw = self._extract_text(response)

            try:
                return self._parser.parse(
                    raw_output=last_raw,
                    required_fields=self._required_output_fields(),
                    agent_type=self.agent_type,
                )
            except MalformedOutputError as exc:
                last_error = exc
                logger.debug(
                    "[%s] MalformedOutputError on attempt %d: %s",
                    self.agent_type,
                    attempt,
                    exc,
                )

            # All retries exhausted
        raise AgentUnrecoverableError(
            agent_type=self.agent_type,
            failure_type="UNRECOVERABLE_MALFORMED",
            detail=(
                f"Missing fields after {max_retries} retries: "
                f"{', '.join(last_error.missing_fields if last_error else [])}"
            ),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(response: anthropic.types.Message) -> str:
        """Extract plain text from the first text content block of a response."""
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""
