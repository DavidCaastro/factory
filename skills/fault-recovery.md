# Skill: Fault Recovery Protocol — PIV/OAC v3.2

**Gap:** G-03 — Fault detection, retry, escalation, and recovery for inter-agent failures
**Status:** Active
**Applies to:** All agents and orchestrators operating within a PIV/OAC pipeline
**Integrates with:** `skills/agent-contracts.md` (G-07), `skills/context-management.md`

---

## Motivation

In multi-agent pipelines, partial failures are inevitable. Without a defined recovery protocol, a single agent timeout or malformed response can silently corrupt the pipeline state or leave it deadlocked. This document defines canonical fault types, retry strategies, model fallback chains, checkpoint discipline, and resolution procedures for each fault class recognized by the framework.

---

## 1. Tipos de Fallo Reconocidos

| Fault Type | Description | Default Timeout / Trigger |
|---|---|---|
| `AGENT_TIMEOUT` | Agent does not respond within its time limit | 5 min (SpecialistAgent), 10 min (Orchestrator) |
| `MALFORMED_OUTPUT` | Response does not comply with the contract in `skills/agent-contracts.md` after 2 retries | 2 retries exhausted |
| `SECURITY_VETO` | SecurityAgent emits a `SECURITY_VETO` that cannot be resolved within the current pipeline scope | Unresolvable veto present |
| `CONTEXT_OVERFLOW` | `VETO_SATURACIÓN` unresolvable at pipeline level — handled by context-management protocol | See `skills/context-management.md` §4 |
| `WORKTREE_CONFLICT` | Merge conflict detected between expert sub-branches during integration | Merge step failure |
| `GATE_DEADLOCK` | A gate reaches a 2nd consecutive rejection of the same plan without resolution | 2nd rejection (same plan) |
| `EXTERNAL_API_FAILURE` | Call to Anthropic API fails — timeout, rate limit, or HTTP 5xx | Any of the above |

`CONTEXT_OVERFLOW` is fully governed by `skills/context-management.md`. The present document does not duplicate that protocol; fault handlers that encounter a `VETO_SATURACIÓN` must delegate to that skill directly.

---

## 2. Retry con Backoff Exponencial

Applies to: `AGENT_TIMEOUT`, `EXTERNAL_API_FAILURE`

| Attempt | Wait before retry | Action |
|---|---|---|
| Retry 1 | 5 seconds | Re-invoke the same agent with the same prompt |
| Retry 2 | 15 seconds | Re-invoke the same agent with the same prompt |
| Retry 3 | 60 seconds | Re-invoke the same agent with the same prompt |
| After retry 3 fails | — | Emit `AGENT_UNRECOVERABLE` to the parent orchestrator |

The invoking orchestrator is responsible for tracking the attempt counter and enforcing wait times. Between retries, the orchestrator must not invoke any downstream agents that depend on the failing agent's output.

**Emit format when escalating:**

```
FAILURE_TYPE: AGENT_UNRECOVERABLE
FAILED_AGENT: <agent_type>
ORIGINAL_FAULT: AGENT_TIMEOUT | EXTERNAL_API_FAILURE
ATTEMPTS: 3
```

---

## 3. Fallback de Modelo

If an agent running on Opus fails repeatedly (exhausts retries per §2):

1. Degrade to **Sonnet** for the same prompt — reset the retry counter and apply the backoff sequence again.
2. If Sonnet also exhausts retries: degrade to **Haiku** — reset and retry.
3. If Haiku exhausts retries: emit `AGENT_UNRECOVERABLE` to the parent orchestrator with `MODEL_CHAIN_EXHAUSTED: true`.

```
FAILURE_TYPE: AGENT_UNRECOVERABLE
FAILED_AGENT: <agent_type>
ORIGINAL_FAULT: <fault_type>
MODEL_CHAIN_EXHAUSTED: true
MODELS_TRIED: opus, sonnet, haiku
```

Model degradation is transparent to the rest of the pipeline — only the invoking orchestrator is aware of the downgrade. Cost implications of retries must be tracked in the session cost log per `skills/cost-control.md`.

---

## 4. Checkpoint Antes de Acción Riesgosa

Any agent about to perform an irreversible action (merge, delete, push, destructive file overwrite) must follow this sequence exactly:

1. **Write checkpoint** to `.piv/active/<objetivo-id>.json` with the following fields:

   ```
   CHECKPOINT_AGENT: <agent_type>
   CHECKPOINT_ACTION: <description of the irreversible action>
   CHECKPOINT_STATE: <summary of current pipeline state relevant to the action>
   CHECKPOINT_TIMESTAMP: <ISO-8601 timestamp>
   ```

2. **Verify** that the checkpoint was written successfully — read back the file and confirm the entry is present.

3. **Only then** execute the irreversible action.

