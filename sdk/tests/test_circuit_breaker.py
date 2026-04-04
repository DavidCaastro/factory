"""
Tests for GateCircuitBreaker and CircuitOpenError.
"""

from __future__ import annotations

import pytest

from piv_oac.circuit_breaker import GateCircuitBreaker, MAX_GATE_REJECTIONS
from piv_oac.exceptions import CircuitOpenError


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestMaxGateRejections:
    def test_default_is_3(self):
        assert MAX_GATE_REJECTIONS == 3

    def test_breaker_uses_default_when_not_specified(self):
        breaker = GateCircuitBreaker()
        assert breaker._max == MAX_GATE_REJECTIONS


# ---------------------------------------------------------------------------
# Sync API
# ---------------------------------------------------------------------------

class TestRecordRejectionSync:
    def test_first_rejection_increments_count(self):
        breaker = GateCircuitBreaker(max_rejections=3)
        breaker.record_rejection_sync("gate_0")
        assert breaker.rejection_counts["gate_0"] == 1

    def test_two_rejections_do_not_open_circuit(self):
        breaker = GateCircuitBreaker(max_rejections=3)
        breaker.record_rejection_sync("gate_0")
        breaker.record_rejection_sync("gate_0")
        assert not breaker.is_open("gate_0")

    def test_third_rejection_opens_circuit(self):
        breaker = GateCircuitBreaker(max_rejections=3)
        breaker.record_rejection_sync("gate_0")
        breaker.record_rejection_sync("gate_0")
        with pytest.raises(CircuitOpenError) as exc_info:
            breaker.record_rejection_sync("gate_0")
        assert exc_info.value.gate == "gate_0"
        assert exc_info.value.rejection_count == 3
        assert breaker.is_open("gate_0")

    def test_open_circuit_raises_immediately(self):
        breaker = GateCircuitBreaker(max_rejections=1)
        with pytest.raises(CircuitOpenError):
            breaker.record_rejection_sync("gate_1")
        # Already open — any further call raises too
        with pytest.raises(CircuitOpenError):
            breaker.record_rejection_sync("gate_1")

    def test_different_gates_are_independent(self):
        breaker = GateCircuitBreaker(max_rejections=3)
        breaker.record_rejection_sync("gate_0")
        breaker.record_rejection_sync("gate_0")
        # gate_0 has 2 rejections; gate_1 is clean
        breaker.record_rejection_sync("gate_1")
        assert not breaker.is_open("gate_0")
        assert not breaker.is_open("gate_1")


# ---------------------------------------------------------------------------
# Async API (no bus)
# ---------------------------------------------------------------------------

class TestRecordRejectionAsync:
    @pytest.mark.asyncio
    async def test_async_increments_count(self):
        breaker = GateCircuitBreaker(max_rejections=3)
        await breaker.record_rejection("gate_0", task_id="T-01")
        assert breaker.rejection_counts["gate_0"] == 1

    @pytest.mark.asyncio
    async def test_async_opens_on_threshold(self):
        breaker = GateCircuitBreaker(max_rejections=3)
        await breaker.record_rejection("gate_0")
        await breaker.record_rejection("gate_0")
        with pytest.raises(CircuitOpenError) as exc_info:
            await breaker.record_rejection("gate_0", task_id="T-03")
        assert exc_info.value.gate == "gate_0"
        assert exc_info.value.rejection_count == 3

    @pytest.mark.asyncio
    async def test_async_open_circuit_raises_immediately(self):
        breaker = GateCircuitBreaker(max_rejections=1)
        with pytest.raises(CircuitOpenError):
            await breaker.record_rejection("gate_2")
        with pytest.raises(CircuitOpenError):
            await breaker.record_rejection("gate_2")

    @pytest.mark.asyncio
    async def test_async_custom_threshold(self):
        breaker = GateCircuitBreaker(max_rejections=2)
        await breaker.record_rejection("gate_1")
        with pytest.raises(CircuitOpenError):
            await breaker.record_rejection("gate_1")
        assert breaker.rejection_counts["gate_1"] == 2


# ---------------------------------------------------------------------------
# State inspection
# ---------------------------------------------------------------------------

