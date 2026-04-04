"""
GateCircuitBreaker — prevents runaway LLM cost on persistent gate rejections.

Tracks rejection counts per gate.  When a gate accumulates MAX_GATE_REJECTIONS
consecutive rejections, the circuit opens, all further attempts for that gate
raise CircuitOpenError immediately, and an EscalationMessage(MAX_REJECTIONS) is
emitted via PMIABus so MasterOrchestrator can surface the incident.

Usage
-----
    from piv_oac.circuit_breaker import GateCircuitBreaker, MAX_GATE_REJECTIONS

    breaker = GateCircuitBreaker()

    # After each gate rejection:
    await breaker.record_rejection("gate_0", task_id="T-01")  # counts 1, 2, 3...
    # On the 3rd call: emits ESCALATION + raises CircuitOpenError

    # After a fix:
    breaker.reset("gate_0")
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from piv_oac.exceptions import CircuitOpenError

if TYPE_CHECKING:
    from piv_oac.pmia.bus import PMIABus

logger = logging.getLogger(__name__)

MAX_GATE_REJECTIONS: int = 3


class GateCircuitBreaker:
    """
    Per-gate rejection counter with automatic escalation on threshold breach.

    Parameters
    ----------
    max_rejections:
        Number of consecutive rejections before a gate circuit opens.
        Defaults to MAX_GATE_REJECTIONS (3).
    bus:
        Optional PMIABus.  When provided, an EscalationMessage with
        reason_code="MAX_REJECTIONS" is published to MasterOrchestrator
        the moment a circuit opens.
    """

    def __init__(
        self,
        max_rejections: int = MAX_GATE_REJECTIONS,
        bus: "PMIABus | None" = None,
    ) -> None:
        self._max = max_rejections
        self._bus = bus
        self._rejections: dict[str, int] = defaultdict(int)
        self._open: set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def record_rejection(self, gate: str, task_id: str = "") -> None:
        """
        Record one rejection for *gate*.

        If the gate is already open, raises CircuitOpenError immediately.
        If this rejection crosses the threshold, opens the circuit, emits
        an ESCALATION via the bus (if configured), then raises CircuitOpenError.

        Parameters
        ----------
        gate:
            Gate identifier, e.g. ``"gate_0"``, ``"gate_1"``.
        task_id:
            Task identifier for tracing (forwarded to the escalation message).

        Raises
        ------
        CircuitOpenError
            When the rejection count reaches *max_rejections*, or when the
            gate is already open.
        """
        if gate in self._open:
            raise CircuitOpenError(gate, self._rejections[gate])

        self._rejections[gate] += 1
        count = self._rejections[gate]

        logger.warning(
            "[GateCircuitBreaker] gate=%s rejection %d/%d task=%s",
            gate, count, self._max, task_id,
        )

        if count >= self._max:
            self._open.add(gate)
            await self._emit_escalation(gate, task_id)
            raise CircuitOpenError(gate, count)

    def record_rejection_sync(self, gate: str) -> None:
        """
        Synchronous variant — does NOT emit PMIA escalations.

        Use this only when you cannot await (e.g. in __init__ or sync tests).
        Prefer :meth:`record_rejection` in async contexts.

        Raises
        ------
        CircuitOpenError
            Same conditions as :meth:`record_rejection`.
        """
        if gate in self._open:
            raise CircuitOpenError(gate, self._rejections[gate])

        self._rejections[gate] += 1
        count = self._rejections[gate]

        if count >= self._max:
            self._open.add(gate)
            raise CircuitOpenError(gate, count)

    def is_open(self, gate: str) -> bool:
        """Return True if the circuit for *gate* is currently open."""
        return gate in self._open

    def reset(self, gate: str) -> None:
        """
        Reset the rejection counter and close the circuit for *gate*.

        Call this after the root cause of the repeated rejections has been
        resolved and the pipeline should be allowed to retry the gate.
        """
        self._open.discard(gate)
        self._rejections[gate] = 0
        logger.info("[GateCircuitBreaker] gate=%s circuit RESET", gate)

    @property
    def rejection_counts(self) -> dict[str, int]:
        """Snapshot of current rejection counts, keyed by gate id."""
        return dict(self._rejections)

    @property
    def open_gates(self) -> frozenset[str]:
        """Set of gate ids whose circuits are currently open."""
        return frozenset(self._open)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _emit_escalation(self, gate: str, task_id: str) -> None:
        if self._bus is None:
            return
        from piv_oac.pmia.message import EscalationMessage

        esc = EscalationMessage(
            from_agent="GateCircuitBreaker",
            to="MasterOrchestrator",
            reason_code="MAX_REJECTIONS",
            task_id=task_id,
        )
        try:
            await self._bus.publish(esc, from_agent="GateCircuitBreaker")
        except Exception as exc:
            logger.error(
                "[GateCircuitBreaker] Failed to emit escalation for gate=%s: %s",
                gate, exc,
            )
