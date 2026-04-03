# PIV/OAC — Paradigma de Intencionalidad Verificable / Orquestación Atómica de Contexto

> **Version:** v4.0 | **Rama directiva:** `agent-configs` | **SDK Python:** `piv-oac`
> Esta rama contiene exclusivamente la configuración del sistema de agentes. No contiene código de aplicación.
> El código producido por este marco vive en las ramas artifact (`main`, `staging`, `feature/*`).

---

## Instalación rápida

```bash
pip install piv-oac          # desde PyPI
# o desde el repo:
pip install -e sdk/
```

```python
import asyncio, anthropic
from piv_oac import MasterOrchestrator, SecurityAgent

async def main():
    client = anthropic.AsyncAnthropic()
    mo = MasterOrchestrator(client=client, model="claude-opus-4-6")
    plan = await mo.dispatch("Build a REST API with JWT auth")
    print(plan["CLASSIFICATION"])       # NIVEL_1 | NIVEL_2
    print(plan["BUDGET_ESTIMATE_USD_EST"])

asyncio.run(main())
```

Valida tu entorno antes de empezar:
```bash
python scripts/validate_env.py
```

---

## ¿Por qué PIV/OAC?

| Problema en frameworks convencionales | Solución PIV/OAC |
|---|---|
| Agentes generan código sin validar la intención | Validación de intención obligatoria antes de toda ejecución |
| Un solo agente satura su contexto con el repo completo | Lazy loading — cada agente carga solo lo mínimo necesario |
| Seguridad y auditoría son pasos finales opcionales | SecurityAgent + AuditAgent con veto pre-código, siempre activos |
| No hay control humano sobre qué va a producción | Gate 3 bloqueante — `main` nunca se toca sin confirmación explícita |
| Las decisiones técnicas se pierden entre sesiones | Sistema Engram atomizado persiste memoria por dominio de agente |
| Vendor lock-in al proveedor LLM | Multi-provider: Anthropic, OpenAI, Ollama |

**Diferenciadores frente al mercado:**

| Feature | PIV/OAC | LangGraph | AutoGen | CrewAI |
|---|---|---|---|---|
| Gates de seguridad bloqueantes multi-agente | ✅ | ❌ | ❌ | ❌ |
| Gate 3 humano (nunca auto-merge a main) | ✅ | Parcial | ❌ | ❌ |
| ComplianceAgent con disclaimer legal | ✅ | ❌ | ❌ | ❌ |
| Validación de intención antes de ejecución | ✅ | ❌ | ❌ | ❌ |
| Continuidad de sesión con checkpoint Zero-Trust | ✅ | Parcial | ❌ | ❌ |
| Modo RESEARCH con gate epistémico | ✅ | ❌ | ❌ | ❌ |
| VETO_SATURACIÓN con cascada de escalado | ✅ | ❌ | ❌ | ❌ |

---

## ¿Qué es PIV/OAC?

**PIV** (Paradigma de Intencionalidad Verificable) + **OAC** (Orquestación Atómica de Contexto) es un marco operativo para desarrollo guiado por agentes de IA que resuelve tres problemas estructurales del uso convencional de LLMs en ingeniería de software:

| Problema convencional | Solución PIV/OAC |
|---|---|
| El agente genera código sin validar la intención real | Toda acción se valida contra una especificación documentada antes de ejecutarse |
| Un solo agente satura su ventana de contexto con todo el repo | Cada agente recibe solo el contexto mínimo necesario para su tarea (lazy loading) |
| La seguridad y auditoría son pasos finales opcionales | SecurityAgent, AuditAgent y CoherenceAgent corren desde el inicio con capacidad de veto pre-código |
| Las decisiones técnicas se pierden entre sesiones | El sistema Engram persiste las decisiones para que el agente no empiece desde cero |
| Los agentes "paralelos" se ejecutan secuencialmente en la práctica | `run_in_background=True` en múltiples Agent calls del mismo mensaje activa paralelismo real |

---

## Arquitectura del Sistema

Jerarquía de tres niveles. Cada nivel tiene scope, responsabilidades y modelo de IA diferente.

