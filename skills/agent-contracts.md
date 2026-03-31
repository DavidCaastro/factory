# Agent Interface Contracts — PIV/OAC v3.2

**Gap:** G-07 — Structured output schemas for inter-agent communication
**Status:** Active
**Applies to:** All agents operating within a PIV/OAC pipeline

---

## Motivation

Agents communicating through free-form text make parsing fragile and error-prone. During `piv-challenge`, `SecurityAgent` responded with `VEREDICTO: RECHAZADO` instead of `VERDICT: REJECTED`, causing downstream parsers to silently fail and propagate an unvalidated task.

This document defines the mandatory structured output contract for each agent type. Contracts enforce canonical English field names and a deterministic line format that any consumer can parse with a simple regex.

---

## 1. Contrato de Salida por Tipo de Agente

### 1.1 MasterOrchestrator

**Emits on normal dispatch:**

```
CLASSIFICATION: NIVEL_1 | NIVEL_2
BUDGET_ESTIMATE_TOKENS_TOTAL_EST: <integer>
BUDGET_ESTIMATE_USD_EST: <float>
BUDGET_ESTIMATE_MODEL_DISTRIBUTION: <json object, e.g. {"gpt-4o": 0.6, "claude-3-5-sonnet": 0.4}>
spec_validated: true | false
```

Followed by a YAML code block containing the execution DAG:

````
```yaml
dag:
  nodes:
    - id: <node_id>
      agent: <agent_type>
      depends_on: [<node_id>, ...]
      input: <description>
  edges:
    - from: <node_id>
      to: <node_id>
```
````

**Emits on malicious intent detection:**

```
VETO_INTENCION: <plain-text reason describing the detected malicious use>
```

When `VETO_INTENCION` is present, no DAG is emitted and execution halts.

---

### 1.2 SecurityAgent

**Emits on every review:**

```
VERDICT: APPROVED | REJECTED | CONDITIONAL_APPROVED
RISK_LEVEL: LOW | MEDIUM | HIGH | CRITICAL
FINDINGS: <comma-separated list of findings, or NONE if APPROVED>
```

**Emits additionally on veto:**

```
SECURITY_VETO: <plain-text reason>
```

When `SECURITY_VETO` is present, the pipeline must halt regardless of `VERDICT`.
`FINDINGS` must be `NONE` only when `VERDICT` is `APPROVED`.

---

### 1.3 AuditAgent

**Emits on every audit:**

```
AUDIT_RESULT: PASS | FAIL
RF_COVERAGE: <X>/<Y> RFs trazados
SCOPE_VIOLATIONS: <comma-separated list of violations, or NONE if PASS>
ENGRAM_WRITE: <atom_path> | NONE
```

`ENGRAM_WRITE` contains the path of the engram atom written during this audit, or `NONE` if no atom was persisted.

---

### 1.4 CoherenceAgent

**Emits on every coherence check:**

```
COHERENCE_STATUS: CONSISTENT | CONFLICT_DETECTED | SCOPE_OVERLAP
GATE1_VERDICT: APPROVED | REJECTED
CONFLICTS: <see format below, or NONE if CONSISTENT>
```

Each conflict in `CONFLICTS` occupies one line in this format:

```
CONFLICT: expert_a=<name> expert_b=<name> conflict_type=<type> resolution=<resolution>
```

Multiple conflicts each appear on their own `CONFLICT:` line immediately after the `CONFLICTS:` field.

---

### 1.5 DomainOrchestrator

**Emits on plan generation:**

```
DO_TYPE: <type of this Domain Orchestrator, e.g. BackendDO, FrontendDO>
PLAN: <plain-text description of the overall plan>
DEPENDENCIES: <comma-separated list of inter-task dependency edges, e.g. task_2->task_3, or NONE>
```

Followed by a `WORKTREES` block — one entry per line:

```
WORKTREE: task=<task_description> expert=<expert_type> base_branch=<branch_name>
```

---

### 1.6 SpecialistAgent

**Emits on implementation completion:**

```
IMPLEMENTATION: <plain-text description of what was implemented>
FILES_CHANGED: <comma-separated list of file paths>
TESTS_ADDED: <integer>
RF_ADDRESSED: <comma-separated list of RF identifiers, or NONE>
```

---

## 2. Idioma Canónico

**Regla:** Todos los campos de contrato (nombres y valores de enumeración) están en inglés. El razonamiento, las explicaciones y el texto libre pueden estar en español.