If the checkpoint write fails (filesystem error, permission denied), the agent must **abort the irreversible action** and emit `FAILURE_TYPE: CHECKPOINT_WRITE_FAILED` to its parent orchestrator. The parent must decide whether to retry or halt.

This rule is not optional. An agent that skips the checkpoint and proceeds with an irreversible action is in protocol violation.

---

## 5. Protocolo de Recuperación por Tipo de Fallo

### 5.1 AGENT_TIMEOUT

| Role | Agent |
|---|---|
| Detects | Parent orchestrator (timer expires) |
| Resolves | Parent orchestrator via retry with backoff (§2) |
| Action | Apply §2 retry sequence; if exhausted, apply §3 model fallback |
| Escalates when | `MODEL_CHAIN_EXHAUSTED` — emit `AGENT_UNRECOVERABLE` to grandparent orchestrator |

### 5.2 MALFORMED_OUTPUT

| Role | Agent |
|---|---|
| Detects | Consuming agent or orchestrator (contract parsing fails per `skills/agent-contracts.md` §3.3) |
| Resolves | Consuming agent re-requests with the missing field specified in the error message |
| Action | Maximum 2 retries per `skills/agent-contracts.md` §3.3; no backoff delay required |
| Escalates when | Field still absent after 2 retries — emit `AGENT_UNRECOVERABLE` with `ORIGINAL_FAULT: MALFORMED_OUTPUT` |

### 5.3 SECURITY_VETO

| Role | Agent |
|---|---|
| Detects | Any orchestrator that receives `SECURITY_VETO` from SecurityAgent |
| Resolves | Cannot be auto-resolved within current scope |
| Action | Halt pipeline immediately; propagate `SECURITY_VETO` upward to MasterOrchestrator |
| Escalates when | MasterOrchestrator receives veto — present to user with reason; no automatic override |

### 5.4 CONTEXT_OVERFLOW

Delegated entirely to `skills/context-management.md` §4 (VETO_SATURACIÓN protocol). Fault-recovery handlers that encounter this condition must invoke that protocol directly without intercepting the escalation chain.

### 5.5 WORKTREE_CONFLICT

See §6 for the full resolution procedure.

| Role | Agent |
|---|---|
| Detects | DomainOrchestrator or CoherenceAgent during integration step |
| Resolves | CoherenceAgent (first pass); DomainOrchestrator (second pass); MasterOrchestrator (final escalation) |
| Action | Per §6 |
| Escalates when | CoherenceAgent cannot resolve same-file conflict — escalate to DomainOrchestrator |

### 5.6 GATE_DEADLOCK

See §7 for the full resolution procedure.

| Role | Agent |
|---|---|
| Detects | Gate-managing orchestrator (2nd consecutive rejection of same plan) |
| Resolves | User (mandatory — no automatic resolution) |
| Action | Per §7 |
| Escalates when | Immediately on detection — do not attempt a 4th iteration |

### 5.7 EXTERNAL_API_FAILURE

| Role | Agent |
|---|---|
| Detects | Any agent that invokes an Anthropic API endpoint |
| Resolves | The invoking agent applies backoff (§2) and model fallback (§3) |
| Action | Log HTTP status code and error body in each retry attempt; include in `AGENT_UNRECOVERABLE` payload |
| Escalates when | Full retry + fallback chain exhausted |

---

## 6. WORKTREE_CONFLICT — Resolución

**Trigger:** A merge step detects a conflict between two or more expert sub-branches.

**Resolution sequence:**

1. **CoherenceAgent attempts automatic merge.**
   - Eligible for automatic merge: changes affect distinct files with no overlapping edits.
   - If automatic merge succeeds, CoherenceAgent emits:
     ```
     COHERENCE_STATUS: CONSISTENT
     GATE1_VERDICT: APPROVED
     CONFLICTS: NONE
     ```
   - CoherenceAgent must write a checkpoint to `.piv/active/<objetivo-id>.json` before executing the merge (§4 applies — merge is irreversible).

2. **Same-file conflict — escalate to DomainOrchestrator.**
   - If two experts modified the same file in incompatible ways, automatic merge is not safe.
   - CoherenceAgent emits:
     ```
     COHERENCE_STATUS: CONFLICT_DETECTED
     GATE1_VERDICT: REJECTED
     CONFLICT: expert_a=<name> expert_b=<name> conflict_type=same_file_edit resolution=PENDING_MANUAL
     ```
   - DomainOrchestrator reviews both versions and decides which to keep or how to merge them manually.
   - DomainOrchestrator must write a checkpoint before applying the manual resolution.

3. **DomainOrchestrator cannot resolve — escalate to MasterOrchestrator.**
   - If the conflict requires cross-domain architectural decisions that exceed the DomainOrchestrator's scope, MasterOrchestrator is invoked.
   - MasterOrchestrator may present the conflict to the user if a product-level decision is required.

---

## 7. GATE_DEADLOCK — Resolución