```
┌──────────────────────────────────────────────────────────────────┐
│                    MASTER ORCHESTRATOR (Nivel 0)                  │
│  Recibe objetivo → construye DAG → presenta al usuario → delega  │
│  Nunca escribe código. Nunca lee archivos de implementación.      │
└──────────────────────────┬───────────────────────────────────────┘
                           │ crea entorno de control
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌────────────┐  ┌────────────┐  ┌─────────────────┐
   │  SECURITY  │  │   AUDIT    │  │   COHERENCE     │
   │   AGENT    │  │   AGENT    │  │     AGENT       │
   │ Veto sobre │  │Trazabilidad│  │ Consistencia    │
   │ planes y   │  │y veracidad │  │ entre expertos  │
   │ código     │  │            │  │ paralelos       │
   └────────────┘  └────────────┘  └─────────────────┘
                           │
                           │ crea agentes de ejecución
                           ▼
                   DOMAIN ORCHESTRATORS (Nivel 1)
                   Uno por dominio del DAG
                           │
                           ▼
                   SPECIALIST AGENTS (Nivel 2)
                   N expertos por tarea, en subramas aisladas
```

---

## El Entorno de Control — Gate Bloqueante

Ninguna línea de código se escribe sin pasar este gate. Los tres agentes de control revisan **en paralelo** el plan de cada tarea:

```
Domain Orchestrator genera plan
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
Security    Audit   Coherence
patrones  trazabil  viabilidad
seguros    idad    ejecución
    │         │    paralela
    └─────────┼─────────┘
              │
   ¿Los tres aprueban?
              │
   NO ────────┴──────── SÍ
   │                     │
   ▼                     ▼
Plan revisado      Crear worktrees
→ repetir gate     y expertos
```

- **SecurityAgent (Opus):** verifica patrones de seguridad, ausencia de secretos, RF cubiertos. Tiene veto.
- **AuditAgent (Sonnet):** verifica trazabilidad a RF, coherencia de scope y arquitectura correcta.
- **CoherenceAgent (Sonnet):** detecta conflictos entre expertos paralelos (semánticos y técnicos de git). Fuerza acuerdos antes de que los expertos escriban código.

---

## Tipología de Ramas

El repositorio distingue dos tipos de rama con propósitos y ciclos de vida distintos:

### Rama Directive
Contiene las directivas que gobiernan el comportamiento del sistema de agentes. No produce artefactos ejecutables. No recibe merges desde ramas artifact. Versiona independientemente el marco operativo.

| Rama | Propósito |
|---|---|
| `agent-configs` | Marco PIV/OAC: CLAUDE.md, skills, registry, engram, protocolos de gates |

### Ramas Artifact
Contienen los artefactos producidos por el sistema de agentes. Su ciclo de vida está gobernado por las directivas de la rama directive.

| Rama | Subtipo | Propósito |
|---|---|---|
| `main` | delivery | Producción. Solo recibe merges desde `staging` con confirmación humana explícita |
| `staging` | integration | Pre-producción. Integración de todas las tareas. Gate final antes de `main` |
| `feature/<tarea>` | execution | Rama de tarea (Nivel 2). Integra el trabajo de los expertos de esa tarea |
| `feature/<tarea>/<experto>` | execution | Subrama de experto. Aislamiento atómico de cada especialista |
| `fix/<nombre>` | execution | Rama de micro-tarea (Nivel 1). Todo cambio — sin excepción de nivel — parte de aquí |

---

## Flujo de Ramas Artifact (Tres Niveles)

```
[directive]  agent-configs  ← gobierna el proceso, no participa en el flujo de merge

[artifact]   main           ← delivery. Confirmación humana explícita requerida.
             └── staging    ← integration. Gate final Security + Audit + humano.
                 ├── fix/<nombre>                 ← execution (Nivel 1: micro-tarea)
                 └── feature/<tarea>              ← execution (Nivel 2)
                     ├── feature/<tarea>/experto-1  ← execution (paralela)
                     └── feature/<tarea>/experto-2  ← execution (paralela)
```

**Merge en tres gates:**
```
feature/<tarea>/experto-N  [execution]
    │  GATE 1: CoherenceAgent autoriza
    ▼
feature/<tarea>            [execution]
    │  GATE 2: Security + Audit aprueban
    ▼
staging                    [integration]
    │  GATE 3: revisión humana + Security + Audit
    ▼
main                       [delivery] ← solo con confirmación humana explícita
```

---

## Clasificación de Tareas

Antes de actuar, toda tarea se clasifica en uno de dos niveles:

### Nivel 1 — Micro-tarea
Se cumplen **todos** los criterios: ≤ 2 archivos afectados, sin arquitectura nueva, RF documentado, riesgo bajo.
**Protocolo:** Sin orquestación formal, pero **branch-first obligatorio**: crear `fix/<nombre>` desde la rama base y promover hacia adelante (`fix/` → `staging` → `main`). Nunca commitear directamente en `staging` o `main`. Zero-Trust y lazy loading aplican igual.

