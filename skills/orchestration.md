# SKILL: Orchestration — Construcción de Grafo de Dependencias y Composición de Equipo
> Skill de carga perezosa. Cargar SOLO por el Master Orchestrator al inicio de una tarea Nivel 2.

## Carga de Precedentes (antes de construir el DAG)

En FASE 1, antes de construir el grafo de dependencias:
1. Leer engram/precedents/INDEX.md
2. Identificar precedentes con task_type relevante al objetivo actual
3. Si existe precedente VALIDADO con outcome APROBADO y score ≥ 0.85:
   → Cargar como estrategia de partida para el Domain Orchestrator relevante
   → El DO puede desviarse del precedente pero debe justificarlo en el plan
4. Si no existe precedente relevante → construir DAG desde cero (comportamiento actual)
5. Si existe precedente con outcome RECHAZADO → incluir como anti-patrón en el briefing del DO

## Contexto de Aplicación
- **Agente:** Master Orchestrator
- **Cuándo:** Al recibir un objetivo para descomponerlo antes de crear ningún agente
- **Output esperado:** DAG de tareas + composición del equipo + confirmación del usuario

---

## Patrón 1: Descomposición del Objetivo en Tareas

El objetivo se descompone siguiendo dimensiones de análisis universales. Los nombres de tarea son adaptables al stack del proyecto (indicado en `specs/active/INDEX.md`).

```
DIMENSIONES UNIVERSALES — presencia en el objetivo → tarea en el grafo:

1. DIMENSIÓN DE PERSISTENCIA
   ¿El objetivo accede, diseña o modifica esquemas de datos o almacenamiento?
   → TAREA: <capa-datos> (ej: data-layer, db-schema, storage-module)

2. DIMENSIÓN DE LÓGICA DE NEGOCIO
   ¿El objetivo requiere lógica de dominio, validaciones, cálculos, servicios?
   → TAREA: <capa-dominio> (ej: domain-layer, business-logic, core-service)

3. DIMENSIÓN DE INTERFAZ
   ¿El objetivo expone una interfaz: endpoints, UI, CLI, contratos, eventos?
   → TAREA: <capa-interfaz> (ej: transport-layer, api-layer, ui-layer, cli)

4. DIMENSIÓN DE VERIFICACIÓN
   ¿El objetivo requiere tests unitarios, de integración, de contrato o e2e?
   → TAREA: tests

5. DIMENSIÓN DE DOCUMENTACIÓN
   ¿Hay decisiones técnicas que deben persistirse en el engram?
   → TAREA: docs (siempre temporal y paralela)
```

**Dimensiones opcionales según el objetivo:**
```
6. DIMENSIÓN DE INFRAESTRUCTURA
   ¿El objetivo requiere configuración de entorno, CI/CD, contenedores, IaC?
   → TAREA: infra

7. DIMENSIÓN DE INTEGRACIÓN
   ¿El objetivo conecta con servicios externos, webhooks, colas de mensajes?
   → TAREA: integration-layer
```

El Master Orchestrator determina qué dimensiones aplican leyendo el objetivo y el stack de `specs/active/INDEX.md`. Si no hay suficiente información en la spec para determinar las dimensiones → solicitar al usuario antes de construir el grafo.

Cada dimensión presente genera exactamente una tarea en el grafo.

---

## Patrón 2: Determinación de Dependencias (Secuencial vs Paralela)

```python
# Reglas de dependencia universales (adaptar nombres de tarea al stack del proyecto):

DEPENDENCIAS = {
    "<capa-datos>":      [],                      # Sin deps → PARALELA
    "<capa-dominio>":    [],                      # Sin deps → PARALELA
    "<capa-interfaz>":   ["<capa-dominio>"],      # Necesita contratos del dominio → SECUENCIAL
    "tests":             ["<capa-interfaz>"],     # Necesita código implementado → SECUENCIAL
    "docs":              ["<capa-datos>",
                          "<capa-dominio>"],      # Puede documentar desde diseño → PARALELA con tests
    "infra":             [],                      # Generalmente independiente → PARALELA
    "integration-layer": ["<capa-dominio>"],      # Necesita contratos de servicio → SECUENCIAL
}

# Una tarea es PARALELA si su lista de deps está vacía o todas sus deps ya completaron.
# Una tarea es SECUENCIAL si tiene deps que aún no han completado.
```

**Regla de paralelismo:** Dos tareas pueden ejecutarse en paralelo si ninguna depende del output de la otra, independientemente de su posición en el grafo.

**Protocolo si el grafo no se puede construir:**
```
Si el Master Orchestrator detecta ambigüedad irresolvible en las dependencias:
1. Listar las dependencias específicas que son ambiguas
2. Presentar al usuario las alternativas con sus trade-offs
3. Esperar decisión del usuario antes de continuar
4. No crear ningún agente ni worktree mientras el grafo tenga ambigüedades
```

---

## Patrón 3: Determinación de Número de Expertos por Tarea

