"""Tests for telemetry module — no-op behaviour when OTel is disabled."""

import pytest
import os


class TestAgentSpanNoOp:
    def test_agent_span_noop_when_disabled(self):
        """agent_span must not raise when telemetry is disabled (default)."""
        os.environ["PIV_OAC_TELEMETRY_ENABLED"] = "false"
        # Re-import to pick up env var (module-level constant)
        import importlib
        import piv_oac.telemetry.tracer as tracer_mod
        importlib.reload(tracer_mod)

        with tracer_mod.agent_span(
            agent_type="SecurityAgent",
            model="claude-sonnet-4-6",
            objective_id="test-obj",
        ):
            pass  # Should execute without error

    def test_setup_tracing_noop_when_disabled(self):
        """setup_tracing must not raise when telemetry is disabled."""
        os.environ["PIV_OAC_TELEMETRY_ENABLED"] = "false"
        import importlib
        import piv_oac.telemetry.tracer as tracer_mod
        importlib.reload(tracer_mod)
        tracer_mod.setup_tracing(service_name="test-service")  # no raise

    def test_agent_span_noop_when_otel_unavailable(self, monkeypatch):
        """agent_span is a no-op when opentelemetry package is not installed."""
        import importlib
        import piv_oac.telemetry.tracer as tracer_mod

        monkeypatch.setattr(tracer_mod, "_OTEL_AVAILABLE", False)
        monkeypatch.setattr(tracer_mod, "_ENABLED", True)

        with tracer_mod.agent_span("AuditAgent", "claude-sonnet-4-6", "obj-1"):
            pass  # No raise expected

    def test_setup_tracing_noop_when_otel_unavailable(self, monkeypatch):
        import piv_oac.telemetry.tracer as tracer_mod
        monkeypatch.setattr(tracer_mod, "_OTEL_AVAILABLE", False)
        monkeypatch.setattr(tracer_mod, "_ENABLED", True)
        tracer_mod.setup_tracing()  # No raise

    def test_telemetry_init_exports(self):
        from piv_oac.telemetry import agent_span, setup_tracing
        assert callable(agent_span)
        assert callable(setup_tracing)
