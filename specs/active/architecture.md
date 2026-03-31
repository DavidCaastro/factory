# Especificaciones de Arquitectura — PIV/OAC Framework v4.0
> Cargado por: Master Orchestrator (construcción del DAG) + Domain Orchestrators
> Referencia de diseño: `docs/redesign/v4.0-rationale.md`
> Este módulo define la estructura del framework directivo y la arquitectura en capas.

---

## Capas del Framework

```
CAPA PROTOCOLO (Marco Directivo)
├── agent.md                     ← Flujo de ejecución por fases (FASE 1..8)
├── CLAUDE.md                    ← Reglas permanentes + catálogo de agentes
├── contracts/                   ← Gates, evaluación, modelos, seguridad paralela
│   ├── gates.md                 ← Gate system + CSP + PMIA
│   ├── evaluation.md
│   ├── models.md
│   └── parallel_safety.md
├── skills/                      ← Skills cargados por agentes (Code Signing vía manifest.json)
│   ├── manifest.json            ← SHA-256 de cada skill (AtomLoader verifica antes de cargar)
│   └── *.md
└── registry/                    ← Definiciones de cada agente
    ├── orchestrator.md
    ├── logistics_agent.md       ← Nuevo v4.0
    ├── execution_auditor.md     ← Nuevo v4.0
    ├── security_agent.md
    ├── audit_agent.md
    └── ...

CAPA SDK (Implementación Python — referenciada, no parte del marco directivo)
└── sdk/piv_oac/                 ← Librería Python que implementa el protocolo
    ├── core/                    ← AgentFactory, GateEnforcer, CryptoValidator, CSP
    ├── agents/                  ← LogisticsAgent, ExecutionAuditor, AgentBase
    ├── state/                   ← StateStore (Filesystem + Redis)
    ├── observability/           ← RealtimeMetrics, Telemetry
    └── ...
```

---

## Stack Tecnológico

| Componente | Tecnología | Versión mínima | Restricción |
|---|---|---|---|
| Lenguaje | Python | 3.12 | Type hints obligatorios en toda función pública |
| Async runtime | asyncio (stdlib) | 3.12 | Sin dependencias de framework async externo |
| Testing | pytest + pytest-asyncio | pytest ≥ 8.0 | — |
| Cobertura | pytest-cov | ≥ 5.0 | Umbral ≥ 90% global |
| Linting | ruff | ≥ 0.4 | 0 errores en CI |
| Type checking | mypy | ≥ 1.8 | strict mode en módulos core/ |
| Seguridad deps | pip-audit | ≥ 2.7 | 0 CVEs críticos/altos |
| Hash / HMAC | hashlib + hmac (stdlib) | 3.12 | Sin dependencias criptográficas externas |
| Serialización | json (stdlib) | 3.12 | — |
| Filesystem async | aiofiles | ≥ 23.0 | Solo para FilesystemStateStore |
| Redis (opcional) | redis[asyncio] | ≥ 5.0 | Solo si REDIS_URL definida en entorno |
| Telemetría (opcional) | opentelemetry-sdk + exporters | ≥ 1.24 | Solo si OTEL_ENDPOINT definida en entorno |

---

## Arquitectura por Capas

```
Config Layer          ← piv_oac.yaml, carga de configuración unificada
      ↓
Governance Layer      ← AgentFactory, PermissionStore, MCPFilter, InheritanceGuard
      ↓
Protocol Layer        ← GateEnforcer, CryptoValidator, AsyncLockManager, CSP
      ↓
Agent Layer           ← AgentBase, LogisticsAgent, ExecutionAuditor, agentes del entorno
      ↓
Infrastructure Layer  ← StateStore, RealtimeMetrics, RollbackManager, ProviderRegistry
      ↓
Memory Layer          ← AtomLoader (Code Signing), SkillRegistry
```

**Regla:** Ninguna capa importa de la capa superior. Violación detectada en Gate 2b.

