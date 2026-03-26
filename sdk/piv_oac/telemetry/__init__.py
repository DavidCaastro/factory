"""PIV/OAC telemetry package — OpenTelemetry instrumentation."""
from piv_oac.telemetry.tracer import setup_tracing, agent_span

__all__ = ["setup_tracing", "agent_span"]
