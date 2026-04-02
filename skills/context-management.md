# Skill: Context Management — Protocolo del 60% y VETO_SATURACIÓN

> Cargado por: todos los orquestadores (Master, Domain) al detectar aproximación a umbrales de contexto.
> Propósito: protocolo operativo para los dos puntos de presión de contexto: escritura proactiva (60%) y veto por saturación (80%).

---

## 1. Los Dos Umbrales — Tabla de Referencia Rápida

| Umbral | Nombre | Acción | ¿Detiene el agente? |
|---|---|---|---|
| 60% | Session Continuity — Regla del 60% | Escribir checkpoint + summary → continuar | NO — el agente continúa tras escribir |
| 80% | VETO_SATURACIÓN | Escalar al padre → no continuar | SÍ — el agente detiene su ejecución |

El 60% es un punto de escritura proactiva **dentro de la misma sesión de trabajo**.
El 80% es el punto de no retorno: el agente no puede operar con calidad suficiente y debe escalar.

---

## 2. Protocolo del 60% — Significado Operativo de "Pausar"

"Pausar la tarea en curso" **no significa suspender la ejecución del agente**. Los agentes LLM no tienen un mecanismo de suspensión real: procesan instrucciones de forma continua.

**Significado correcto:** antes de iniciar la próxima acción sustantiva, completar la escritura del estado. La "pausa" es la ventana de escritura del checkpoint, no una suspensión.

### Pasos operativos (orden estricto)

```
TRIGGER DEL 60% DETECTADO:

1. Completar la acción ATÓMICA en curso sin interrumpirla
   (si estás leyendo un archivo, termina de leerlo; si estás escribiendo, termina el write)

2. Escribir/actualizar <objetivo-id>_summary.md con el estado ACTUAL
   → Sección "Pendiente Inmediato": la acción que acababas de completar + qué sigue exactamente
   → Ver formato completo en skills/session-continuity.md §2

3. Escribir/actualizar <objetivo-id>.json con estado de gates y fases
   → Ver schema en .piv/README.md

4. Registrar en "Notas de Recuperación" del summary:
   → qué archivo/tarea estaba procesando
   → qué queda pendiente para completar la acción en curso
   → decisiones relevantes tomadas en este bloque de trabajo

5. Emitir notificación al orquestador padre:
   CHECKPOINT_60_EMITIDO
   OBJETIVO: <objetivo-id>
   SUMMARY: .piv/active/<objetivo-id>_summary.md
   PENDIENTE_INMEDIATO: <descripción de la próxima acción>

6. Continuar con la próxima acción
   (el checkpoint fue escrito — el trabajo es recuperable ante cualquier compresión posterior)
```

### Qué NO implica este protocolo

- No esperar respuesta del usuario
- No esperar respuesta del padre (el paso 5 es notificación asíncrona, no bloqueo)
- No detener el flujo de ejecución más allá del tiempo de escritura del checkpoint
- No es un checkpoint de bloqueo — es un checkpoint de **continuidad garantizada**

### Garantía

Un agente que escribe el checkpoint al 60% garantiza que, aunque ocurra compresión de contexto inmediatamente después, el estado puede retomarse desde `skills/session-continuity.md §4` sin re-ejecutar fases previas.

---

## 3. Triggers Deterministas del 60%

Los orquestadores no pueden medir tokens directamente. Usar estos proxies. **Cualquiera** de los siguientes dispara la escritura del checkpoint:

| ID | Trigger | Condición concreta |
|---|---|---|
| **T-a** | Archivos leídos | ≥ 15 archivos distintos leídos desde el último checkpoint en la fase actual |
| **T-b** | Ciclos de gate | ≥ 3 ciclos completos (plan → revisión → aprobación/rechazo) desde el último checkpoint |
| **T-c** | Próxima carga grande | La próxima acción requiere cargar ≥ 3 archivos Y el total acumulado llegaría a ≥ 15 |
| **T-sub** | Estimación subjetiva | El orquestador estima subjetivamente que supera el 60% por otros indicios |

Los triggers T-a, T-b, T-c son el **mínimo garantizado** — cubren el caso en que la estimación subjetiva falla. T-sub complementa pero no reemplaza.

**Consecuencia de no disparar:** Un agente que llega al 80% sin haber escrito el checkpoint al 60% viola esta skill y viola la regla permanente de Continuidad de Sesión. El AuditAgent verifica este invariante en FASE 8.

---

