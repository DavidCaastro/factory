# piv-oac SDK

SDK Python para el framework PIV/OAC — orquestación multi-agente con gates bloqueantes.

## Instalación

```bash
pip install piv-oac         # cuando esté en PyPI
pip install -e sdk/         # desde el repo (desarrollo)
```

## Quick Start

```python
from piv_oac import MasterOrchestrator, SecurityAgent
import anthropic

client = anthropic.AsyncAnthropic()

# Invocar SecurityAgent directamente
agent = SecurityAgent(client=client, model="claude-opus-4-6")
result = await agent.invoke("Revisa este plan: ...")
print(result["VERDICT"])  # APPROVED | REJECTED
```

## API Reference

### MasterOrchestrator

Orquestador principal del pipeline PIV/OAC: clasifica tareas, estima presupuesto y coordina los sub-agentes.

```python
MasterOrchestrator(
    client: anthropic.AsyncAnthropic,
    model: str = "claude-sonnet-4-6",
    max_retries: int = 2,
) -> None
```

**Métodos públicos:**

| Método | Firma | Return |
|---|---|---|
| `dispatch` | `async dispatch(task: str) -> dict[str, str]` | Campos del contrato parseados: `CLASSIFICATION`, `BUDGET_ESTIMATE_TOKENS_TOTAL_EST`, `BUDGET_ESTIMATE_USD_EST`, `BUDGET_ESTIMATE_MODEL_DISTRIBUTION`, `spec_validated` |

Raises `VetoError` si detecta `VETO_INTENCION`. Raises `AgentUnrecoverableError` si el modelo no emite campos requeridos tras agotar `max_retries`.

---

### SecurityAgent

Revisa tareas e implementaciones en busca de riesgos de seguridad (Gate de seguridad).

```python
SecurityAgent(
    client: anthropic.AsyncAnthropic,
    model: str = "claude-sonnet-4-6",
) -> None
```

**Métodos públicos:**

| Método | Firma | Return |
|---|---|---|
| `invoke` | `async invoke(prompt: str, max_retries: int = 2) -> dict[str, str]` | Campos: `VERDICT` (`APPROVED`\|`REJECTED`\|`CONDITIONAL_APPROVED`), `RISK_LEVEL` (`LOW`\|`MEDIUM`\|`HIGH`\|`CRITICAL`), `FINDINGS` |
| `check_veto` | `@staticmethod check_veto(raw_output: str, agent_type: str = "SecurityAgent") -> None` | `None`; raises `VetoError` si se detecta `SECURITY_VETO` en `raw_output` |

---

### AuditAgent

Verifica cobertura de RFs y escribe átomos de engram. Único agente autorizado para llamar `EngramStore.write_atom`.

```python
AuditAgent(
    client: anthropic.AsyncAnthropic,
    model: str = "claude-sonnet-4-6",
) -> None
```

**Métodos públicos:**

| Método | Firma | Return |
|---|---|---|
| `invoke` | `async invoke(prompt: str, max_retries: int = 2) -> dict[str, str]` | Campos: `AUDIT_RESULT` (`PASS`\|`FAIL`), `RF_COVERAGE`, `SCOPE_VIOLATIONS`, `ENGRAM_WRITE` |

---

### CoherenceAgent

Ejecuta Gate-1: coherencia entre planes de múltiples Domain Orchestrators.

```python
CoherenceAgent(
    client: anthropic.AsyncAnthropic,
    model: str = "claude-sonnet-4-6",
) -> None
```

**Métodos públicos:**

| Método | Firma | Return |
|---|---|---|
| `invoke` | `async invoke(prompt: str, max_retries: int = 2) -> dict[str, str]` | Campos: `COHERENCE_STATUS`, `GATE1_VERDICT` (`APPROVED`\|`REJECTED`), `CONFLICTS`; raises `GateRejectedError` si `GATE1_VERDICT == "REJECTED"` |
| `parse_conflicts` | `@staticmethod parse_conflicts(raw_output: str) -> list[dict[str, str]]` | Lista de dicts con claves `expert_a`, `expert_b`, `conflict_type`, `resolution` |

---

### ContractParser

