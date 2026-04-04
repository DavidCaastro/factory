# Changelog — piv-oac

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.0] — 2026-03-17

### Added

**Agents**
- `SecurityAgent` — security review with VERDICT/RISK_LEVEL/FINDINGS contract; optional `SECURITY_VETO` hard-halt
- `AuditAgent` — RF coverage audit with RF_COVERAGE/SCOPE_VERDICT contract
- `CoherenceAgent` — Gate-1 coherence check with GATE1_VERDICT/CONFLICT_LEVEL/CONFLICTS contract
- `StandardsAgent` — Gate-2 code quality gate; raises `GateRejectedError` on REJECTED
- `ComplianceAgent` — Gate-3 legal/regulatory evaluation with mandatory `COMPLIANCE_DISCLAIMER`; raises `ValueError` on `compliance_scope="NONE"`
- `DomainOrchestrator` — domain-level task coordinator with `parse_worktrees()` static method
- `SpecialistAgent` — atomic task implementor with IMPLEMENTATION/FILES_CHANGED/TESTS_ADDED/RF_ADDRESSED contract
- `AgentBase.invoke()` — retry loop (up to `max_retries`), OTel span, `timeout_seconds` via `asyncio.wait_for()`

**Orchestration**
- `MasterOrchestrator` — top-level pipeline client; raises `VetoError` on `VETO_INTENCION`

**DAG**
- `DAGNode` + `DAGValidator` — DFS cycle detection, Kahn topological sort, parallel wave grouping
- `CyclicDependencyError` — raised before any agent is launched on a cyclic graph

**Contracts**
- `ContractParser` — regex-based parser for structured agent output; `MalformedOutputError` on missing fields

**Checkpoint**
- `CheckpointStore` — atomic JSON writes to `.piv/active/`; `load()` returns `None` on corrupt/missing; `complete()`/`fail()` lifecycle management

**Engram**
- `EngramStore` — SHA-256 integrity headers, version snapshots, `AuditAgent`-only write enforcement, path traversal protection

**Client**
- `AnthropicClient` — wraps `anthropic.AsyncAnthropic`; returns `(text, tokens_in, tokens_out)`
- `OpenAIClient` — wraps `openai.AsyncOpenAI` (optional dep: `pip install piv-oac[openai]`)
- `OllamaClient` — wraps `httpx.AsyncClient` for local Ollama server at `/api/chat`
- `get_client(provider)` — factory function, case-insensitive, raises `ValueError` on unknown provider

**Telemetry**
- `setup_tracing()` — OTel TracerProvider with OTLP gRPC export; no-op when disabled or OTel not installed
- `agent_span()` — context manager that emits `piv_oac.agent.<AgentType>` spans

**Exceptions**
- `PIVOACError` — base exception
- `AgentUnrecoverableError(agent_type, failure_type, detail)`
- `GateRejectedError(gate, findings)`
- `VetoError(agent_type, reason)`
- `MalformedOutputError(agent_type, raw_output, missing_fields)`

**Tests**
- 155 tests across 13 test files; coverage ≥ 94%

**Documentation**
- `docs/getting-started.md` — 5-step quickstart with full pipeline example
- `docs/runbook.md` — 8 operational procedures (VETO_SATURACIÓN, GATE_DEADLOCK, Budget Alert, TimeoutError, CyclicDependencyError, SHA-256 mismatch, GateRejectedError, VetoError)
- `docs/deployment.md` — infrastructure setup, OTel Collector with Docker, production checklist

**Configuration**
- `mypy` configured in `pyproject.toml` (strict type checking for `piv_oac/`)
- `pytest-cov` with `fail_under=80`
- `asyncio_mode = "auto"` for async tests

---

## [0.2.0] — 2026-04-04

### Added

**Agents — pipeline support (closes registry gap vs agent-configs v4.0)**
- `LogisticsAgent` — token budget estimator active in FASE 1 (Nivel 2 objectives);
  produces `TOTAL_ESTIMATED_TOKENS`, `FRAGMENTATION_RECOMMENDED`, and
  `WARNING_ANOMALOUS_ESTIMATE` when a task exceeds its cap.
  Includes `TOKEN_CAPS` constants and `estimate_cost()` static helper.
- `ExecutionAuditor` — passive out-of-band observer FASE 2→8; records
  irregularities (GATE_SKIPPED, GATE_BYPASSED, PROTOCOL_DEVIATION,
  TOKEN_OVERRUN, CONTEXT_SATURATION, UNAUTHORIZED_INSTANTIATION) without
  intervening in gates. `generate_report()` always returns — never raises.
- `DocumentationAgent` — temporary specialist that generates missing
  product documentation for Gate 3 when StandardsAgent emits
  `GATE_3_DOCS_BLOQUEADO`. Uses `[COMPLETAR: ...]` placeholders for
  missing spec data.

**Tests**
- `tests/test_new_agents.py` — 18 tests covering all three new agents

---

## [0.3.0] — 2026-04-04

### Added

**PMIA — Protocolo de Mensaje Inter-Agente** (`piv_oac.pmia`)
- `GateVerdictMessage`, `EscalationMessage`, `CrossAlertMessage`, `CheckpointReqMessage`
  — typed, immutable, JSON-serializable message dataclasses per `skills/inter-agent-protocol.md`
- `IssueEntry` — 50-token enforced issue descriptor for gate verdicts
- `ControlEnvironmentState` — snapshot of all control agent statuses for CHECKPOINT_REQ
- `CryptoValidator` — HMAC-SHA256 sign + verify; raises `MessageTampered` on bad signature
  (no retry) and `MessageExpired` on TTL exceeded (retry path)
- `PMIABus` — in-process asyncio message bus: routes by type, validates structure + signature,
  handles 2-retry protocol on `MALFORMED_MESSAGE`, escalates to MasterOrchestrator on exhaustion;
  exposes `metrics` (total, retries, escalations, retry_rate)
- `CROSS_ALERT_AUTHORIZED` — frozenset enforcing that only control agents emit lateral alerts
- `MAX_TOKENS_PER_MESSAGE = 300` — hard limit constant

**SafeLocalExecutor** (`piv_oac.tools`)
- `SafeLocalExecutor` — allowlist-only subprocess runner; agents delegate to
  `worktree_init` (`tools/worktree-init.sh`) and `validate_specs` (`tools/validate-specs.py`)
  without exposing full LLM context; output truncated to 32 KB before returning to agents
- `ExecutionDataFilter` — rejects credentials, shell injection patterns, path traversal,
  and disallowed characters before any subprocess is created; `shell=False` always
- `ExecutionResult` — structured result with `success`, `returncode`, `stdout`, `stderr`,
  `truncated`, and `to_agent_summary()` for safe embedding in agent prompts

**Onboarding**
- `docs/getting-started.md` — full rewrite: visual agent hierarchy diagram, 5-minute
  quick start, 4-level learning path (single agent → parallel pipeline → PMIA → local tools),
  error handling guide, multi-provider and telemetry sections

**Tests**
- `tests/test_pmia.py` — 22 tests covering all message types, CryptoValidator, PMIABus routing
- `tests/test_local_executor.py` — 22 tests covering filter and executor

Total: 272 tests, coverage 90.53%

---

## [Unreleased]

### Planned
- Integration tests against real Anthropic API (opt-in, requires `ANTHROPIC_API_KEY`)
- Prometheus alerting rules for gate states
- Grafana dashboard for agent spans
- `CONTRIBUTING.md` and community guidelines
