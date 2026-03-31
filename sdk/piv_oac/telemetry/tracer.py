"""PIV/OAC OpenTelemetry instrumentation."""
from __future__ import annotations
import os
from typing import Iterator
from contextlib import contextmanager

_ENABLED = os.getenv("PIV_OAC_TELEMETRY_ENABLED", "false").lower() == "true"

try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    _OTEL_AVAILABLE = True
except ImportError:
    otel_trace = None  # type: ignore[assignment]
    TracerProvider = None  # type: ignore[assignment,misc]
    BatchSpanProcessor = None  # type: ignore[assignment]
    OTLPSpanExporter = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment,misc]
    SERVICE_NAME = "service.name"  # type: ignore[assignment]
    _OTEL_AVAILABLE = False


def setup_tracing(service_name: str = "piv-oac") -> None:
    """Initialize OpenTelemetry tracing. No-op if telemetry disabled or otel not installed."""
    if not _ENABLED or not _OTEL_AVAILABLE:
        return
    resource = Resource(attributes={SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    otel_trace.set_tracer_provider(provider)


@contextmanager
def agent_span(agent_type: str, model: str, objective_id: str) -> Iterator[None]:
    """Context manager that creates an OTel span for an agent invocation. No-op if disabled."""
    if not _ENABLED or not _OTEL_AVAILABLE:
        yield
        return
    tracer = otel_trace.get_tracer("piv_oac")
    with tracer.start_as_current_span(f"piv_oac.agent.{agent_type}") as span:
        span.set_attribute("agent.type", agent_type)
        span.set_attribute("agent.model", model)
        span.set_attribute("objective.id", objective_id)
        yield