### Nivel 2 — Feature / POC / Objetivo complejo
Cualquiera de: archivos nuevos, ≥ 3 archivos, arquitectura nueva, RF nuevo o ambiguo, impacto en seguridad.
**Protocolo:** Orquestación completa con DAG, entorno de control, gates bloqueantes y merge en tres niveles.

**Escalado automático:** Nivel 1 que crece en scope → escala a Nivel 2 con notificación al usuario.

---

## Asignación Dinámica de Modelo

La capacidad se asigna por dimensión de razonamiento, no por jerarquía fija:

| Condición | Modelo |
|---|---|
| Alta ambigüedad / alto riesgo / múltiples trade-offs / construcción de DAG | claude-opus-4-6 |
| Planificación estructurada / coordinación / generación con patrones | claude-sonnet-4-6 |
| Transformaciones mecánicas / lookups / formateo / validación clara | claude-haiku-4-5 |

Cualquier agente puede solicitar escalado si detecta que su tarea supera su capacidad asignada.

---

## Gestión de Contexto por Abstracción (Lazy Loading)

- **Master Orchestrator:** Solo objetivos, DAG y estado de entorno. No lee código.
- **Domain Orchestrators:** Solo spec de su dominio + skill relevante de `/skills/`.
- **Specialist Agents:** Solo scope de su subrama + outputs necesarios de dependencias.
- **CoherenceAgent:** Solo diffs entre subramas, no el código completo de cada experto.

---

## Sistema Engram — Memoria Persistente

Resuelve la "amnesia agéntica": pérdida de decisiones técnicas entre sesiones.

- **Escritura exclusiva:** Solo AuditAgent escribe en los átomos de `engram/`.
- **Lectura libre:** Cualquier agente puede consultarlo al inicio de una tarea.
- **Contenido:** Decisiones técnicas, patrones reutilizables, resultado de gates, observaciones para la próxima sesión.
- **No contiene:** Ningún valor del vault, ninguna credencial, ningún dato sensible.

---

## Principios Zero-Trust (todos los agentes, siempre)

1. **Vault restringido:** Ningún agente lee `security_vault.md` sin instrucción humana explícita en el turno activo
2. **Credenciales solo vía MCP:** Nunca en la ventana de contexto de ningún agente
3. **Veto de SecurityAgent:** Detiene cualquier plan o acción que represente un riesgo
4. **Anti Prompt Injection:** Veto automático + notificación al usuario
5. **Logs limpios:** AuditAgent verifica que ningún valor sensible aparezca en los logs

---

## Estructura de Archivos

