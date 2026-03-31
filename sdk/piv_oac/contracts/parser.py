"""
PIV/OAC ContractParser — extracts structured output fields from agent responses.

Contract format (skills/agent-contracts.md §3.1):

    FIELD_NAME: value

Extraction regex (§3.2):

    ^FIELD_NAME:\\s+(.+)$

Fields defined per agent type (§3.4):

    SecurityAgent    : VERDICT, RISK_LEVEL, FINDINGS
    AuditAgent       : AUDIT_RESULT, RF_COVERAGE, SCOPE_VIOLATIONS, ENGRAM_WRITE
    CoherenceAgent   : COHERENCE_STATUS, GATE1_VERDICT, CONFLICTS
    MasterOrchestrator: CLASSIFICATION, BUDGET_ESTIMATE_TOKENS_TOTAL_EST,
                        BUDGET_ESTIMATE_USD_EST, BUDGET_ESTIMATE_MODEL_DISTRIBUTION,
                        spec_validated
    DomainOrchestrator: DO_TYPE, PLAN, DEPENDENCIES
    SpecialistAgent  : IMPLEMENTATION, FILES_CHANGED, TESTS_ADDED, RF_ADDRESSED
"""

from __future__ import annotations

import re
from typing import Final

from piv_oac.exceptions import MalformedOutputError

# ---------------------------------------------------------------------------
# Canonical required-field sets (keyed by agent_type string)
# ---------------------------------------------------------------------------

AGENT_REQUIRED_FIELDS: Final[dict[str, list[str]]] = {
    "SecurityAgent": ["VERDICT", "RISK_LEVEL", "FINDINGS"],
    "AuditAgent": ["AUDIT_RESULT", "RF_COVERAGE", "SCOPE_VIOLATIONS", "ENGRAM_WRITE"],
    "CoherenceAgent": ["COHERENCE_STATUS", "GATE1_VERDICT", "CONFLICTS"],
    "MasterOrchestrator": [
        "CLASSIFICATION",
        "BUDGET_ESTIMATE_TOKENS_TOTAL_EST",
        "BUDGET_ESTIMATE_USD_EST",
        "BUDGET_ESTIMATE_MODEL_DISTRIBUTION",
        "spec_validated",
    ],
    "DomainOrchestrator": ["DO_TYPE", "PLAN", "DEPENDENCIES"],
    "SpecialistAgent": ["IMPLEMENTATION", "FILES_CHANGED", "TESTS_ADDED", "RF_ADDRESSED"],
}


class ContractParser:
    """
    Parses the structured output block of a PIV/OAC agent response.

    Usage::

        parser = ContractParser()
        fields = parser.parse(raw_output, required_fields=["VERDICT", "RISK_LEVEL", "FINDINGS"])
        verdict = fields["VERDICT"]   # "APPROVED" | "REJECTED" | "CONDITIONAL_APPROVED"

    The parser is stateless; a single instance can be reused across calls.
    """

    # Compiled pattern cache: field_name -> compiled regex
    _pattern_cache: dict[str, re.Pattern[str]] = {}

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def parse(
        self,
        raw_output: str,
        required_fields: list[str],
        agent_type: str = "UnknownAgent",
    ) -> dict[str, str]:
        """
        Extract *required_fields* from *raw_output*.

        Parameters
        ----------
        raw_output:
            The full text returned by the agent (may include free-form reasoning
            before/after the contract block).
        required_fields:
            The field names that MUST appear in the output.  Any missing field
            triggers a ``MalformedOutputError``.
        agent_type:
            Used only for error reporting.

        Returns
        -------
        dict[str, str]
            Mapping of field name → extracted value string.

        Raises
        ------
        MalformedOutputError
            If one or more required fields are absent from *raw_output*.
        """
        extracted: dict[str, str] = {}
        missing: list[str] = []

        for field in required_fields:
            pattern = self._get_pattern(field)
            match = pattern.search(raw_output)
            if match:
                extracted[field] = match.group(1).strip()
            else:
                missing.append(field)

        if missing:
            raise MalformedOutputError(
                agent_type=agent_type,
                raw_output=raw_output,
                missing_fields=missing,
            )

        return extracted

    def parse_for_agent(self, raw_output: str, agent_type: str) -> dict[str, str]:
        """
        Convenience wrapper that looks up the canonical required fields for
        *agent_type* and delegates to :meth:`parse`.

        Raises
        ------
        ValueError
            If *agent_type* is not registered in ``AGENT_REQUIRED_FIELDS``.
        MalformedOutputError
            If required fields are missing.
        """
        if agent_type not in AGENT_REQUIRED_FIELDS:
            raise ValueError(
                f"Unknown agent_type '{agent_type}'. "
                f"Registered types: {list(AGENT_REQUIRED_FIELDS)}"
            )
        return self.parse(
            raw_output,
            required_fields=AGENT_REQUIRED_FIELDS[agent_type],
            agent_type=agent_type,
        )

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    @classmethod
    def _get_pattern(cls, field_name: str) -> re.Pattern[str]:
        """Return a compiled regex for *field_name*, using a simple cache."""
        if field_name not in cls._pattern_cache:
            # Escape the field name in case it contains regex metacharacters
            escaped = re.escape(field_name)
            cls._pattern_cache[field_name] = re.compile(
                rf"^{escaped}:\s+(.+)$", re.MULTILINE
            )
        return cls._pattern_cache[field_name]
