# Framework Quality Gate — PIV/OAC
> Cargado por: StandardsAgent en Gate 2 cuando `MODO_META_ACTIVO` está declarado.
> Define los checks deterministas equivalentes a los gates de producto, aplicados a archivos de protocolo y documentación del framework.
> Principio: **herramientas antes de LLM**. Todo check debe ser verificable con grep/glob — no estimación subjetiva.

---

## Equivalencias con Gates de Producto

| Gate de producto | Equivalente de framework | Herramienta |
|---|---|---|
| `pytest-cov ≥ 90%` | Integridad de cross-references: todos los archivos referenciados existen | `glob` + `grep` |
| `ruff: 0 errores` | Completitud estructural: archivos de registry tienen todas las secciones requeridas | `grep` (headers `## N.`) |
| `pip-audit: 0 vulnerabilidades` | Integridad de protocolo: todos los estados, modos y agentes citados en reglas tienen entrada canónica en su registry | `grep` |
| `Definition of Done` | Framework DoD (ver §5) | combinación de los anteriores |

> Si una herramienta no puede ejecutarse → `BLOQUEADO_POR_HERRAMIENTA`. No emitir veredicto estimado.

---

## Check 1 — Integridad de Cross-References (equivalente a cobertura de tests)

**Objetivo:** Verificar que toda referencia a un archivo del framework apunta a un archivo que existe.

**Procedimiento:**
1. Extraer todas las referencias de la forma `` `ruta/archivo.md` `` en los archivos modificados en el objetivo actual
2. Para cada referencia, verificar existencia con `glob` o lectura directa
3. Una referencia rota = fallo equivalente a test sin cobertura

**Resultado esperado:** 0 referencias rotas.

**Ejemplos de referencias a verificar:**
- En registry files: sección "Referencias Cruzadas" — todas las rutas deben existir
- En CLAUDE.md: todos los archivos en la sección "Estructura del Repositorio"
- En agent.md: todas las referencias a `skills/`, `registry/`, `engram/` en el protocolo

**Formato de reporte:**
```
CROSS-REF CHECK:
  [OK]  registry/coherence_agent.md → existe
  [FAIL] registry/nonexistent.md → NO EXISTE
  Total: X/Y referencias válidas
```

---

## Check 2 — Completitud Estructural de Registry Files (equivalente a linting)

**Objetivo:** Verificar que los archivos de registry del framework tienen todas las secciones requeridas según su tipo.

**Tipo: Agent Registry** (aplica a todos los archivos en `registry/*.md` excepto `orchestrator.md` y `agent_taxonomy.md`)

Secciones requeridas (verificar presencia de header `## N.`):
```
## 1. Identidad
## 2. Responsabilidades
## 3. [sección específica del agente]
## 4. [...]
...
## N-1. Restricciones
## N. Referencias Cruzadas
```
Mínimo requerido: la primera sección `## 1.` y las dos últimas (`Restricciones` y `Referencias Cruzadas`).

**Tipo: Skill** (aplica a `skills/*.md`)

Secciones requeridas:
- Al menos un header de nivel 2 (`## `)
- No debe contener `[PENDIENTE]` en campos obligatorios

**Formato de reporte:**
```
STRUCTURAL CHECK — registry/research_orchestrator.md:
  [OK]  ## 1. Identidad — presente
  [OK]  ## 9. Restricciones — presente
  [OK]  ## 10. Referencias Cruzadas — presente
  Resultado: COMPLETO
```

---

## Check 3 — Integridad de Protocolo (equivalente a pip-audit)

**Objetivo:** Verificar que todos los estados, modos y agentes citados en las reglas del framework tienen entrada canónica en su archivo de registry.

**Procedimiento:**
1. Identificar todos los valores de `execution_mode` mencionados en `CLAUDE.md` y `agent.md`
   → Verificar que cada valor aparece en la lista de valores válidos de `specs/active/INDEX.md`
2. Identificar todos los estados del Master Orchestrator mencionados en `CLAUDE.md`
   → Verificar que cada estado aparece en la tabla de estados de `registry/orchestrator.md`
3. Identificar todos los agentes mencionados en la tabla "Asignación de Modelo" de `CLAUDE.md`
   → Verificar que cada agente tiene un archivo de registry en `registry/` o está declarado en `registry/agent_taxonomy.md`

**Resultado esperado:** 0 referencias de protocolo sin entrada canónica.

**Tabla de canonicidad — entidades y archivos canónicos:**

