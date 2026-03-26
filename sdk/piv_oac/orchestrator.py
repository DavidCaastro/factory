"""
PIV/OAC MasterOrchestrator — top-level pipeline client.

The MasterOrchestrator coordinates the full PIV/OAC pipeline:
1. Validates the incoming request against spec schemas (G-06).
2. Dispatches the request through SecurityAgent → CoherenceAgent → execution DAG.
3. Delegates audit to AuditAgent at the end of the pipeline.

Contract emitted on normal dispatch (skills/agent-contracts.md §1.1):

    CLASSIFICATION: NIVEL_1 | NIVEL_2
    BUDGET_ESTIMATE_TOKENS_TOTAL_EST: <integer>
    BUDGET_ESTIMATE_USD_EST: <float>
    BUDGET_ESTIMATE_MODEL_DISTRIBUTION: <json object>
    spec_validated: true | false

On malicious intent detection:

    VETO_INTENCION: <reason>
"""

from __future__ import annotations

import logging
import re

import anthropic

from piv_oac.agents.audit import AuditAgent
from piv_oac.agents.coherence import CoherenceAgent
from piv_oac.agents.security import SecurityAgent
from piv_oac.contracts.parser import ContractParser
from piv_oac.exceptions import AgentUnrecoverableError, MalformedOutputError, VetoError

logger = logging.getLogger(__name__)

_VETO_INTENCION_PATTERN = re.compile(r"^VETO_INTENCION:\s+(.+)$", re.MULTILINE)

_MO_REQUIRED_FIELDS = [
    "CLASSIFICATION",
    "BUDGET_ESTIMATE_TOKENS_TOTAL_EST",
    "BUDGET_ESTIMATE_USD_EST",
    "BUDGET_ESTIMATE_MODEL_DISTRIBUTION",
    "spec_validated",
]


class MasterOrchestrator:
    """
    Top-level orchestrator for the PIV/OAC pipeline.

    Parameters
    ----------
    client:
        Async Anthropic client.
    model:
        Default model for the orchestrator itself.  Agents may use different
        models if constructed separately.
    max_retries:
        Default retry budget forwarded to each agent invocation.
    """

    agent_type = "MasterOrchestrator"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-sonnet-4-6",
        max_retries: int = 2,
    ) -> None:
        self._client = client
        self._model = model
        self._max_retries = max_retries
        self._parser = ContractParser()

        # Sub-agents (can be replaced by callers for testing)
        self.security_agent = SecurityAgent(client=client, model=model)
        self.coherence_agent = CoherenceAgent(client=client, model=model)
        self.audit_agent = AuditAgent(client=client, model=model)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def dispatch(self, task: str) -> dict[str, str]:
        """
        Entry point for the PIV/OAC pipeline.

        Steps:
        1. Send the task to the MasterOrchestrator model to produce a
           CLASSIFICATION + DAG response.
        2. Check for VETO_INTENCION in the raw response.
        3. Parse and return the structured contract fields.

        Parameters
        ----------
        task:
            Free-text task description from the user.

        Returns
        -------
        dict[str, str]
            Parsed orchestrator contract fields.

        Raises
        ------
        VetoError
            If VETO_INTENCION is detected.
        AgentUnrecoverableError
            If structured output cannot be parsed after retries.
        """
        system_prompt = self._get_system_prompt()
        messages = [{"role": "user", "content": task}]
        last_error: MalformedOutputError | None = None
        last_raw: str = ""

        for attempt in range(self._max_retries + 1):
            if attempt > 0 and last_error is not None:
                missing_str = ", ".join(last_error.missing_fields)
                messages.append({"role": "assistant", "content": last_raw})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your previous response was missing the following required "
                            f"contract fields: {missing_str}. Please regenerate your "
                            f"response with all required fields present."
                        ),
                    }
                )

            response = await self._client.messages.create(
                model=self._model,
                max_tokens=8192,
                system=system_prompt,
                messages=messages,
            )

            last_raw = ""
            for block in response.content:
                if hasattr(block, "text"):
                    last_raw = block.text
                    break

            # Check for hard veto before parsing contract fields
            veto_match = _VETO_INTENCION_PATTERN.search(last_raw)
            if veto_match:
                raise VetoError(
                    agent_type=self.agent_type,
                    reason=veto_match.group(1).strip(),
                )

            try:
                return self._parser.parse(
                    raw_output=last_raw,
                    required_fields=_MO_REQUIRED_FIELDS,
                    agent_type=self.agent_type,
                )
            except MalformedOutputError as exc:
                last_error = exc
                logger.warning(
                    "[MasterOrchestrator] attempt %d/%d — missing fields: %s",
                    attempt,
                    self._max_retries,
                    exc.missing_fields,
                )

        raise AgentUnrecoverableError(
            agent_type=self.agent_type,
            failure_type="UNRECOVERABLE_MALFORMED",
            detail=(
                f"Missing fields after {self._max_retries} retries: "
                f"{', '.join(last_error.missing_fields if last_error else [])}"
            ),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_system_prompt(self) -> str:
        return (
            "You are the MasterOrchestrator of the PIV/OAC framework. "
            "Your responsibilities:\n"
            "1. Classify the incoming task (NIVEL_1 = simple, NIVEL_2 = complex).\n"
            "2. Estimate the token and USD budget for the execution pipeline.\n"
            "3. Validate that the task conforms to the spec schemas (G-06).\n"
            "4. If the task describes malicious intent, emit VETO_INTENCION and halt.\n"
            "5. Otherwise, produce an execution DAG in YAML.\n\n"
            "You MUST emit the following structured contract block:\n\n"
            "CLASSIFICATION: NIVEL_1 | NIVEL_2\n"
            "BUDGET_ESTIMATE_TOKENS_TOTAL_EST: <integer>\n"
            "BUDGET_ESTIMATE_USD_EST: <float>\n"
            "BUDGET_ESTIMATE_MODEL_DISTRIBUTION: <json object>\n"
            "spec_validated: true | false\n\n"
            "Then append a YAML code block with the execution DAG.\n"
            "If malicious intent is detected, emit only:\n"
            "VETO_INTENCION: <reason>\n\n"
            "All field names and enumeration values must be in English."
        )
