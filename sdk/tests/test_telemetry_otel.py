"""Tests for telemetry — OTel-enabled paths (mocking opentelemetry)."""

import pytest
from unittest.mock import MagicMock, patch, call


class TestSetupTracingOtelEnabled:
    def test_setup_tracing_configures_provider(self, monkeypatch):
        """When OTel available + enabled, setup_tracing creates a provider."""
        import importlib
        import piv_oac.telemetry.tracer as mod

        mock_provider = MagicMock()
        mock_processor = MagicMock()
        mock_exporter = MagicMock()
        mock_trace = MagicMock()

        monkeypatch.setattr(mod, "_OTEL_AVAILABLE", True)
        monkeypatch.setattr(mod, "_ENABLED", True)

        with patch.multiple(
            "piv_oac.telemetry.tracer",
            Resource=MagicMock(return_value=MagicMock()),
            TracerProvider=MagicMock(return_value=mock_provider),
            BatchSpanProcessor=MagicMock(return_value=mock_processor),
            OTLPSpanExporter=MagicMock(return_value=mock_exporter),
            otel_trace=mock_trace,
        ):
            mod.setup_tracing(service_name="my-service")
            mock_provider.add_span_processor.assert_called_once_with(mock_processor)
            mock_trace.set_tracer_provider.assert_called_once_with(mock_provider)

    def test_setup_tracing_uses_env_endpoint(self, monkeypatch):
        """setup_tracing passes OTEL_EXPORTER_OTLP_ENDPOINT to the exporter."""
        import piv_oac.telemetry.tracer as mod

        monkeypatch.setattr(mod, "_OTEL_AVAILABLE", True)
        monkeypatch.setattr(mod, "_ENABLED", True)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://custom-collector:4317")

        mock_exporter_cls = MagicMock()
        with patch.multiple(
            "piv_oac.telemetry.tracer",
            Resource=MagicMock(return_value=MagicMock()),
            TracerProvider=MagicMock(return_value=MagicMock()),
            BatchSpanProcessor=MagicMock(return_value=MagicMock()),
            OTLPSpanExporter=mock_exporter_cls,
            otel_trace=MagicMock(),
        ):
            mod.setup_tracing()
        mock_exporter_cls.assert_called_once_with(endpoint="http://custom-collector:4317")

    def test_setup_tracing_default_endpoint(self, monkeypatch):
        """setup_tracing defaults to localhost:4317 when env var not set."""
        import piv_oac.telemetry.tracer as mod
        import os

        monkeypatch.setattr(mod, "_OTEL_AVAILABLE", True)
        monkeypatch.setattr(mod, "_ENABLED", True)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

        mock_exporter_cls = MagicMock()
        with patch.multiple(
            "piv_oac.telemetry.tracer",
            Resource=MagicMock(return_value=MagicMock()),
            TracerProvider=MagicMock(return_value=MagicMock()),
            BatchSpanProcessor=MagicMock(return_value=MagicMock()),
            OTLPSpanExporter=mock_exporter_cls,
            otel_trace=MagicMock(),
        ):
            mod.setup_tracing()
        mock_exporter_cls.assert_called_once_with(endpoint="http://localhost:4317")


class TestAgentSpanOtelEnabled:
    def test_agent_span_creates_span_with_attributes(self, monkeypatch):
        """When OTel enabled, agent_span creates a span with correct attributes."""
        import piv_oac.telemetry.tracer as mod

        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)

        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span

        mock_trace = MagicMock()
        mock_trace.get_tracer.return_value = mock_tracer

        monkeypatch.setattr(mod, "_OTEL_AVAILABLE", True)
        monkeypatch.setattr(mod, "_ENABLED", True)
        monkeypatch.setattr(mod, "otel_trace", mock_trace)

        with mod.agent_span("SecurityAgent", "claude-sonnet-4-6", "OBJ-001"):
            pass

        mock_tracer.start_as_current_span.assert_called_once_with(
            "piv_oac.agent.SecurityAgent"
        )
        mock_span.set_attribute.assert_any_call("agent.type", "SecurityAgent")
        mock_span.set_attribute.assert_any_call("agent.model", "claude-sonnet-4-6")
        mock_span.set_attribute.assert_any_call("objective.id", "OBJ-001")

    def test_agent_span_gets_tracer_with_correct_name(self, monkeypatch):
        """agent_span uses 'piv_oac' as the tracer name."""
        import piv_oac.telemetry.tracer as mod

        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)

        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span

        mock_trace = MagicMock()
        mock_trace.get_tracer.return_value = mock_tracer

        monkeypatch.setattr(mod, "_OTEL_AVAILABLE", True)
        monkeypatch.setattr(mod, "_ENABLED", True)
        monkeypatch.setattr(mod, "otel_trace", mock_trace)

        with mod.agent_span("AuditAgent", "claude-sonnet-4-6", "OBJ-002"):
            pass

        mock_trace.get_tracer.assert_called_once_with("piv_oac")

    def test_agent_span_span_name_includes_agent_type(self, monkeypatch):
        """The OTel span name follows the pattern piv_oac.agent.<AgentType>."""
        import piv_oac.telemetry.tracer as mod

        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)

        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span

        mock_trace = MagicMock()
        mock_trace.get_tracer.return_value = mock_tracer

        monkeypatch.setattr(mod, "_OTEL_AVAILABLE", True)
        monkeypatch.setattr(mod, "_ENABLED", True)
        monkeypatch.setattr(mod, "otel_trace", mock_trace)

        with mod.agent_span("CoherenceAgent", "claude-sonnet-4-6", "OBJ-003"):
            pass

        mock_tracer.start_as_current_span.assert_called_once_with(
            "piv_oac.agent.CoherenceAgent"
        )