| Tipo de entidad | Archivo canónico | Comando de verificación |
|---|---|---|
| `execution_mode` (valores válidos) | `specs/active/INDEX.md` | `grep "execution_mode" specs/active/INDEX.md` |
| Estados del Master Orchestrator | `registry/orchestrator.md` (tabla estados) | `grep -n "BLOQUEADA\|EN_EJECUCIÓN\|GATE_PENDIENTE\|COMPLETADA\|MODO_META" registry/orchestrator.md` |
| Agentes nombrados en tabla Asignación | `registry/agent_taxonomy.md` o archivo propio en `registry/` | `grep "agente\|Agent" registry/agent_taxonomy.md` |
| Reglas Permanentes (nombres de reglas) | `CLAUDE.md` tabla Reglas Permanentes | `grep "^\| \*\*" CLAUDE.md` |
| Gates (Gate 1 / Gate 2 / Gate 3) | `CLAUDE.md` FASE 6, 7 + `registry/orchestrator.md` | `grep -n "Gate [123]" CLAUDE.md registry/orchestrator.md` |
| Skills referenciados en protocolo | `skills/<nombre>.md` existe | `ls skills/` |
| Campos de `specs/active/INDEX.md` | `specs/active/INDEX.md` (plantilla definida en `agent.md` §6) | `grep "execution_mode\|compliance_scope\|version" specs/active/INDEX.md` |

**Formato de reporte:**
```
PROTOCOL INTEGRITY CHECK:
  execution_modes: DEVELOPMENT ✓ | RESEARCH ✓ | MIXED ✓ | INIT ✓ | MODO_META_ACTIVO — no es execution_mode, es estado ✓
  estados: GATE3_RECORDATORIO_PENDIENTE ✓ | MODO_META_ACTIVO ✓ | BLOQUEADA_POR_DISEÑO ✓
  agentes: MasterOrchestrator ✓ | SecurityAgent → registry/security_agent.md ✓ | AuditAgent → registry/audit_agent.md ✓ | EvaluationAgent → registry/evaluation_agent.md ✓ | ...
  Total: X/Y referencias con entrada canónica
```

---

## Check 4 — Ausencia de Placeholders Obligatorios (parte del DoD)

**Objetivo:** Verificar que los archivos del framework no contienen `[PENDIENTE]` en campos que deben estar poblados para que el framework sea funcional.

**Campos que PUEDEN estar `[PENDIENTE]`** (son templates intencionalmente incompletos):
- Cualquier campo dentro de `specs/` — es el contrato de proyecto, se llena por proyecto
- Campos de ejemplo en instrucciones de formato

**Campos que NO PUEDEN estar `[PENDIENTE]`**:
- Cualquier campo en `registry/*.md`
- Cualquier regla en la tabla de Reglas Permanentes de `CLAUDE.md`
- Cualquier sección en `skills/*.md`
- Cualquier paso en el protocolo de `agent.md`

**Procedimiento:** `grep -rn "\[PENDIENTE\]"` en los archivos modificados del objetivo (excluyendo `specs/`).

**Resultado esperado:** 0 ocurrencias en archivos de framework.

---

## 5. Framework Definition of Done

Un objetivo de framework se considera **COMPLETADO** solo cuando:

1. **Check 1 — Cross-references:** 0 referencias rotas en archivos modificados
2. **Check 2 — Completitud estructural:** registry files tienen mínimo `## 1.`, `Restricciones` y `Referencias Cruzadas`
3. **Check 3 — Integridad de protocolo:** 0 estados, modos o agentes sin entrada canónica
4. **Check 4 — Sin placeholders en framework:** 0 `[PENDIENTE]` en archivos de registry, skills o protocolo
5. **Gate pre-código aprobado** por Security + Audit + Coherence
6. **Gate 2 aprobado** por Security + Audit + Standards (con este checklist, no con pytest-cov)
7. **Merge a staging** ejecutado por Domain/Research Orchestrator tras Gate 2

---

## 6. Protocolo de Reporte del StandardsAgent en Modo Meta

Al ejecutar Gate 2 en `MODO_META_ACTIVO`, StandardsAgent reporta:

```
FRAMEWORK QUALITY GATE — [nombre del objetivo]
Modo: MODO_META_ACTIVO

Check 1 — Cross-Reference Integrity:   X/Y refs válidas — [PASS/FAIL]
Check 2 — Structural Completeness:     X/Y archivos completos — [PASS/FAIL]
Check 3 — Protocol Integrity:          X/Y entradas canónicas — [PASS/FAIL]
Check 4 — No Pending Placeholders:     X ocurrencias — [PASS/FAIL]

Veredicto: APROBADO | RECHAZADO
Acción correctiva: [si RECHAZADO: archivo:línea + fix requerido]
```