Extrae campos de contrato estructurado del output raw de cualquier agente PIV/OAC. Stateless; reutilizable entre llamadas.

```python
ContractParser() -> None
```

**Métodos públicos:**

| Método | Firma | Return |
|---|---|---|
| `parse` | `parse(raw_output: str, required_fields: list[str], agent_type: str = "UnknownAgent") -> dict[str, str]` | Mapa `field_name → value`; raises `MalformedOutputError` si falta algún campo |
| `parse_for_agent` | `parse_for_agent(raw_output: str, agent_type: str) -> dict[str, str]` | Igual que `parse` usando los campos canónicos del `agent_type`; raises `ValueError` si el tipo no está registrado |

---

### EngramStore

Gestiona lectura y escritura de átomos de engram con verificación SHA-256 e historial de snapshots.

```python
EngramStore(engram_dir: Path) -> None
```

**Métodos públicos:**

| Método | Firma | Return |
|---|---|---|
| `read_atom` | `read_atom(atom_path: str) -> str` | Contenido raw del átomo; raises `PIVOACError` si no existe o si el digest SHA-256 no coincide |
| `write_atom` | `write_atom(atom_path: str, content: str, agent_identity: str) -> None` | `None`; raises `PIVOACError` si `agent_identity != "AuditAgent"` |

---

### get_client(provider, **kwargs) — multi-provider factory

```python
from piv_oac.client import get_client

get_client(provider: str = "anthropic", **kwargs) -> LLMClient
```

Crea e instancia el cliente LLM para el proveedor indicado. Raises `ValueError` si el proveedor no está registrado. Raises `ImportError` si falta una dependencia opcional (p. ej. `openai`).

---

### Excepciones: PIVOACError, AgentUnrecoverableError, GateRejectedError, VetoError

| Excepción | Constructor | Atributos | Cuándo se lanza |
|---|---|---|---|
| `PIVOACError` | `PIVOACError(message: str)` | — | Base de todas las excepciones del SDK |
| `AgentUnrecoverableError` | `(agent_type, failure_type, detail)` | `.agent_type`, `.failure_type`, `.detail` | Agente superó `max_retries` sin output válido |
| `GateRejectedError` | `(gate, findings)` | `.gate`, `.findings` | Un gate rechazó la ejecución |
| `VetoError` | `(agent_type, reason)` | `.agent_type`, `.reason` | Agente emitió veto (`VETO_INTENCION` / `SECURITY_VETO`) |
| `MalformedOutputError` | `(agent_type, raw_output, missing_fields)` | `.agent_type`, `.raw_output`, `.missing_fields` | Output del agente omitió campos requeridos del contrato |

## Multi-provider

```python
from piv_oac.client import get_client

client = get_client("openai", api_key="...")  # o "anthropic", "ollama"
```

Proveedores soportados: `"anthropic"` (estable), `"openai"` (experimental, requiere `pip install piv-oac[openai]`), `"ollama"` (experimental, requiere servidor Ollama local).

Ver `skills/multi-provider.md` para la especificación completa del protocolo.

## Telemetría (opt-in)

```python
import os
os.environ["PIV_OAC_TELEMETRY_ENABLED"] = "true"
from piv_oac.telemetry import setup_tracing
setup_tracing(service_name="mi-proyecto")
```

Variables de entorno disponibles:

| Variable | Default | Descripción |
|---|---|---|
| `PIV_OAC_TELEMETRY_ENABLED` | `"false"` | Activa la instrumentación OTel; cuando es `"false"` toda la instrumentación es no-op |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | URL del OTLP collector |
| `OTEL_SERVICE_NAME` | `piv-oac` | Nombre del servicio en los traces |

Ver `skills/observability.md` para la especificación completa de traces, métricas y alertas.

## Excepciones

```python
try:
    result = await agent.invoke(prompt)
except AgentUnrecoverableError as e:
    print(e.failure_type, e.detail)
except GateRejectedError as e:
    print(e.gate, e.findings)
```

## Requisitos

- Python 3.11+
- anthropic >= 0.40.0
- pydantic >= 2.7.0
- pyyaml >= 6.0
- jsonschema >= 4.0