## 4. Protocolo VETO_SATURACIÓN (80%)

### Caso base: agente satura, padre disponible

```
Agente detecta ≥ 80% de contexto Y no puede fragmentar más:

1. Emitir al padre inmediatamente:

   VETO_SATURACIÓN
   AGENTE: <nombre completo — ej: SecurityAgent/crypto>
   CONTEXTO_ESTIMADO: ≥80%
   PUEDE_FRAGMENTAR: NO
   TRABAJO_COMPLETADO: <descripción de lo que terminó>
   TRABAJO_PENDIENTE: <descripción precisa de lo que quedó sin hacer>
   ACCIÓN_REQUERIDA: [re-fragmentar | escalar | reducir scope]

2. Detener toda ejecución activa — NO procesar más material
   Un agente que emite VETO y luego sigue ejecutando viola Zero-Trust metodológico

3. El padre recibe el VETO y aplica una de estas acciones:
   a. Re-fragmentar: divide el trabajo pendiente en sub-agentes y los lanza
   b. Escalar al Master: si el padre tampoco puede re-fragmentar (ver caso cascada)
   c. Reducir scope: si el trabajo pendiente no es crítico para el objetivo actual
```

### Caso cascada: padre también saturado

Este caso no estaba cubierto por la regla permanente anterior. Protocolo explícito:

```
CONDICIÓN: Agente A emite VETO_SATURACIÓN → Padre B intenta resolver
           pero Padre B también está al ≥ 80% de contexto.

PROTOCOLO DEL PADRE B (≥ 80%) que recibe VETO_SATURACIÓN:

1. Padre B NO intenta resolver el VETO — no tiene capacidad con calidad suficiente

2. Si Padre B no escribió checkpoint al 60%: escribir checkpoint de emergencia ahora
   (incluir en Notas de Recuperación: VETO recibido de Agente A + estado pendiente de A)

3. Padre B emite VETO_SATURACIÓN_CASCADA al Master Orchestrator:

   VETO_SATURACIÓN_CASCADA
   AGENTE_ORIGEN: <nombre del Agente A — primer emisor>
   AGENTE_INTERMEDIO: <nombre del Padre B — emisor de este mensaje>
   CONTEXTO_AGENTE_ORIGEN: ≥80% — no puede continuar
   CONTEXTO_AGENTE_INTERMEDIO: ≥80% — no puede resolver
   TRABAJO_PENDIENTE_ORIGEN: <trabajo que Agente A no terminó>
   TRABAJO_PENDIENTE_INTERMEDIO: <trabajo que Padre B no terminó>
   ACCIÓN_REQUERIDA: Master Orchestrator debe intervenir — ver protocolo de respuesta

4. Detener toda ejecución en Padre B — esperar acción del Master
```

### Respuesta del Master Orchestrator ante VETO_SATURACIÓN_CASCADA

```
MASTER recibe VETO_SATURACIÓN_CASCADA:

CASO A — Master < 80% de contexto:
  1. Registrar el evento en checkpoint inmediatamente
  2. Presentar opciones al usuario con toda la información:

     "Saturación en cascada detectada en el sistema de agentes.
      Agente A [nombre]: no puede continuar — trabajo pendiente: [resumen]
      Agente B [nombre]: no puede resolver — trabajo pendiente: [resumen]
      Todo el trabajo realizado hasta ahora está en checkpoint.
      Opciones:
      [1] Nueva sesión — el framework retoma desde el checkpoint (0 trabajo perdido)
      [2] Reducir scope del trabajo pendiente y continuar con los agentes disponibles
      [3] Cancelar el objetivo — mover a .piv/failed/"

  3. Esperar respuesta humana antes de cualquier otra acción
  4. Ejecutar la opción elegida por el usuario

CASO B — Master también ≥ 80%:
  1. Escribir checkpoint de emergencia con toda la información disponible:
     → Estado de todos los agentes afectados
     → Trabajo completado vs. pendiente por agente
     → Nota "SATURACIÓN_TOTAL: true"
  2. Emitir al usuario:

     "ALERTA: Saturación total del sistema de orquestación.
      Checkpoint de emergencia escrito en .piv/active/<objetivo-id>.json
      Iniciar nueva sesión para retomar — el estado está preservado.
      Agentes afectados: [lista]"

  3. Detener TODA ejecución — no procesar ninguna instrucción más
```

### Invariante del protocolo de saturación

