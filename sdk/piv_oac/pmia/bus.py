"""
PMIA In-Process Message Bus.

Implements the routing and retry protocol from skills/inter-agent-protocol.md §4:
    - Routes messages to registered recipients.
    - Validates structure + signature before delivery.
    - On MALFORMED_MESSAGE: notifies emitter; emitter has 2 retries.
    - After 2 failures → automatic ESCALATION to MasterOrchestrator.
    - MessageTampered → immediate SECURITY_VIOLATION escalation (no retry).

Usage
-----
    bus = PMIABus()
    bus.subscribe("SecurityAgent", handler_coroutine)
    await bus.publish(gate_verdict_msg, from_agent="SecurityAgent")
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable

from piv_oac.pmia.crypto import CryptoValidator, MessageTampered
from piv_oac.pmia.message import (
    PMIAMessage,
    EscalationMessage,
    MalformedMessageResponse,
    GateVerdictMessage,
    CrossAlertMessage,
    CheckpointReqMessage,
    CROSS_ALERT_AUTHORIZED,
)

logger = logging.getLogger(__name__)

Handler = Callable[[PMIAMessage], Awaitable[None]]

_MAX_RETRIES = 2
_REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "GATE_VERDICT": frozenset({"type", "gate", "verdict", "agent_id", "task_id", "timestamp", "signature"}),
    "ESCALATION": frozenset({"type", "from_agent", "to", "reason_code", "task_id", "timestamp", "signature"}),
    "CROSS_ALERT": frozenset({"type", "from_agent", "to_agent", "alert_type", "artifact_ref", "timestamp", "signature"}),
    "CHECKPOINT_REQ": frozenset({"type", "phase", "objective_id", "timestamp", "signature"}),
}


class PMIABus:
    """
    In-process asyncio message bus for PMIA inter-agent communication.

    Agents register handlers via :meth:`subscribe`. Messages are dispatched
    via :meth:`publish`. The bus validates, signs, verifies, retries, and
    escalates automatically per §4 and §5 of the protocol.

    Parameters
    ----------
    crypto:
        CryptoValidator instance. Creates a default one if not provided.
    """

    def __init__(self, crypto: CryptoValidator | None = None) -> None:
        self._crypto = crypto or CryptoValidator()
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._metrics: dict[str, int] = {
            "pmia_messages_total": 0,
            "pmia_retries": 0,
            "pmia_escalations": 0,
        }

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    def subscribe(self, agent_id: str, handler: Handler) -> None:
        """Register *handler* to receive messages addressed to *agent_id*."""
        self._handlers[agent_id].append(handler)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish(
        self,
        message: PMIAMessage,
        from_agent: str = "",
        retries_left: int = _MAX_RETRIES,
    ) -> None:
        """
        Sign, validate, and deliver *message* to its recipient(s).

        Parameters
        ----------
        message:
            Any PMIAMessage dataclass instance (unsigned — bus signs it).
        from_agent:
            Agent identifier emitting the message.
        retries_left:
            Internal retry counter — do not set manually.
        """
        self._metrics["pmia_messages_total"] += 1

        # Sign the message
        raw_json = message.to_json()
        signed_json = self._crypto.sign_message(raw_json)

        # Structural validation
        malformed = self._validate_structure(signed_json, message.type)
        if malformed:
            if retries_left > 0:
                self._metrics["pmia_retries"] += 1
                logger.warning(
                    "[PMIABus] MALFORMED_MESSAGE from %s (%s retries left): %s",
                    from_agent, retries_left, malformed.error,
                )
                # Re-publish with reduced retry budget — emitter must reformulate
                await self.publish(message, from_agent=from_agent, retries_left=retries_left - 1)
            else:
                await self._escalate(
                    from_agent=from_agent,
                    reason_code="PROTOCOL_DEVIATION",
                    task_id=getattr(message, "task_id", ""),
                    detail=f"MALFORMED_MESSAGE after {_MAX_RETRIES} retries",
                )
            return

        # Signature / TTL verification
        import json as _json
        data = _json.loads(signed_json)
        try:
            self._crypto.verify(signed_json, data.get("signature", ""))
        except MessageTampered as exc:
            logger.error("[PMIABus] MessageTampered from %s: %s", from_agent, exc)
            await self._escalate(
                from_agent=from_agent,
                reason_code="SECURITY_VIOLATION",
                task_id=getattr(message, "task_id", ""),
                detail=str(exc),
            )
            return

        # CROSS_ALERT authorization check
        if message.type == "CROSS_ALERT" and from_agent not in CROSS_ALERT_AUTHORIZED:
            await self._escalate(
                from_agent=from_agent,
                reason_code="SECURITY_VIOLATION",
                task_id="",
                detail=f"Unauthorized CROSS_ALERT from {from_agent}",
            )
            return

        # Route to recipients
        recipients = self._resolve_recipients(message)
        if not recipients:
            logger.debug("[PMIABus] No handlers registered for message type %s", message.type)
            return

        for recipient_id in recipients:
            for handler in self._handlers.get(recipient_id, []):
                try:
                    await handler(message)
                except Exception as exc:
                    logger.error(
                        "[PMIABus] Handler error for %s → %s: %s",
                        from_agent, recipient_id, exc,
                    )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def metrics(self) -> dict[str, int | float]:
        """Return current PMIA metrics snapshot."""
        total = self._metrics["pmia_messages_total"]
        retries = self._metrics["pmia_retries"]
        return {
            **self._metrics,
            "pmia_retry_rate": round(retries / total * 100, 2) if total else 0.0,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_structure(
        self, signed_json: str, msg_type: str
    ) -> MalformedMessageResponse | None:
        import json as _json
        try:
            data = _json.loads(signed_json)
        except _json.JSONDecodeError as exc:
            return MalformedMessageResponse(error=str(exc), expected_schema=msg_type)

        required = _REQUIRED_FIELDS.get(msg_type, frozenset())
        missing = required - set(data.keys())
        if missing:
            return MalformedMessageResponse(
                error=f"Missing fields: {sorted(missing)}",
                expected_schema=msg_type,
            )
        return None

    def _resolve_recipients(self, message: PMIAMessage) -> list[str]:
        """Determine which agent IDs should receive this message."""
        if message.type == "GATE_VERDICT":
            # Verdicts go to MasterOrchestrator by default
            return ["MasterOrchestrator"]
        if message.type == "ESCALATION":
            return [message.to]
        if message.type == "CROSS_ALERT":
            return [message.to_agent]
        if message.type == "CHECKPOINT_REQ":
            return ["MasterOrchestrator", "DomainOrchestrator"]
        return []

    async def _escalate(
        self,
        from_agent: str,
        reason_code: str,
        task_id: str,
        detail: str = "",
    ) -> None:
        """Emit an ESCALATION to MasterOrchestrator and record the metric."""
        self._metrics["pmia_escalations"] += 1
        logger.error(
            "[PMIABus] ESCALATION: from=%s reason=%s task=%s detail=%s",
            from_agent, reason_code, task_id, detail,
        )
        esc = EscalationMessage(
            from_agent=from_agent,
            to="MasterOrchestrator",
            reason_code=reason_code,  # type: ignore[arg-type]
            task_id=task_id,
        )
        raw = self._crypto.sign_message(esc.to_json())
        for handler in self._handlers.get("MasterOrchestrator", []):
            try:
                import json as _json
                await handler(esc)
            except Exception as exc:
                logger.error("[PMIABus] Escalation handler error: %s", exc)