| Correcto | Incorrecto |
|---|---|
| `VERDICT: REJECTED` | `VEREDICTO: RECHAZADO` |
| `AUDIT_RESULT: FAIL` | `RESULTADO_AUDITORIA: FALLO` |
| `RISK_LEVEL: HIGH` | `NIVEL_RIESGO: ALTO` |
| `COHERENCE_STATUS: CONSISTENT` | `ESTADO_COHERENCIA: CONSISTENTE` |

Esta regla elimina la clase de fallos observada en `piv-challenge` y garantiza que todos los parsers puedan usar un único conjunto de patrones sin localización.

---

## 3. Protocolo de Parsing

### 3.1 Formato de línea

Cada campo de contrato aparece en su propia línea con el formato exacto:

```
FIELD_NAME: value
```

Los campos no pueden aparecer dentro de párrafos de texto libre. El texto libre (razonamiento, explicación) debe preceder o seguir al bloque de contrato, nunca entremezclarse con las líneas de campo.

### 3.2 Extracción con regex

Los consumidores extraen cada campo usando el patrón:

```
^FIELD_NAME:\s+(.+)$
```

Por ejemplo, para `VERDICT`:

```
^VERDICT:\s+(APPROVED|REJECTED|CONDITIONAL_APPROVED)$
```

### 3.3 Manejo de respuestas malformadas

Si un campo requerido no aparece en la respuesta del agente productor:

1. El agente consumidor marca la respuesta como `MALFORMED`.
2. Solicita un retry al agente productor incluyendo el campo faltante en el mensaje de error.
3. Máximo **2 retries** por campo faltante.
4. Si tras 2 retries el campo sigue ausente, el consumidor escala al orquestador padre con estado `UNRECOVERABLE_MALFORMED`.

### 3.4 Campos requeridos por tipo de agente

| Agente | Campos requeridos |
|---|---|
| MasterOrchestrator | `CLASSIFICATION`, `BUDGET_ESTIMATE_TOKENS_TOTAL_EST`, `BUDGET_ESTIMATE_USD_EST`, `BUDGET_ESTIMATE_MODEL_DISTRIBUTION`, `spec_validated` + bloque YAML DAG |
| SecurityAgent | `VERDICT`, `RISK_LEVEL`, `FINDINGS` |
| AuditAgent | `AUDIT_RESULT`, `RF_COVERAGE`, `SCOPE_VIOLATIONS`, `ENGRAM_WRITE` |
| CoherenceAgent | `COHERENCE_STATUS`, `GATE1_VERDICT`, `CONFLICTS` |
| DomainOrchestrator | `DO_TYPE`, `PLAN`, `DEPENDENCIES` + al menos un `WORKTREE` |
| SpecialistAgent | `IMPLEMENTATION`, `FILES_CHANGED`, `TESTS_ADDED`, `RF_ADDRESSED` |

---

## 4. Compatibilidad con G-06

Los contratos de `MasterOrchestrator` incluyen obligatoriamente el campo:

```
spec_validated: true | false
```

Este campo indica si los schemas ubicados en `specs/schemas/` fueron verificados antes de construir el DAG. Un valor `false` no bloquea la ejecución, pero debe ser registrado en el audit trail por `AuditAgent` como una advertencia de cobertura incompleta.

Referencia: ver `specs/schemas/` para los schemas actuales validados por G-06.

---

## 5. Ejemplos Completos de Respuesta Conforme al Contrato

### 5.1 MasterOrchestrator — Despacho normal

```
Analicé la intención del usuario y determiné que corresponde a una tarea de backend de complejidad media.
El presupuesto estimado considera 3 agentes especializados y 1 ronda de auditoría.

CLASSIFICATION: NIVEL_2
BUDGET_ESTIMATE_TOKENS_TOTAL_EST: 48000
BUDGET_ESTIMATE_USD_EST: 0.29
BUDGET_ESTIMATE_MODEL_DISTRIBUTION: {"claude-sonnet-4-6": 0.7, "claude-haiku-3-5": 0.3}
spec_validated: true

```yaml
dag:
  nodes:
    - id: security_review
      agent: SecurityAgent
      depends_on: []
      input: Revisar los endpoints propuestos para inyección SQL y autenticación
    - id: backend_impl
      agent: SpecialistAgent
      depends_on: [security_review]
      input: Implementar endpoints REST con validación
    - id: audit
      agent: AuditAgent
      depends_on: [backend_impl]
      input: Verificar cobertura de RFs y escribir engram
  edges:
    - from: security_review
      to: backend_impl
    - from: backend_impl
      to: audit