class TestStateProperties:
    def test_is_open_false_by_default(self):
        breaker = GateCircuitBreaker()
        assert not breaker.is_open("gate_0")
        assert not breaker.is_open("gate_1")

    def test_rejection_counts_empty_by_default(self):
        breaker = GateCircuitBreaker()
        assert breaker.rejection_counts == {}

    def test_open_gates_empty_by_default(self):
        breaker = GateCircuitBreaker()
        assert breaker.open_gates == frozenset()

    def test_open_gates_contains_open_circuit(self):
        breaker = GateCircuitBreaker(max_rejections=1)
        with pytest.raises(CircuitOpenError):
            breaker.record_rejection_sync("gate_3")
        assert "gate_3" in breaker.open_gates


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_closes_circuit(self):
        breaker = GateCircuitBreaker(max_rejections=1)
        with pytest.raises(CircuitOpenError):
            breaker.record_rejection_sync("gate_0")
        assert breaker.is_open("gate_0")
        breaker.reset("gate_0")
        assert not breaker.is_open("gate_0")

    def test_reset_clears_rejection_count(self):
        breaker = GateCircuitBreaker(max_rejections=3)
        breaker.record_rejection_sync("gate_0")
        breaker.record_rejection_sync("gate_0")
        breaker.reset("gate_0")
        assert breaker.rejection_counts["gate_0"] == 0

    def test_reset_allows_new_rejections(self):
        breaker = GateCircuitBreaker(max_rejections=1)
        with pytest.raises(CircuitOpenError):
            breaker.record_rejection_sync("gate_0")
        breaker.reset("gate_0")
        # Should not raise — 1 rejection after reset
        # (max_rejections=1 means 1st rejection opens it again)
        with pytest.raises(CircuitOpenError):
            breaker.record_rejection_sync("gate_0")
        assert breaker.rejection_counts["gate_0"] == 1

    def test_reset_unknown_gate_is_noop(self):
        breaker = GateCircuitBreaker()
        breaker.reset("nonexistent_gate")  # should not raise
        assert not breaker.is_open("nonexistent_gate")


# ---------------------------------------------------------------------------
# PMIA integration — escalation emitted via bus
# ---------------------------------------------------------------------------

class TestPMIAEscalation:
    @pytest.mark.asyncio
    async def test_escalation_emitted_when_circuit_opens(self):
        from piv_oac.pmia.bus import PMIABus
        from piv_oac.pmia.message import EscalationMessage

        bus = PMIABus()
        received: list[EscalationMessage] = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("MasterOrchestrator", handler)

        breaker = GateCircuitBreaker(max_rejections=2, bus=bus)
        await breaker.record_rejection("gate_0", task_id="T-ESC")
        with pytest.raises(CircuitOpenError):
            await breaker.record_rejection("gate_0", task_id="T-ESC")

        assert len(received) == 1
        esc = received[0]
        assert isinstance(esc, EscalationMessage)
        assert esc.reason_code == "MAX_REJECTIONS"
        assert esc.task_id == "T-ESC"

    @pytest.mark.asyncio
    async def test_no_escalation_without_bus(self):
        # Should not raise even though no bus is provided
        breaker = GateCircuitBreaker(max_rejections=1)
        with pytest.raises(CircuitOpenError):
            await breaker.record_rejection("gate_0")

    @pytest.mark.asyncio
    async def test_escalation_not_emitted_before_threshold(self):
        from piv_oac.pmia.bus import PMIABus

        bus = PMIABus()
        received = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("MasterOrchestrator", handler)

        breaker = GateCircuitBreaker(max_rejections=3, bus=bus)
        await breaker.record_rejection("gate_1")
        await breaker.record_rejection("gate_1")
        # Only 2 of 3 — circuit still closed, no escalation yet
        assert received == []


# ---------------------------------------------------------------------------
# CircuitOpenError attributes
# ---------------------------------------------------------------------------

class TestCircuitOpenError:
    def test_error_carries_gate_and_count(self):
        err = CircuitOpenError(gate="gate_2", rejection_count=5)
        assert err.gate == "gate_2"
        assert err.rejection_count == 5

    def test_error_message_contains_gate(self):
        err = CircuitOpenError(gate="gate_2", rejection_count=3)
        assert "gate_2" in str(err)
        assert "3" in str(err)

    def test_inherits_from_piv_oac_error(self):
        from piv_oac.exceptions import PIVOACError
        err = CircuitOpenError("gate_0", 3)
        assert isinstance(err, PIVOACError)
