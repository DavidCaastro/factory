# PIV/OAC SDK — Operational Runbook

Response procedures for each alert and failure state the SDK can emit.

---

## 1. Pre-VETO_SATURACIÓN

**Trigger:** An orchestrator logs `[WARNING] context window at ≥80%`.

**Impact:** Agent may not have enough context to complete its task reliably.

**Response:**
1. Check `.piv/active/<objective-id>_summary.md` — verify the session summary was written before saturation hit.
2. If summary exists: start a new session referencing the objective ID. The framework reloads state from `.piv/active/<objective-id>.json`.
3. If summary is missing or corrupt: reconstruct minimal state from `git log --oneline -20` and `git diff HEAD`.
4. Never continue an 80%+ context session — the agent must escalate before this point per protocol.

**Recovery command:**
```bash
# Inspect current session state
cat .piv/active/<objective-id>.json | python -m json.tool
# Validate summary against JSON (Zero-Trust check)
diff <(jq .phase .piv/active/<objective-id>.json) <(grep '"phase"' .piv/active/<objective-id>_summary.md)
```

---

## 2. GATE_DEADLOCK

**Trigger:** A gate agent (Security, Audit, or Standards) does not respond after 3 invocation attempts, or two gates deadlock waiting on each other.

**Impact:** Pipeline halted at gate; no merge proceeds.

**Response:**
1. Identify which gate is blocked: check the last orchestrator log entry.
2. Re-invoke the stalled agent independently with the same prompt. Timeouts: SecurityAgent/AuditAgent 300 s, orchestrators 600 s.
3. If re-invocation fails 3× → escalate to parent orchestrator → present to user.
4. Do NOT bypass the gate. The `--no-verify` equivalent is prohibited by protocol.

**Diagnostic commands:**
```python
import asyncio, anthropic
from piv_oac.agents import SecurityAgent

async def probe():
    agent = SecurityAgent(client=anthropic.AsyncAnthropic())
    try:
        result = await agent.invoke("Probe: respond with VERDICT: APPROVED, RISK_LEVEL: LOW, FINDINGS: NONE", timeout_seconds=30)
        print("Gate responsive:", result)
    except asyncio.TimeoutError:
        print("Gate timed out — check API connectivity")
    except Exception as e:
        print("Gate error:", e)

asyncio.run(probe())
```

---

## 3. Budget Alert

**Trigger:** Token usage exceeds expected range for the objective (visible in OTel spans or Anthropic usage dashboard).

**Impact:** Cost overrun; possible runaway retry loops.

**Response:**
1. Check `metrics/sessions.md` for token counts from recent sessions.
2. Identify which agent is consuming excess tokens: look for `max_retries` exhaustion patterns in logs.
3. Common causes:
   - Agent stuck in retry loop due to malformed output → fix the system prompt.
   - Oversized context being passed → apply lazy loading (reduce `_get_system_prompt()` size).
   - Orchestrator reloading full spec on every task → cache spec reads.
4. Set a hard budget cap via Anthropic's usage limits dashboard if runaway is confirmed.

**Runbook check:**
```bash
# Count total tokens per session from OTel if enabled
grep "token" logs_veracidad/*.jsonl | tail -20
# Check for retry exhaustion patterns
grep "UNRECOVERABLE_MALFORMED" logs_veracidad/*.jsonl
```

---

## 4. Reliability Alert — asyncio.TimeoutError

**Trigger:** `asyncio.TimeoutError` raised from `agent.invoke()`.

**Impact:** The agent invocation did not complete within `timeout_seconds`.

**Response:**
1. Identify which agent timed out from the stack trace.
2. Default timeouts per `skills/fault-recovery.md`:
   - Specialist/leaf agents: 300 s
   - Domain/Master orchestrators: 600 s
3. If the timeout is consistently hit, the model may be under load. Retry with exponential back-off (max 3×).
4. If retries also time out: check Anthropic status page. Do not loop indefinitely.

**Recovery pattern:**
```python
import asyncio
from piv_oac.agents import SecurityAgent
import anthropic

async def invoke_with_backoff(agent, prompt, retries=3):
    for attempt in range(retries):
        try:
            return await agent.invoke(prompt, timeout_seconds=300)
        except asyncio.TimeoutError:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt  # 1s, 2s, 4s
            await asyncio.sleep(wait)
```

---

## 5. CyclicDependencyError

**Trigger:** `DAGValidator.validate()` raises `CyclicDependencyError`.

**Impact:** Task graph is invalid; no agents should be launched.

**Response:**
1. Read `exc.cycle` attribute — it contains the cycle path as a list of task IDs.
2. Remove the cycle by either:
   - Deleting the back-edge dependency, or
   - Splitting the circular task into two independent tasks.
3. Re-run `DAGValidator(nodes).validate()` before proceeding.

**Never bypass:** launching agents on a cyclic DAG leads to infinite dependency waits.

---

## 6. SHA-256 Mismatch (EngramStore)

**Trigger:** `PIVOACError: SHA-256 mismatch` raised by `EngramStore.read_atom()`.

**Impact:** An engram atom has been tampered with or corrupted. The atom is quarantined.

**Response:**
1. Do NOT silently ignore or overwrite — this is a security signal.
2. Check `engram/_snapshots/<path>/` for the last known-good snapshot.
3. Restore from snapshot: `store.write_atom(path, snapshot_content, "AuditAgent")`.
4. Log the incident in `logs_veracidad/` with the file path and discovery timestamp.
5. Investigate the write path — only `AuditAgent` is authorized to write atoms.

---

## 7. GateRejectedError

**Trigger:** A gate agent returns `REJECTED` verdict (Gate-1, Gate-2, or Gate-3).

**Impact:** Merge is blocked. The corresponding worktree branch is NOT merged.

**Response:**
1. Read `exc.findings` — each finding is an actionable item.
2. Address each finding in the feature branch.
3. Re-submit the plan through the gate (do not skip).
4. Gate-3 rejections require human review — present the full findings to the user.

---

## 8. VetoError

**Trigger:** `SecurityAgent` emits `SECURITY_VETO` or `MasterOrchestrator` emits `VETO_INTENCION`.

**Impact:** Full pipeline halt. No further execution.

**Response:**
1. Read `exc.reason` — the veto reason is always a plain-text explanation.
2. `SECURITY_VETO`: a critical security issue was detected. Fix before re-running.
3. `VETO_INTENCION`: the objective failed ethical/legal validation. Do not retry automatically — present to user for clarification or cancellation.
4. Both veto types are recorded in `logs_veracidad/intent_rejections.jsonl`.
