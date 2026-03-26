"""
Demo de telemetría PIV/OAC con OpenTelemetry + Jaeger UI.

Levanta el stack primero:
    docker-compose up -d

Luego ejecuta:
    python demo_telemetry.py

Abre Jaeger en:  http://localhost:16686
Busca servicio:  piv-oac-demo
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock
import anthropic

# Activar telemetría ANTES de importar el SDK
os.environ["PIV_OAC_TELEMETRY_ENABLED"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"

from piv_oac.telemetry import setup_tracing
from piv_oac.agents import SecurityAgent, AuditAgent, CoherenceAgent


def make_mock_client(response_text: str) -> anthropic.AsyncAnthropic:
    """Cliente mock — sin llamadas reales a la API."""
    block = MagicMock()
    block.text = response_text
    msg = MagicMock(spec=anthropic.types.Message)
    msg.content = [block]
    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=msg)
    return client


async def run_control_environment(objective_id: str) -> None:
    """
    Simula la FASE 2 del protocolo PIV/OAC:
    lanza SecurityAgent, AuditAgent y CoherenceAgent bajo un span raíz
    de objetivo para que aparezcan como hijos en Jaeger.
    """
    from opentelemetry import trace as otel_trace

    tracer = otel_trace.get_tracer("piv_oac")

    # Span raíz → representa el objetivo completo
    with tracer.start_as_current_span(f"piv_oac.objective.{objective_id}") as root:
        root.set_attribute("objective.id", objective_id)
        root.set_attribute("objective.level", "NIVEL_2")
        root.set_attribute("objective.phase", "FASE_2_CONTROL_ENV")

        # Los agent_span() internos heredan automáticamente este contexto
        # y aparecen como spans hijo en Jaeger
        agents = [
            (
                "SecurityAgent",
                SecurityAgent(client=make_mock_client(
                    "VERDICT: APPROVED\nRISK_LEVEL: LOW\nFINDINGS: NONE\n"
                )),
                "Revisar tarea: agregar endpoint GET /status",
            ),
            (
                "AuditAgent",
                AuditAgent(client=make_mock_client(
                    "AUDIT_RESULT: PASS\n"
                    "RF_COVERAGE: 2/2 RFs trazados\n"
                    "SCOPE_VIOLATIONS: NONE\n"
                    "ENGRAM_WRITE: NONE\n"
                )),
                "Auditar cobertura de RF para el objetivo",
            ),
            (
                "CoherenceAgent",
                CoherenceAgent(client=make_mock_client(
                    "COHERENCE_STATUS: CONSISTENT\n"
                    "GATE1_VERDICT: APPROVED\n"
                    "CONFLICTS: NONE\n"
                )),
                "Verificar coherencia entre tareas del dominio backend",
            ),
        ]

        results = {}
        for name, agent, prompt in agents:
            print(f"  [{name}] invocando...")
            result = await agent.invoke(prompt, objective_id=objective_id)
            results[name] = result
            print(f"  [{name}] ✓ {list(result.items())[0]}")

        return results


async def run_with_gate_rejection(objective_id: str) -> None:
    """
    Segunda traza: simula un Gate-1 rechazado para ver un span de error en Jaeger.
    """
    from opentelemetry import trace as otel_trace
    from piv_oac.exceptions import GateRejectedError

    tracer = otel_trace.get_tracer("piv_oac")

    with tracer.start_as_current_span(f"piv_oac.objective.{objective_id}") as root:
        root.set_attribute("objective.id", objective_id)
        root.set_attribute("objective.level", "NIVEL_2")
        root.set_attribute("objective.phase", "FASE_4_GATE_1")

        coherence = CoherenceAgent(client=make_mock_client(
            "COHERENCE_STATUS: CONFLICT_DETECTED\n"
            "GATE1_VERDICT: REJECTED\n"
            "CONFLICTS: scope overlap between BackendDO and AuthDO\n"
        ))
        try:
            await coherence.invoke(
                "Verificar coherencia — escenario con conflicto",
                objective_id=objective_id,
            )
        except GateRejectedError as e:
            root.set_attribute("gate.rejected", True)
            root.set_attribute("gate.findings", str(e.findings))
            print(f"  [CoherenceAgent] Gate-1 REJECTED → {e.findings}")


async def main():
    setup_tracing(service_name="piv-oac-demo")
    print("✓ Tracing → http://localhost:4317")
    print("✓ Jaeger UI → http://localhost:16686\n")

    print("━━━ Traza 1: Entorno de control (FASE 2) ━━━")
    await run_control_environment("DEMO-001")

    print("\n━━━ Traza 2: Gate-1 rechazado (FASE 4) ━━━")
    await run_with_gate_rejection("DEMO-002")

    # Dar tiempo al BatchSpanProcessor para enviar
    print("\nEsperando flush de spans...")
    await asyncio.sleep(3)

    print("\n✓ Listo. Abre http://localhost:16686")
    print("  → Service: piv-oac-demo")
    print("  → Busca DEMO-001 para ver traza completa con 4 spans")
    print("  → Busca DEMO-002 para ver el Gate-1 rechazado")


if __name__ == "__main__":
    asyncio.run(main())