```
agent-configs/
│
├── CLAUDE.md                         ← Entrypoint operativo (carga obligatoria por Claude Code)
├── LAYERS.md                         ← Contrato de separación de capas (framework/proyecto/runtime)
├── agent.md                          ← Marco operativo completo PIV/OAC v4.0
├── security_vault.md                 ← Acceso restringido (Zero-Trust)
│
├── contracts/                        ← Primitivas canónicas compartidas (CAPA 1 — FRAMEWORK)
│   ├── gates.md                     ← Fuente única de Gate 1, 2, 2b, 3
│   ├── models.md                    ← Tabla de asignación de modelos por agente
│   ├── evaluation.md                ← Rubric de scoring 0-1 + resource policy + schema JSONL
│   └── parallel_safety.md           ← Reglas de aislamiento para grupos paralelos
│
├── specs/                            ← Contrato de Ejecución Verificable
│   ├── _templates/                  ← Plantillas inmutables del framework (nunca modificar)
│   └── active/                      ← Specs del proyecto activo (gitignored en agent-configs)
│
├── skills/                           ← Skills de carga perezosa por agente (~28 skills)
│   ├── orchestration.md             ← Construcción de DAG (Master Orchestrator)
│   ├── agent-factory.md             ← Protocolo AgentFactory — instanciación controlada
│   ├── inter-agent-protocol.md      ← PMIA, HMAC, TTL de contexto heredado
│   ├── context-management.md        ← Lazy loading, CSP, VETO_SATURACIÓN
│   ├── session-continuity.md        ← Checkpoints, triggers T-a/T-b/T-c
│   ├── cost-control.md              ← TokenBudgetReport, caps por nivel
│   ├── observability.md             ← Telemetría OTEL, trazabilidad
│   ├── framework-quality.md         ← Framework Quality Gate (MODO_META)
│   ├── init.md                      ← Bootstrap de nuevo proyecto (execution_mode: INIT)
│   ├── evaluation.md                ← Scoring 0-1, EvaluationAgent, precedentes
│   ├── compliance.md                ← Perfil legal, GDPR, Documento de Mitigación
│   ├── product-docs.md              ← Gate 3: README, deployment, referencia API
│   ├── standards.md                 ← Definition of Done, cobertura, ruff
│   ├── testing.md                   ← Tests pytest + pytest-cov
│   ├── backend-security.md          ← Seguridad FastAPI + JWT + BCrypt
│   ├── layered-architecture.md      ← Arquitectura por capas del producto
│   ├── api-design.md                ← Contratos de API
│   └── manifest.json                ← SHA-256 de cada skill (verificado por AtomLoader)
│
├── registry/                         ← Catálogo de agentes, protocolos y gates
│   ├── orchestrator.md              ← Master Orchestrator
│   ├── security_agent.md            ← SecurityAgent (Gate 2 + veto)
│   ├── audit_agent.md               ← AuditAgent (trazabilidad, FASE 8, precedentes)
│   ├── coherence_agent.md           ← CoherenceAgent (Gate 1, conflictos entre expertos)
│   ├── standards_agent.md           ← StandardsAgent (Gate 2b, cobertura, calidad)
│   ├── compliance_agent.md          ← ComplianceAgent (FASE 1 legal)
│   ├── evaluation_agent.md          ← EvaluationAgent (scoring 0-1)
│   ├── domain_orchestrator.md       ← Domain Orchestrators (coordinación por dominio)
│   ├── logistics_agent.md           ← LogisticsAgent (TokenBudgetReport pre-DAG)
│   ├── execution_auditor.md         ← ExecutionAuditor (observador out-of-band FASE 2→8)
│   ├── documentation_agent.md       ← DocumentationAgent (Gate 3 docs)
│   ├── research_orchestrator.md     ← ResearchOrchestrator (modo RESEARCH)
│   └── agent_taxonomy.md            ← Catálogo completo: ciclo de vida, modelos, permisos
│
├── engram/                           ← Sistema de memoria atomizada por agente
│   ├── INDEX.md                     ← Context-Map (qué átomo carga qué agente)
│   ├── VERSIONING.md                ← Protocolo de snapshot y rollback
│   ├── core/                        ← Decisiones de arquitectura (Master Orchestrator)
│   ├── security/                    ← Patrones de ataque/vulnerabilidades (SecurityAgent)
│   ├── quality/                     ← Patrones de código y testing (StandardsAgent)
│   ├── coherence/                   ← Patrones de conflictos entre expertos (CoherenceAgent)
│   ├── compliance/                  ← Patrones de riesgo legal/ético (ComplianceAgent)
│   ├── audit/                       ← Historial de gates y cobertura de RF (AuditAgent)
│   ├── domains/                     ← Knowledge específico por dominio de proyecto
│   └── precedents/                  ← Precedentes validados post-Gate 3 (AuditAgent exclusivo)
│
├── metrics/                          ← Métricas de sesión (AuditAgent, append-only)
│   ├── sessions.md                  ← Registro histórico de sesiones
│   ├── schema.md                    ← Esquema de métricas
│   ├── cost-schema.md               ← Esquema de costos por sesión
│   ├── execution_audit_schema.md    ← Schema ExecutionAuditReport
│   └── precedents_schema.md         ← Schema de precedentes
│
├── compliance/                       ← Informes y paquetes de entrega (ComplianceAgent)
│
├── docs/                             ← Documentación del framework
│   ├── CHANGELOG.md                 ← Changelog generado automáticamente
│   ├── ROADMAP_PRODUCCION.md        ← Roadmap de madurez hacia producción v1.0
│   ├── TUTORIAL_LEVEL2.md           ← Tutorial completo: objetivo Nivel 2 end-to-end
│   ├── sdk-api.md                   ← Referencia de la API del SDK piv-oac
│   ├── git-branch-protection.md     ← Reglas de protección de ramas recomendadas
│   ├── architecture/                ← Diagramas de arquitectura del framework
│   ├── flows/                       ← Flujos visuales por fase (FASE 0→8)
│   ├── justification/               ← Análisis competitivo y ADRs
│   └── redesign/                    ← Rationale v4.0 y decisiones de rediseño
│
├── scripts/                          ← Utilitarios de operación y validación
│   ├── validate_env.py              ← Validación del entorno antes de ejecutar
│   ├── validate_docs.py             ← Validación de documentación del framework
│   ├── validate-specs.py            ← Validación de specs/active/
│   ├── fase8_auto.py                ← Automatización de cierre FASE 8
│   ├── generate_changelog.py        ← Generación de CHANGELOG desde commits
│   ├── skill_manifest.py            ← Actualización de skills/manifest.json
│   ├── bootstrap.sh                 ← Bootstrap de entorno inicial
│   └── worktree-init.sh             ← Inicialización de worktrees de expertos
│
├── tools/                            ← Herramientas determinísticas del framework
│
├── sdk/                              ← SDK Python piv-oac (fuente local)
│
├── logs_veracidad/                   ← Logs de AuditAgent al cierre de objetivo
├── logs_scores/                      ← Audit trail de scoring y EvaluationAgent
└── worktrees/                        ← Temporal, no versionado (.gitignore)
```