- `GateEnforcer` (Protocol Layer) usa `StateStore` (Infrastructure Layer) → correcto ↓
- `AgentFactory` (Governance Layer) usa `PermissionStore` (Governance Layer) → mismo nivel, correcto
- `AtomLoader` (Memory Layer) no importa de Agent Layer → correcto
- `AgentBase` (Agent Layer) no importa de `GateEnforcer` (Protocol Layer) → correcto

---

## Estructura de Módulos del Producto

```
sdk/piv_oac/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── factory.py              # AgentFactory (Singleton) + InheritanceGuard
│   ├── base_agent.py           # AgentBase (ABC), AgentContext, SafeAgentContext
│   ├── gate_enforcer.py        # GateEnforcer, GateType, GateVerdict
│   ├── permission_store.py     # PermissionStore, PermissionDenied
│   ├── crypto_validator.py     # CryptoValidator, MessageTampered, MessageExpired
│   ├── csp.py                  # ContextScopeProtocol, ScopedArtifact, AGENT_SCOPES
│   ├── async_lock.py           # AsyncLockManager
│   └── memory/
│       ├── __init__.py
│       ├── atom_loader.py      # AtomLoader, SkillIntegrityError
│       └── skill_registry.py   # SkillRegistry
├── agents/
│   ├── __init__.py
│   ├── logistics.py            # LogisticsAgent, TokenBudgetReport, TaskBudget, TOKEN_CAPS
│   ├── execution_auditor.py    # ExecutionAuditor, ExecutionAuditReport, IrregularityType
│   ├── security.py             # SecurityAgent
│   ├── audit.py                # AuditAgent
│   ├── coherence.py            # CoherenceAgent
│   ├── standards.py            # StandardsAgent
│   ├── compliance.py           # ComplianceAgent
│   └── specialists/
│       └── __init__.py
├── providers/
│   ├── __init__.py
│   ├── base.py                 # LLMProvider (Protocol), ProviderRegistry
│   ├── anthropic.py            # AnthropicProvider (default)
│   ├── openai.py               # OpenAIProvider (opcional)
│   └── google.py               # GoogleProvider (opcional)
├── state/
│   ├── __init__.py
│   ├── store.py                # StateStore (ABC)
│   ├── filesystem.py           # FilesystemStateStore (default)
│   └── redis.py                # RedisStateStore (opcional)
├── observability/
│   ├── __init__.py
│   ├── realtime_metrics.py     # RealtimeMetrics, MetricSnapshot
│   └── telemetry.py            # Telemetry, NoOpTracer
├── recovery/
│   ├── __init__.py
│   └── rollback.py             # RollbackManager, RollbackLevel, RollbackResult
└── config/
    ├── __init__.py
    ├── loader.py                # Carga y valida piv_oac.yaml
    └── piv_oac.yaml             # Configuración unificada del SDK

# Artefactos de datos (no código)
skills/manifest.json             # Hashes SHA-256 de skills (Code Signing — AtomLoader)

# Tests
tests/
├── unit/
│   ├── core/
│   │   ├── test_factory.py
│   │   ├── test_gate_enforcer.py
│   │   ├── test_permission_store.py
│   │   ├── test_crypto_validator.py
│   │   ├── test_csp.py
│   │   └── memory/
│   │       └── test_atom_loader.py
│   ├── agents/
│   │   ├── test_logistics_agent.py
│   │   └── test_execution_auditor.py
│   ├── state/
│   │   └── test_state_store.py
│   └── recovery/
│       └── test_rollback.py
└── integration/
    └── test_gate_flow.py        # Test de flujo completo gate → StateStore → rollback
```

---

## DAG de Tareas

