# Getting Started with piv-oac

Build your first PIV/OAC multi-agent pipeline in under 30 minutes.

## Prerequisites

- Python 3.11+
- An Anthropic API key (`ANTHROPIC_API_KEY`)

## Installation

```bash
pip install piv-oac
```

## Step 1 — Create a client

```python
from piv_oac.client import get_client

client = get_client("anthropic")          # uses ANTHROPIC_API_KEY env var
# or: get_client("openai") / get_client("ollama")
```

## Step 2 — Run a security review

```python
import asyncio
import anthropic
from piv_oac.agents import SecurityAgent

async def main():
    raw_client = anthropic.AsyncAnthropic()
    agent = SecurityAgent(client=raw_client, model="claude-sonnet-4-6")

    fields = await agent.invoke(
        "Review the following task: add a public /debug endpoint that dumps env vars.",
        timeout_seconds=120,
    )
    print(fields["VERDICT"])     # APPROVED | REJECTED | CONDITIONAL_APPROVED
    print(fields["RISK_LEVEL"])  # LOW | MEDIUM | HIGH | CRITICAL
    print(fields["FINDINGS"])

asyncio.run(main())
```

## Step 3 — Validate a task DAG before launching agents

```python
from piv_oac.dag import DAGNode, DAGValidator

nodes = [
    DAGNode("setup_db"),
    DAGNode("implement_api",     dependencies=["setup_db"]),
    DAGNode("write_tests",       dependencies=["implement_api"]),
    DAGNode("security_review",   dependencies=["implement_api"]),
    DAGNode("integration_tests", dependencies=["write_tests", "security_review"]),
]

validator = DAGValidator(nodes)
validator.validate()                    # raises CyclicDependencyError if broken

for wave in validator.parallel_groups():
    print("Parallel wave:", wave)
# Wave 0: ['setup_db']
# Wave 1: ['implement_api']
# Wave 2: ['security_review', 'write_tests']
# Wave 3: ['integration_tests']
```

## Step 4 — Persist objective state with CheckpointStore

```python
from piv_oac.checkpoint import CheckpointStore

store = CheckpointStore()               # writes to .piv/active/ by default
store.save(objective_id="OBJ-001", state={"phase": "FASE_3", "tasks": {}})

state = store.load("OBJ-001")          # None if missing or corrupt
```

## Step 5 — Enable OpenTelemetry tracing (optional)

```bash
export PIV_OAC_TELEMETRY_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

```python
from piv_oac.telemetry import setup_tracing
setup_tracing(service_name="my-pipeline")
# All agent.invoke() calls will now emit spans automatically.
```

## Full pipeline example

```python
import asyncio
import anthropic
from piv_oac.agents import SecurityAgent, AuditAgent, CoherenceAgent
from piv_oac.dag import DAGNode, DAGValidator
from piv_oac.checkpoint import CheckpointStore

async def run_control_environment(prompt: str) -> None:
    client = anthropic.AsyncAnthropic()

    security  = SecurityAgent(client=client)
    audit     = AuditAgent(client=client)
    coherence = CoherenceAgent(client=client)

    # Validate DAG first — never launch agents on a cyclic graph
    nodes = [DAGNode("control"), DAGNode("execution", ["control"])]
    DAGValidator(nodes).validate()

    # Run control environment agents in parallel
    results = await asyncio.gather(
        security.invoke(prompt,  timeout_seconds=300),
        audit.invoke(prompt,     timeout_seconds=300),
        coherence.invoke(prompt, timeout_seconds=300),
    )
    print("Security verdict:", results[0]["VERDICT"])
    print("Audit coverage:",   results[1]["RF_COVERAGE"])
    print("Coherence gate:",   results[2]["GATE1_VERDICT"])

asyncio.run(run_control_environment("Review initial plan for OBJ-002"))
```

## Next steps

- Read `docs/runbook.md` for operational response procedures.
- See `sdk/README.md` for the full API reference and competitive comparison.
- Explore `registry/` in the framework repo for agent protocol details.