```
```

---

### 5.2 MasterOrchestrator — Veto por intención maliciosa

```
La solicitud describe explícitamente la generación de exploits para sistemas de terceros sin autorización.

VETO_INTENCION: La tarea solicita construir herramientas de ataque para infraestructura no autorizada, lo cual viola la política de uso aceptable del framework PIV/OAC.
```

---

### 5.3 SecurityAgent — Aprobado

```
Revisé los endpoints propuestos. No encontré vectores de ataque evidentes en la descripción funcional.

VERDICT: APPROVED
RISK_LEVEL: LOW
FINDINGS: NONE
```

---

### 5.4 SecurityAgent — Rechazado con veto

```
El endpoint /admin/exec permite ejecución de comandos de sistema sin autenticación. Esto representa un riesgo crítico de RCE.

VERDICT: REJECTED
RISK_LEVEL: CRITICAL
FINDINGS: RCE via /admin/exec — no authentication check, user input passed directly to shell
SECURITY_VETO: Endpoint exposes unauthenticated remote code execution; pipeline halted pending architectural redesign
```

---

### 5.5 AuditAgent — Pass

```
Verifiqué la cobertura de todos los RFs del sprint y no encontré violaciones de scope.

AUDIT_RESULT: PASS
RF_COVERAGE: 5/5 RFs trazados
SCOPE_VIOLATIONS: NONE
ENGRAM_WRITE: engram/atoms/sprint_12_backend_audit.md
```

---

### 5.6 AuditAgent — Fail

```
El especialista modificó archivos fuera del módulo asignado y no trazó RF-03.

AUDIT_RESULT: FAIL
RF_COVERAGE: 4/5 RFs trazados
SCOPE_VIOLATIONS: auth/middleware.ts modificado fuera del scope de BackendDO, RF-03 sin implementación trazable
ENGRAM_WRITE: NONE
```

---

### 5.7 CoherenceAgent — Sin conflictos

```
Revisé los planes de los tres Domain Orchestrators y no encontré solapamientos de scope ni contradicciones.

COHERENCE_STATUS: CONSISTENT
GATE1_VERDICT: APPROVED
CONFLICTS: NONE
```

---

### 5.8 CoherenceAgent — Con conflictos resueltos

```
FrontendDO y BackendDO definieron esquemas de respuesta incompatibles para el endpoint /user/profile.

COHERENCE_STATUS: CONFLICT_DETECTED
GATE1_VERDICT: REJECTED
CONFLICTS: definidos a continuación
CONFLICT: expert_a=FrontendDO expert_b=BackendDO conflict_type=schema_mismatch resolution=BackendDO adopta el schema de FrontendDO; campo snake_case unificado
```

---

### 5.9 DomainOrchestrator

```
Desglosaré la implementación del módulo de pagos en tres tareas paralelas asignadas a especialistas distintos.

DO_TYPE: BackendDO
PLAN: Implementar el módulo de pagos con tres capas: gateway adapter, business logic, y persistence. Las tareas de adapter y persistence pueden correr en paralelo; business logic depende de ambas.
DEPENDENCIES: task_adapter->task_business, task_persistence->task_business
WORKTREE: task=Implementar PaymentGatewayAdapter expert=SpecialistAgent base_branch=feature/payments
WORKTREE: task=Implementar PaymentRepository con PostgreSQL expert=SpecialistAgent base_branch=feature/payments
WORKTREE: task=Implementar PaymentService con reglas de negocio expert=SpecialistAgent base_branch=feature/payments
```

---

### 5.10 SpecialistAgent

```
Implementé el PaymentGatewayAdapter con soporte para Stripe y un stub para pruebas. Añadí tests unitarios para los casos de éxito, fallo de red y rechazo de tarjeta.

IMPLEMENTATION: PaymentGatewayAdapter implementado con interfaz genérica IPaymentGateway; StripeAdapter como implementación concreta; MockAdapter para tests
FILES_CHANGED: src/payments/gateway/IPaymentGateway.ts, src/payments/gateway/StripeAdapter.ts, src/payments/gateway/MockAdapter.ts, tests/unit/payments/StripeAdapter.test.ts
TESTS_ADDED: 7
RF_ADDRESSED: RF-08, RF-09
```