```
Para cada factor, responder SÍ o NO. ≥ 2 factores SÍ → 2 expertos. 0-1 factores SÍ → 1 experto.

FACTOR 1 — Alta complejidad de diseño
  Pregunta binaria: ¿Existen ≥ 2 enfoques arquitectónicos concretos, mutuamente excluyentes
  y ambos razonables para este stack, que justifiquen exploración paralela?
  (Un solo enfoque evidente, aunque sea complejo de implementar, = NO)
  SÍ → explorar en paralelo aporta valor de diseño
  NO → un experto con más contexto es suficiente

FACTOR 2 — Riesgo arquitectónico
  Pregunta binaria: ¿Un error en esta tarea requeriría modificar ≥ 3 archivos FUERA de su
  dominio (en otras capas) para corregirse?
  (Impacto contenido dentro del mismo dominio = NO)
  SÍ → perspectiva adicional reduce riesgo en cascada
  NO → el gate de security/audit cubre el riesgo suficientemente

FACTOR 3 — Volumen que justifica paralelismo
  Pregunta binaria: ¿La tarea contiene ≥ 2 subtareas independientes entre sí, sin interfaz
  compartida, que pueden asignarse a expertos distintos sin riesgo de conflicto de merge?
  (Subtareas con interfaz compartida o que se llaman entre sí = NO)
  SÍ → distribución entre expertos sin fricción de coordinación
  NO → un experto secuencial es más eficiente

Regla de decisión (estricta):
  ≥ 2 factores SÍ → 2 expertos
  0 o 1 factor SÍ → 1 experto (incluso si la tarea parece grande o compleja)

El Master Orchestrator declara los factores evaluados en la columna "Justificación expertos" del DAG.
```

---

## Patrón 4: Formato del Grafo de Dependencias (DAG)

```markdown
## Grafo de Dependencias — [nombre del objetivo]

| ID | Tarea | Tipo | Expertos | Depende de | Justificación expertos |
|---|---|---|---|---|---|
| T-01 | data-layer | PARALELA | 1 | — | Esquema simple y claro |
| T-02 | domain-layer | PARALELA | 2 | — | Lógica auth compleja, vale explorar 2 enfoques |
| T-03 | transport-layer | SECUENCIAL | 1 | T-02 | Straightforward una vez definido el dominio |
| T-04 | tests | SECUENCIAL | 2 | T-03 | Unit tests + integration tests en paralelo |
| T-05 | docs | PARALELA | 1 | T-01, T-02 | Temporal, documenta decisiones de diseño |

### Orden de ejecución:
FASE 1 (paralelas): T-01, T-02, T-05
FASE 2 (desbloquea al completar T-02): T-03
FASE 3 (desbloquea al completar T-03): T-04
```

---

## Patrón 5: Composición del Entorno de Control

```markdown
## Entorno de Control — [nombre del objetivo]

### Mínimos obligatorios
- SecurityAgent     (Opus)   — gate de seguridad, veto
- AuditAgent        (Sonnet) — trazabilidad, logs, engram
- CoherenceAgent    (Sonnet) — consistencia entre expertos paralelos

### Criterios para superagentes adicionales
Si el objetivo involucra...          Añadir...
────────────────────────────────────────────────────────
Alto volumen de datos / queries      PerformanceAgent (Sonnet)
Múltiples servicios externos         IntegrationAgent (Sonnet)
Requisitos regulatorios (GDPR, etc.) ComplianceAgent (Opus)
Infraestructura / deploy             InfraAgent (Sonnet)
```

---

## Patrón 6: Presentación al Usuario para Confirmación

```
## Propuesta de equipo para: [objetivo]

### Grafo de tareas
[tabla DAG]

### Fases de ejecución
FASE 1 (paralelas): [lista]
FASE 2: [lista] — inicia al completar [deps]
...

### Entorno de control
[lista de superagentes con roles]

### Domain Orchestrators a crear
[lista por dominio]

### Specialist Agents planificados
[lista por tarea, incluyendo número de expertos y subramas]

---
¿Confirmas este plan o quieres ajustar algún elemento?
```

El Master Orchestrator NO crea ningún agente ni worktree hasta recibir confirmación.

---

## Patrón 7: Gestión del Estado del Grafo durante Ejecución

```
Estado por tarea:
  BLOQUEADA      → tiene dependencias sin completar
  LISTA          → dependencias completadas, esperando activación
  EN_EJECUCIÓN   → Domain Orchestrator y expertos activos
  GATE_PENDIENTE → esperando aprobación del entorno de control
  COMPLETADA     → código en rama de tarea, gate aprobado

Transiciones:
  BLOQUEADA → LISTA        cuando todas sus deps pasan a COMPLETADA
  LISTA → EN_EJECUCIÓN     cuando Master activa el Domain Orchestrator
  EN_EJECUCIÓN → GATE_PENDIENTE  cuando expertos reportan completado
  GATE_PENDIENTE → COMPLETADA    cuando Security + Audit aprueban
  GATE_PENDIENTE → EN_EJECUCIÓN  cuando gate rechaza (revisión y retry)
```