---

## Flujo Completo de un Objetivo Nivel 2

```
1. Usuario entrega objetivo
         │
2. Master Orchestrator (Opus)
   └── Lee specs/active/ → valida RF
   └── Construye DAG de dependencias
   └── Presenta DAG al usuario → espera confirmación
         │
3. Crear entorno de control en PARALELO REAL (tras confirmación)
   ├── SecurityAgent (Opus)    — run_in_background=True ┐
   ├── AuditAgent (Sonnet)     — run_in_background=True ├── mismo mensaje → paralelo real
   └── CoherenceAgent (Sonnet) — run_in_background=True ┘
         │
4. Por cada tarea en orden del DAG:
   Domain Orchestrator → diseña plan → somete al gate
         │
5. Gate bloqueante (los 3 deben aprobar)
   RECHAZADO → revisar plan → repetir gate
   APROBADO  → crear worktrees y expertos
         │
6. Expertos trabajan en subramas aisladas
   CoherenceAgent monitoriza diffs continuamente
         │
7. Gate 1 (CoherenceAgent) → merge expertos → feature/<tarea>
   Gate 2 (Security + Audit) → merge feature/<tarea> → staging
         │
8. Gate 3 (humano + Security + Audit)
   Solo con confirmación humana → merge staging → main
         │
9. Cierre
   AuditAgent genera 3 logs en /logs_veracidad/
   AuditAgent + CoherenceAgent actualizan engram/
```

---

## Estado del framework

**PIV/OAC v4.0** — framework en producción. OBJ-003 cerrado el 2026-04-02 con Gate compliance rate 1.0 (18/18 gates, 0 rechazos).

| Dimensión | Estado |
|---|---|
| Gates canónicos | Gate 1, 2, 2b, 3 definidos en `contracts/gates.md` |
| Agentes catalogados | 13 agentes en `registry/` con modelos y permisos asignados |
| Skills disponibles | ~28 skills en `skills/` con verificación SHA-256 vía `manifest.json` |
| SDK Python | `piv-oac` disponible en `sdk/` e instalable vía `pip install piv-oac` |
| Trazabilidad | `logs_veracidad/` + `metrics/sessions.md` + `engram/precedents/` |
| Roadmap de madurez | `docs/ROADMAP_PRODUCCION.md` — documento vivo con scoring por dimensión |

---

## Separación Directive / Artifact

| | Rama directive (`agent-configs`) | Ramas artifact (`main`, `staging`, `feature/*`) |
|---|---|---|
| **Contiene** | CLAUDE.md, agent.md, skills/, registry/, engram/, contracts/, specs/_templates/ | src/, tests/, docs/, specs/active/, logs_veracidad/ |
| **Produce** | Nada ejecutable — solo directivas | Código, tests, documentación, trazabilidad |
| **Recibe merges de** | Nunca desde artifact | Desde la rama artifact inmediatamente inferior |
| **Versionado** | Independiente del ciclo de entrega | Sigue el flujo execution → integration → delivery |
| **Quién la modifica** | El operador humano del marco | Los agentes bajo protocolo PIV/OAC |

---

## Protección de Ramas

La configuración recomendada de branch protection rules está documentada en `docs/git-branch-protection.md`.

Resumen de la política:

| Rama | Protección |
|---|---|
| `agent-configs` | **Solo lectura** — Lock branch + PR obligatoria + sin bypass de admin |
| `main` | Solo el owner puede mergear — no force push |
| `staging` | Solo el owner puede pushear — no force push |
| `feature/*` | Solo el owner puede pushear — no force push |

**Flujo para modificar `agent-configs`** (cuando está protegida):
1. Crear `directive/update-<descripcion>` desde `agent-configs`
2. Aplicar cambios en esa rama
3. Abrir PR hacia `agent-configs` → revisar → merge