```
En ningún nivel de la jerarquía un agente continúa procesando
después de emitir VETO_SATURACIÓN o VETO_SATURACIÓN_CASCADA.

Violación = Zero-Trust metodológico (el agente ya no opera con calidad).
AuditAgent verifica este invariante en FASE 8 revisando logs.
```

---

## 5. Diagrama de Presión de Contexto

```
┌───────────────────────────────────────────────────────────────────┐
│                     PRESIÓN DE CONTEXTO                           │
│                                                                   │
│   0%     20%     40%     60%     80%    100%                      │
│   ├───────┼───────┼───────┼───────┼───────┤                      │
│                           ▲       ▲                               │
│                           │       │                               │
│                      CHECKPOINT  VETO                             │
│                      (continúa)  (detiene)                        │
│                                                                   │
│   < 60%   → ejecución normal                                      │
│   60-80%  → obligatorio escribir checkpoint; continuar            │
│   > 80%   → VETO_SATURACIÓN obligatorio; detener                 │
│                                                                   │
│   CASCADA → padre también > 80% → VETO_SATURACIÓN_CASCADA        │
│             hasta Master → opciones al usuario                    │
└───────────────────────────────────────────────────────────────────┘
```

---

## 6. Referencias Cruzadas

| Archivo | Relación |
|---|---|
| `skills/session-continuity.md` | Formato completo del summary + triggers del 60% (fuente primaria) |
| `agent.md §13` | Fragmentación recursiva + regla permanente VETO_SATURACIÓN |
| `CLAUDE.md` regla "Veto por Saturación" | Definición de la regla a nivel de framework |
| `CLAUDE.md` regla "Continuidad de Sesión" | Regla del 60% a nivel de framework |
| `registry/orchestrator.md` | Protocolo de checkpoint del Master Orchestrator |
| `.piv/README.md` | Schema del checkpoint JSON |

---

## InheritanceGuard v4.0 — Herencia Controlada

El lazy loading controla qué archivos carga un agente.
El InheritanceGuard controla qué contexto hereda de su agente padre.

### SAFE_INHERIT — Whitelist explícita

Solo estos 5 atributos pasan de padre a hijo:
- `objective_id` — ID del objetivo en curso
- `task_scope` — scope de la tarea asignada
- `execution_mode` — DEVELOPMENT / RESEARCH / MIXED
- `compliance_scope` — FULL / MINIMAL / NONE
- `parent_agent_id` — ID del agente que lo creó

**Todo lo demás NO se hereda.** Los permisos, credenciales y capacidades
del hijo son asignados por PermissionStore, nunca por el padre.

### Reglas de herencia

| Regla | Valor | Por qué |
|---|---|---|
| Profundidad máxima | 1 nivel (padre → hijo) | Previene cadenas de herencia ocultas |
| TTL del snapshot | 30 minutos | Un contexto muy antiguo puede ser incorrecto |
| Firma HMAC | Obligatoria | Detectar manipulación del snapshot |
| `InheritanceExpired` | Solicitar snapshot fresco | Error esperado en tareas largas |
| `InheritanceTampered` | SECURITY_VIOLATION inmediato | Error no esperado — posible ataque |

## Context Scope Protocol v4.0 — CSP (Protocolo Recomendado)

Extensión del lazy loading aplicada al INPUT de los agentes de gate.

**Problema:** En Gate 2b, tres agentes revisan el mismo diff en paralelo.
Sin CSP, cada uno recibe el diff completo aunque su checklist solo cubra ~30-40%.

**Solución:** El artefacto se almacena UNA VEZ en StateStore.
Cada agente recibe solo el scope filtrado correspondiente a su checklist.
Si un agente necesita más contexto → solicita por `artifact_ref`.

### Scope filters por agente (canónicos, definidos en contracts/gates.md)

| Agente | Keywords de su scope | % típico del diff |
|---|---|---|
| SecurityAgent | auth, crypto, bcrypt, jwt, token, secret, password, session, rbac, input_validation, cors | 25-35% |
| AuditAgent | business_logic, domain, service, repository, tests, rf_coverage | 35-45% |
| StandardsAgent | test_, _test, docstring, import, public_api, docs/ | 25-40% |

El razonamiento (chain of thought) es in-agent. Solo viaja el veredicto estructurado.

**Estado:** Protocolo RECOMENDADO en capa directiva. Se convierte en regla permanente
obligatoria cuando el SDK tenga soporte completo de StateStore y artifact_ref.