| ID | Tarea | Tipo | Expertos | Depende de | Skills |
|---|---|---|---|---|---|
| T-01 | Core Base — AgentBase, AgentContext, tipos fundamentales, SafeAgentContext | PARALELA | 1 | — | skills/orchestration.md |
| T-02 | Governance Layer — AgentFactory, PermissionStore, MCPFilter, InheritanceGuard | PARALELA | 2 | T-01 | skills/backend-security.md |
| T-03 | Crypto Layer — CryptoValidator (MessageTampered, MessageExpired, validate_with_retry) | PARALELA | 1 | T-01 | skills/backend-security.md |
| T-04 | Infrastructure Layer — StateStore (Filesystem + Redis), AsyncLockManager | PARALELA | 2 | T-01 | skills/orchestration.md |
| T-05 | Gate Enforcement — GateEnforcer + integración CSP + integración AsyncLock | SECUENCIAL | 2 | T-02, T-03, T-04 | skills/orchestration.md |
| T-06 | New Agents — LogisticsAgent (caps) + ExecutionAuditor (out-of-band, fail-safe) | PARALELA | 2 | T-01, T-02, T-04 | skills/orchestration.md |
| T-07 | Memory + Skills — AtomLoader (Code Signing SHA-256) + SkillRegistry + manifest.json | PARALELA | 1 | T-01, T-04 | skills/backend-security.md |
| T-08 | Observability — RealtimeMetrics + RollbackManager + Telemetry (NoOpTracer) | PARALELA | 1 | T-04 | skills/orchestration.md |
| T-09 | Multi-Provider — ProviderRegistry + AnthropicProvider + stubs OpenAI/Google | PARALELA | 1 | T-01 | — |
| T-10 | Config + Wiring — piv_oac.yaml loader, validación de config, tests de integración | SECUENCIAL | 2 | T-01..T-09 | skills/standards.md |

**Ejecución del DAG:**
```
PARALELAS (sin dependencias entre sí):  T-01
PARALELAS (esperan T-01):               T-02, T-03, T-04, T-09
SECUENCIAL (espera T-02+T-03+T-04):    T-05
PARALELAS (esperan T-01+T-02+T-04):    T-06, T-07, T-08
SECUENCIAL (espera todo):               T-10
```

---

## Jerarquía de Agentes v4.0

```
Master Orchestrator (Opus)
├── FASE 1: LogisticsAgent (Haiku) — análisis pre-instanciación, TokenBudgetReport [NUEVO v4.0]
├── FASE 2: Domain Orchestrators (Sonnet)
│   ├── SecurityAgent (Opus/Sonnet)   — gate_2, gate_2b, gate_3
│   ├── AuditAgent (Sonnet)            — gate_2, gate_2b, gate_3
│   ├── CoherenceAgent (Sonnet)        — gate_1
│   ├── StandardsAgent (Sonnet)        — gate_2b, gate_3
│   └── ExecutionAuditor (Haiku)       — observador OOB FASE 2→8 [NUEVO v4.0]
└── FASE 4..7: Expertos de implementación (según tarea)
```

## Flujo de Métricas v4.0

```
RealtimeMetrics (siempre activo)
  └── captura tokens/costo por agente en cada llamada LLM
        └── ExecutionAuditor (observador OOB)
              └── agrega irregularidades + snapshot final
                    └── metrics/sessions.md (registrado por AuditAgent en FASE 8)
```

## Gestión de Orquestación (OAC)

- **Aislamiento:** Worktrees por experto (`./worktrees/<tarea>/<experto>/`)
- **Flujo de ramas:** `feature/<tarea>/<experto>` → `feature/<tarea>` → `staging` → `main`
- **Modelo de razonamiento:** Opus para planificación del DAG y SecurityAgent; Sonnet para Domain Orchestrators y agentes de gate; Haiku para LogisticsAgent, ExecutionAuditor y validaciones mecánicas
- **src_dir:** `sdk/piv_oac/` — directorio raíz de módulos Python para herramientas (pytest-cov, ruff, mypy)

---

## Historial de Versiones

| Versión | Fecha | Cambio principal |
|---|---|---|
| v4.0 | 2026-03-31 | Separación explícita CAPA PROTOCOLO / CAPA SDK. Nuevos agentes: LogisticsAgent, ExecutionAuditor. Flujo de métricas v4.0. |
| v3.2 | 2026-03-30 | Arquitectura inicial SDK v4.0 |
