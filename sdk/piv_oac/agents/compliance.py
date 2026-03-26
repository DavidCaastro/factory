"""
PIV/OAC ComplianceAgent — evaluates legal and regulatory implications.

The ComplianceAgent acts at:
- FASE 1 (via MasterOrchestrator): initial compliance evaluation of the objective.
- Gate 3 (staging → main): final compliance check of the complete product.
- FASE 8 (closure): generates the compliance report and Delivery Package.

MANDATORY DISCLAIMER: The ComplianceAgent generates checklists against known
published standards (GDPR, CCPA, HIPAA, OWASP, etc.). It NEVER affirms or
guarantees legal compliance. Every report includes an explicit disclaimer
requiring review by a qualified legal professional.

Contract emitted on every review:

    COMPLIANCE_VERDICT: APPROVED | REJECTED | MITIGATION_REQUIRED
    RISK_CATEGORIES: <comma-separated categories, or NONE>
    MITIGATION_REQUIRED: YES | NO
    DISCLAIMER: HUMAN_REVIEW_REQUIRED
"""

from __future__ import annotations

import anthropic

from piv_oac.exceptions import GateRejectedError

from .base import AgentBase

# Mandatory disclaimer text — must appear in every compliance report.
COMPLIANCE_DISCLAIMER = (
    "DISCLAIMER: This report was generated automatically by ComplianceAgent. "
    "It checks against known published standards but does NOT constitute legal advice "
    "and does NOT guarantee regulatory compliance. A qualified legal professional "
    "must review this report before any production deployment."
)


class ComplianceAgent(AgentBase):
    """
    Superagent that evaluates legal, ethical, and regulatory implications of
    the product being built.

    ComplianceAgent is conditionally present in the control environment:
    - compliance_scope == "FULL" or "MINIMAL" → active
    - compliance_scope == "NONE" → not instantiated

    Evaluation categories (skills/compliance.md):
    1. Personal data protection (GDPR, CCPA, LGPD)
    2. Information security (ISO 27001, SOC 2, OWASP ASVS)
    3. Accessibility if applicable (WCAG)
    4. Export restrictions or dual-use if applicable
    5. Dependency licenses (compatibility with product license)

    If a risk cannot be mitigated with code, ComplianceAgent generates a
    Mitigation Document that blocks Gate 3 until the user acknowledges it.

    Parameters
    ----------
    client:
        Async Anthropic client.
    model:
        Model to use (default: claude-sonnet-4-6 per CLAUDE.md assignment table).
    compliance_scope:
        One of "FULL", "MINIMAL", or "NONE". Affects how exhaustive the
        evaluation is. "NONE" should not be passed — the agent should not be
        instantiated in that case.
    """

    agent_type = "ComplianceAgent"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str = "claude-sonnet-4-6",
        compliance_scope: str = "MINIMAL",
    ) -> None:
        if compliance_scope == "NONE":
            raise ValueError(
                "ComplianceAgent must not be instantiated when compliance_scope is NONE. "
                "Check the activation table in CLAUDE.md FASE 2."
            )
        super().__init__(client, model)
        self._compliance_scope = compliance_scope

    # ------------------------------------------------------------------
    # AgentBase interface
    # ------------------------------------------------------------------

    def _get_system_prompt(self) -> str:
        scope_instruction = (
            "Perform a thorough evaluation across all five compliance categories."
            if self._compliance_scope == "FULL"
            else "Perform a focused evaluation on the highest-risk categories for this product type."
        )
        return (
            "You are a ComplianceAgent operating within the PIV/OAC framework. "
            "Your role is to evaluate the legal, ethical, and regulatory implications "
            "of the product or changes being reviewed.\n\n"
            f"Compliance scope: {self._compliance_scope}. {scope_instruction}\n\n"
            "Evaluation categories:\n"
            "1. Personal data protection (GDPR Art. relevant, CCPA, LGPD)\n"
            "2. Information security (ISO 27001, SOC 2, OWASP ASVS)\n"
            "3. Accessibility if applicable (WCAG)\n"
            "4. Export restrictions or dual-use if applicable\n"
            "5. Dependency licenses (compatibility with product license)\n\n"
            "CRITICAL RULES:\n"
            "- You NEVER affirm or guarantee legal compliance.\n"
            "- Every response MUST include the mandatory disclaimer.\n"
            "- If a risk cannot be mitigated with code, set MITIGATION_REQUIRED: YES.\n"
            "- MITIGATION_REQUIRED: YES blocks Gate 3 until the user acknowledges.\n\n"
            "You MUST end every response with the following structured contract block:\n\n"
            "COMPLIANCE_VERDICT: APPROVED | REJECTED | MITIGATION_REQUIRED\n"
            "RISK_CATEGORIES: <comma-separated list of affected categories, or NONE>\n"
            "MITIGATION_REQUIRED: YES | NO\n"
            "DISCLAIMER: HUMAN_REVIEW_REQUIRED\n\n"
            "All field names and enumeration values must be in English."
        )

    def _required_output_fields(self) -> list[str]:
        return [
            "COMPLIANCE_VERDICT",
            "RISK_CATEGORIES",
            "MITIGATION_REQUIRED",
            "DISCLAIMER",
        ]

    async def invoke(self, prompt: str, max_retries: int = 2, **kwargs) -> dict[str, str]:
        """
        Invoke the compliance evaluation.

        Raises GateRejectedError if COMPLIANCE_VERDICT is REJECTED.
        When MITIGATION_REQUIRED is YES, the verdict is MITIGATION_REQUIRED
        (not REJECTED) — callers must present the mitigation document to the
        user and set mitigation_acknowledged=true in the checkpoint before
        Gate 3 can proceed.

        Raises
        ------
        GateRejectedError
            If COMPLIANCE_VERDICT is REJECTED (not MITIGATION_REQUIRED).
        AgentUnrecoverableError
            If the agent fails to produce valid output within the retry budget.
        """
        fields = await super().invoke(prompt, max_retries=max_retries, **kwargs)
        if fields.get("COMPLIANCE_VERDICT") == "REJECTED":
            risk_cats = fields.get("RISK_CATEGORIES", "no details")
            raise GateRejectedError(gate="Gate-3-Compliance", findings=[risk_cats])
        return fields

    @property
    def disclaimer(self) -> str:
        """Return the mandatory compliance disclaimer text."""
        return COMPLIANCE_DISCLAIMER
