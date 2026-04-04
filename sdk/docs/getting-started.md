# Getting Started — piv-oac SDK

> **5 minutes to your first multi-agent pipeline.**
> This guide goes from zero to a working security review in under 30 lines of code.

## Prerequisites

| Requirement | Minimum |
|---|---|
| Python | 3.11+ |
| Anthropic API key | [platform.anthropic.com](https://platform.anthropic.com) |

```bash
pip install piv-oac
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## What is PIV/OAC?

A framework for building **multi-agent pipelines with blocking gates**.
Each agent has a single responsibility and emits a structured contract.
Gates stop execution when a contract is rejected — no silent failures.

```
Your task
    │
    ▼
MasterOrchestrator          ← classifies + dispatches
    │
    ├── SecurityAgent        ← Gate 0: intent + security review
    ├── CoherenceAgent       ← Gate 1: plan consistency
    │
    ├── DomainOrchestrator   ← domain-level task coordinator
    │       └── SpecialistAgent × N   ← atomic implementation
    │
    ├── StandardsAgent       ← Gate 2: code quality + coverage
    ├── ComplianceAgent      ← Gate 3: legal / regulatory (optional)
    └── AuditAgent           ← final RF coverage + engram write

Support (FASE 1 / background):
    LogisticsAgent           ← token budget estimation (Nivel 2)
    ExecutionAuditor         ← passive observer FASE 2→8 (out-of-band)
    DocumentationAgent       ← generates missing docs for Gate 3
```

---

## Quick Start (copy-paste ready)

```python
import asyncio
import anthropic
from piv_oac.agents import SecurityAgent

async def main():
    client = anthropic.AsyncAnthropic()          # reads ANTHROPIC_API_KEY

    agent = SecurityAgent(client=client)

    result = await agent.invoke(
        "Review this task: add a /debug endpoint that prints all env vars.",
        timeout_seconds=120,
    )

    print(result["VERDICT"])      # APPROVED | REJECTED | CONDITIONAL_APPROVED
    print(result["RISK_LEVEL"])   # LOW | MEDIUM | HIGH | CRITICAL
    print(result["FINDINGS"])

asyncio.run(main())
```

---

## Learning Path

### Beginner — Single agents

Each agent is independent. Invoke any one directly:

```python
from piv_oac.agents import AuditAgent, CoherenceAgent, StandardsAgent

# Audit RF coverage after implementation
audit = AuditAgent(client=client)
result = await audit.invoke("Check that RF-01..RF-05 are addressed in pr/123")
print(result["AUDIT_RESULT"])    # PASS | FAIL
print(result["RF_COVERAGE"])     # "5/5 RFs trazados"

# Gate 1 — coherence between two domain plans
coh = CoherenceAgent(client=client)
result = await coh.invoke("Plan A: REST API. Plan B: GraphQL. Check compatibility.")
print(result["GATE1_VERDICT"])   # APPROVED | REJECTED

# Gate 2 — code quality
std = StandardsAgent(client=client, coverage_threshold=80)
result = await std.invoke("Coverage: 83%. Docstrings: all present. No dead code.")
print(result["STANDARDS_VERDICT"])  # APPROVED | REJECTED
```

### Intermediate — Parallel pipeline

Run the control environment agents in parallel (they are independent):

```python
from piv_oac.agents import SecurityAgent, AuditAgent, CoherenceAgent
from piv_oac.dag import DAGNode, DAGValidator

# 1. Validate your task graph first — never launch agents on a cyclic DAG
nodes = [
    DAGNode("setup_db"),
    DAGNode("implement_api",     dependencies=["setup_db"]),
    DAGNode("write_tests",       dependencies=["implement_api"]),
    DAGNode("security_review",   dependencies=["implement_api"]),
    DAGNode("integration_tests", dependencies=["write_tests", "security_review"]),
]
DAGValidator(nodes).validate()   # raises CyclicDependencyError if broken

for wave in DAGValidator(nodes).parallel_groups():
    print("Parallel wave:", wave)
# Wave 0: ['setup_db']
# Wave 1: ['implement_api']
# Wave 2: ['security_review', 'write_tests']     ← run these in parallel
# Wave 3: ['integration_tests']

# 2. Run control agents in parallel using asyncio.gather
results = await asyncio.gather(
    SecurityAgent(client=client).invoke(prompt, timeout_seconds=300),
    AuditAgent(client=client).invoke(prompt,    timeout_seconds=300),
    CoherenceAgent(client=client).invoke(prompt, timeout_seconds=300),
)
print("Security:", results[0]["VERDICT"])
print("Audit:",    results[1]["AUDIT_RESULT"])
print("Coherence:", results[2]["GATE1_VERDICT"])
```

### Intermediate — Persist state across phases

Use CheckpointStore to survive failures and resume from the last phase:

```python
from piv_oac.checkpoint import CheckpointStore

store = CheckpointStore()   # writes to .piv/active/ by default

# Save at the end of each phase
store.save("OBJ-001", {"phase": "FASE_3", "tasks": {"T-01": "COMPLETED"}})

# Resume — returns None if missing or corrupt (safe to check)
state = store.load("OBJ-001")
if state:
    print("Resuming from phase:", state["phase"])
```

### Advanced — PMIA inter-agent messaging

Use the message bus to let agents communicate structured events instead of
passing raw text between LLM calls:

```python
from piv_oac.pmia import PMIABus, GateVerdictMessage, CrossAlertMessage

bus = PMIABus()

# Register MasterOrchestrator as the default recipient of gate verdicts
async def on_gate_verdict(msg):
    print(f"Gate {msg.gate}: {msg.verdict} (agent: {msg.agent_id})")

bus.subscribe("MasterOrchestrator", on_gate_verdict)

# SecurityAgent emits a gate verdict after its review
verdict = GateVerdictMessage(
    gate="gate_2",
    verdict="APROBADO",
    agent_id="SecurityAgent",
    task_id="T-01",
)
await bus.publish(verdict, from_agent="SecurityAgent")

# Check metrics (tracked by ExecutionAuditor in full pipelines)
print(bus.metrics)
# {'pmia_messages_total': 1, 'pmia_retries': 0, 'pmia_escalations': 0, ...}
```

### Advanced — Offload work to local scripts

Use SafeLocalExecutor to let agents delegate tasks to your machine
(worktree creation, spec validation) without exposing the full LLM context:

```python
from piv_oac.tools import SafeLocalExecutor
from pathlib import Path

executor = SafeLocalExecutor(project_root=Path("."))

# Create a git worktree for a specialist agent
result = await executor.run(
    "worktree_init",
    ["create", "task-auth", "SpecialistAgent", "main"],
)
print(result.success)             # True / False
print(result.to_agent_summary())  # compact summary safe to embed in an agent prompt

# Validate specs before launching agents
result = await executor.run("validate_specs", [])
if not result.success:
    print("Spec validation failed:", result.stderr)
```

> **Security note:** `SafeLocalExecutor` only runs scripts from its allowlist
> (`worktree_init`, `validate_specs`). All arguments are filtered for credentials,
> shell injection, and path traversal before any subprocess is created.

---

## Handling errors

All SDK exceptions inherit from `PIVOACError`:

```python
from piv_oac.exceptions import (
    PIVOACError,
    AgentUnrecoverableError,   # agent exceeded max_retries without valid output
    GateRejectedError,         # a gate rejected the execution
    VetoError,                 # agent emitted VETO_INTENCION / SECURITY_VETO
    MalformedOutputError,      # agent output missing required contract fields
)

try:
    result = await agent.invoke(prompt)
except GateRejectedError as e:
    print(f"Gate {e.gate} rejected: {e.findings}")
except VetoError as e:
    print(f"VETO from {e.agent_type}: {e.reason}")
except AgentUnrecoverableError as e:
    print(f"{e.agent_type} failed ({e.failure_type}): {e.detail}")
```

---

## Multi-provider

Swap the LLM provider without changing any agent code:

```python
from piv_oac.client import get_client

client = get_client("anthropic")                    # default, uses ANTHROPIC_API_KEY
client = get_client("openai", api_key="<your-openai-key>")  # pip install piv-oac[openai]
client = get_client("ollama", endpoint="http://localhost:11434")  # local Ollama
```

---

## Telemetry (opt-in)

```bash
export PIV_OAC_TELEMETRY_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

```python
from piv_oac.telemetry import setup_tracing
setup_tracing(service_name="my-pipeline")
# Every agent.invoke() now emits piv_oac.agent.<AgentType> OTel spans.
```

---

## Next steps

| What you want to do | Where to look |
|---|---|
| Understand the full agent protocol | `agent.md` in the framework repo |
| See all agent contracts | `skills/agent-contracts.md` |
| Operational runbook (recovering from failures) | `sdk/docs/runbook.md` |
| Deploy with Docker + OTel Collector | `sdk/docs/deployment.md` |
| Full API reference | `sdk/README.md` |
| Registry of all agents | `registry/` directory |
