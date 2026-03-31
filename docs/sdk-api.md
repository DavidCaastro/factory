# PIV/OAC SDK — API Reference

> Version: 0.1.0 | Package: `piv-oac` | Python ≥ 3.11

---

## Install

```bash
pip install piv-oac
```

---

## Agents

All agents extend `AgentBase` and are invoked with `await agent.invoke(prompt)`.

### `AgentBase`

```python
from piv_oac.agents.base import AgentBase

class AgentBase(ABC):
    agent_type: str  # set by each subclass

    def __init__(self, client: anthropic.AsyncAnthropic, model: str) -> None: ...

    async def invoke(
        self,
        prompt: str,
        max_retries: int = 2,
        objective_id: str = "unknown",
        timeout_seconds: float | None = None,
    ) -> dict[str, str]: ...
```

Returns a `dict[str, str]` of the structured contract fields.
Raises `AgentUnrecoverableError` after exhausting retries.

---

### Control Environment Agents

| Class | `agent_type` | Required output fields |
|---|---|---|
| `SecurityAgent` | `"SecurityAgent"` | `VERDICT`, `BLOCKERS`, `WARNINGS` |
| `AuditAgent` | `"AuditAgent"` | `VERDICT`, `RF_COVERAGE`, `GAPS` |
| `CoherenceAgent` | `"CoherenceAgent"` | `VERDICT`, `CONFLICTS`, `RESOLUTION` |
| `StandardsAgent` | `"StandardsAgent"` | `VERDICT`, `ISSUES`, `COVERAGE` |
| `ComplianceAgent` | `"ComplianceAgent"` | `VERDICT`, `RISKS`, `DISCLAIMER` |

---

### Orchestrators

#### `MasterOrchestrator`

```python
from piv_oac import MasterOrchestrator

agent = MasterOrchestrator(client=client, model="claude-opus-4-6")
result = await agent.invoke(objective_prompt, objective_id="OBJ-001")
```

#### `DomainOrchestrator`

```python
from piv_oac import DomainOrchestrator, WorktreeSpec

agent = DomainOrchestrator(client=client, model="claude-sonnet-4-6")
```

#### `ResearchOrchestrator`

For `RESEARCH` and `MIXED` execution modes.

```python
from piv_oac import ResearchOrchestrator

agent = ResearchOrchestrator(client=client, model="claude-sonnet-4-6")
result = await agent.invoke("Research EIP-1559 dynamics.", objective_id="OBJ-RES-01")
# result keys: RQ_ID, CONFIDENCE, FINDINGS, SOURCES, GAPS
```

---

### `EvaluationAgent`

Scores parallel Specialist Agent outputs on a 0–1 scale.

```python
from piv_oac import (
    EvaluationAgent, FuncInput, SecInput, QualInput, CohInput, FootInput
)

agent = EvaluationAgent(logs_dir=Path("logs_scores/"))

result = agent.score(
    objective_id="OBJ-001",
    task_id="T-02",
    expert_id="expert-A",
    func=FuncInput(acs_covered=4, acs_partial=0, acs_total=4),
    sec=SecInput(findings_critical_high=0, total_checks=100, tool="semgrep"),
    qual=QualInput(coverage_pct=97.0, violations=0),
    coh=CohInput(
        implements_in_declared_layer=True,
        no_layer_bypass=True,
        interfaces_match_plan=True,
        no_undeclared_deps=True,
    ),
    foot=FootInput(files_changed=3, files_declared=3),
)

print(result.total_score)          # 1.0
agent.append_to_log(result, session_id="2026-03-22")

# Early termination recommendation
recommend, expert_id = agent.should_recommend_early_termination(
    results=[result], active_experts=2
)
```

**Scoring dimensions** (contracts/evaluation.md):

| Dimension | Weight | Method |
|---|---|---|
| `FUNC` — functional completeness | 0.35 | AC coverage count |
| `SEC` — security findings | 0.25 | semgrep/bandit ratio |
| `QUAL` — code quality | 0.20 | pytest-cov + ruff |
| `COH` — architectural coherence | 0.15 | 4-item rubric |
| `FOOT` — footprint minimality | 0.05 | git diff --stat |

---

## Checkpoint

### `CheckpointStore`

```python
from piv_oac.checkpoint.store import CheckpointStore, ObjectiveState

store = CheckpointStore(base_dir=Path("."))
state = store.create("OBJ-001", "Build auth module")
store.save(state)
loaded = store.load("OBJ-001")
store.complete("OBJ-001")   # moves to .piv/completed/
store.fail("OBJ-001")       # moves to .piv/failed/
```

### `CheckpointValidator`

```python
from piv_oac import CheckpointValidator

validator = CheckpointValidator(repo_root=Path("."))
report = validator.validate_all()
print(report.format())        # PASS / FAIL with details
print(report.passed)          # bool
print(report.errors)          # list[ValidationIssue]
print(report.warnings)        # list[ValidationIssue]
```

---

## DAG

```python
from piv_oac import DAGNode, DAGValidator, CyclicDependencyError

nodes = [
    DAGNode(id="T-01", depends_on=[]),
    DAGNode(id="T-02", depends_on=["T-01"]),
    DAGNode(id="T-03", depends_on=["T-01"]),
]
order = DAGValidator(nodes).topological_sort()  # raises CyclicDependencyError if cycle
```

---

## LLM Client

```python
from piv_oac.client import get_client, LLMClient

client = get_client(provider="anthropic")  # or "openai", "ollama"
# Use with any AgentBase subclass as the `client` parameter
```

---

## Exceptions

| Exception | When raised |
|---|---|
| `PIVOACError` | Base class for all SDK exceptions |
| `AgentUnrecoverableError` | Agent exhausted retries without valid output |
| `GateRejectedError` | A gate explicitly rejected the plan |
| `MalformedOutputError` | Agent output missing required contract fields |
| `VetoError` | Intent validation failed (ethical/security/legal) |
| `CyclicDependencyError` | DAG contains a cycle |

---

## CLI

```bash
piv --help
piv validate [PATH] [--dry-run] [--no-cross-refs] [--no-index]
piv init [--answers YAML] [--root PATH]
piv status [--objective OBJ_ID] [--no-validate]
```
