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

## [Unreleased]

### Planned for 0.2.0
- CLI: `piv-oac init`, `piv-oac run <objective>`
- Integration tests against real Anthropic API (opt-in, requires `ANTHROPIC_API_KEY`)
- Prometheus alerting rules for gate states
- Grafana dashboard for agent spans
- `CONTRIBUTING.md` and community guidelines