**Trigger:** A gate receives a 2nd consecutive rejection of the same plan (see `contracts/gates.md §Definición de "mismo plan"`). Escalate immediately — do not attempt a 3rd iteration of the same plan.

**Resolution sequence:**

1. **AuditAgent documents the deadlock.**
   - AuditAgent writes a structured entry to `engram/core/architecture_decisions.md` listing:
     - The gate that is deadlocked.
     - All iteration outcomes (what was rejected each time and why).
     - The unresolved points of disagreement between reviewers.
   - AuditAgent emits:
     ```
     AUDIT_RESULT: FAIL
     SCOPE_VIOLATIONS: GATE_DEADLOCK — <gate_name> — 2nd consecutive same-plan rejection
     ENGRAM_WRITE: engram/core/architecture_decisions.md
     ```

2. **MasterOrchestrator presents options to the user.**
   - Execution is paused. MasterOrchestrator presents the user with the documented disagreement and exactly three options:
     - **(a)** Reduce the scope of the current plan to remove the contested elements and re-enter the gate.
     - **(b)** Accept the plan as-is with the risk formally documented in engram.
     - **(c)** Cancel the current task entirely.

3. **The user decides — no automatic resolution.**
   - Gate deadlocks are not overridable by any agent autonomously.
   - After the user selects an option, MasterOrchestrator resumes the pipeline accordingly.
   - If option (b) is selected, AuditAgent records the accepted risk in `engram/core/architecture_decisions.md` before execution continues.

---

## 8. Integración con agent-contracts.md

### 8.1 Campo FAILURE_TYPE en contratos de agentes

When an agent emits a fault signal, it must append a `FAILURE_TYPE` field to its structured output block. This field follows the same canonical English format defined in `skills/agent-contracts.md` §2.

Extended contract fields for fault emission:

```
FAILURE_TYPE: AGENT_TIMEOUT | MALFORMED_OUTPUT | SECURITY_VETO | WORKTREE_CONFLICT | GATE_DEADLOCK | EXTERNAL_API_FAILURE | AGENT_UNRECOVERABLE | CHECKPOINT_WRITE_FAILED
FAILURE_DETAIL: <plain-text description of the specific failure>
```

`FAILURE_TYPE` is only emitted when a fault is being reported. It must not appear in successful responses.

### 8.2 Campos requeridos por agente al reportar fallo

| Agent | Required fields on fault emission |
|---|---|
| Any agent | `FAILURE_TYPE`, `FAILURE_DETAIL` |
| Agent after retry exhaustion | + `ATTEMPTS`, `ORIGINAL_FAULT` |
| Agent after model chain exhaustion | + `MODEL_CHAIN_EXHAUSTED`, `MODELS_TRIED` |
| CoherenceAgent on WORKTREE_CONFLICT | + `COHERENCE_STATUS: CONFLICT_DETECTED`, standard `CONFLICT:` lines |
| Gate-managing orchestrator on GATE_DEADLOCK | + `AUDIT_RESULT: FAIL`, `SCOPE_VIOLATIONS` |

### 8.3 Parsing de FAILURE_TYPE por el orquestador padre

The parent orchestrator reads `FAILURE_TYPE` from the child agent's output using the standard regex pattern:

```
^FAILURE_TYPE:\s+(.+)$
```

Once `FAILURE_TYPE` is extracted, the orchestrator routes to the appropriate protocol section of this document. The routing table is:

| FAILURE_TYPE value | Protocol section |
|---|---|
| `AGENT_TIMEOUT` | §2 + §5.1 |
| `MALFORMED_OUTPUT` | §5.2 |
| `SECURITY_VETO` | §5.3 |
| `CONTEXT_OVERFLOW` | `skills/context-management.md` §4 |
| `WORKTREE_CONFLICT` | §6 |
| `GATE_DEADLOCK` | §7 |
| `EXTERNAL_API_FAILURE` | §2 + §5.7 |
| `AGENT_UNRECOVERABLE` | Escalate to grandparent orchestrator immediately |
| `CHECKPOINT_WRITE_FAILED` | Abort irreversible action; parent decides retry or halt |

---

## 9. Tabla de Referencia Cruzada

| Document | Relationship |
|---|---|
| `skills/agent-contracts.md` | Defines the output contract fields that fault handlers parse; `FAILURE_TYPE` is an extension of those contracts |
| `skills/context-management.md` | Owns `CONTEXT_OVERFLOW` / `VETO_SATURACIÓN` protocol; this document defers to it |
| `skills/cost-control.md` | Model fallback (§3) generates retry token costs that must be tracked per cost-control rules |
| `skills/worktree-automation.md` | `WORKTREE_CONFLICT` resolution (§6) interacts with the worktree lifecycle managed by this skill |
| `.piv/active/<objetivo-id>.json` | Checkpoint target for irreversible actions (§4) |
| `engram/core/architecture_decisions.md` | Gate deadlock documentation target (§7) |
