# Átomo: core/operational_patterns
> ACCESO: Master Orchestrator, Domain Orchestrators
> CROSS-IMPACT: audit/gate_decisions
> Patrones operativos del framework PIV/OAC — cómo trabajan los agentes, no qué producen.

---

## 2026-03-12 — Protocolo de "mismo plan"

**Definición operativa:** Un plan revisado que NO corrige el componente específico que originó el rechazo se considera el mismo plan. El contador de rechazos NO se reinicia. El contador SÍ se reinicia si el componente rechazado fue corregido (aunque se hayan introducido otros cambios).

**Dónde aplica:** SecurityAgent al evaluar si es el 2do rechazo consecutivo del mismo plan → escalar al Master.

---

## 2026-03-12 — Flujo de worktrees y gates (clarificación de timing)

**Regla explícita:** Los worktrees y expertos NO existen antes de la aprobación explícita del gate de los tres agentes de control. FASE 4 es bloqueante. No se puede avanzar a creación de expertos con un gate pendiente.

---

## 2026-03-13 — Agentes en background compartiendo working tree

**Problema observado:** Cuando ≥3 agentes trabajan en paralelo en el MISMO directorio sin `isolation: "worktree"`, los cambios de un agente interfieren con los de otro.

**Solución:** Usar `git stash` antes de cambiar de rama y `git stash pop` al regresar, O usar `isolation: "worktree"` que crea una copia aislada del repositorio para cada agente.

**Recomendación:** Preferir `isolation: "worktree"` para evitar conflictos de estado del working tree.

---

## 2026-03-13 — Historial de versiones del DAG en specs/ ⚠️ nomenclatura actualizada

**Patrón:** Mantener secciones `v1.0/v2.0/...` separadas en el DAG de `specs/active/architecture.md`.
El historial de evolución del producto debe ser trazable desde la spec. No sobreescribir versiones anteriores del DAG.
**Nota:** El monolito `project_spec.md` está DEPRECADO. La referencia canónica ahora es `specs/active/INDEX.md` + módulos atomizados en `specs/active/`.
Ver LAYERS.md para la estructura completa del directorio `specs/`.

---

## 2026-03-17 — Timing del entorno de control: FASE 2 al inicio, no al final

**Problema observado (OBJ-001):** Los agentes de control (SecurityAgent, AuditAgent, StandardsAgent, CoherenceAgent) se lanzaron solo al final para Gate 2 integral, omitiendo los gates intermedios por tarea.

**Regla explícita:**
- FASE 2 se ejecuta al inicio, antes de crear ningún worktree ni experto
- Cada tarea en FASE 4 pasa por gate bloqueante de plan (Security + Audit + Coherence) antes de crear su worktree
- CoherenceAgent monitoriza diffs continuamente durante FASE 5 (un agente `monitor_diff` por par de expertos activos)
- Gate 1 (Coherence) se ejecuta por cada subrama antes de merge a `feature/<tarea>`
- Gate 2 (Security + Audit + Standards) se ejecuta por cada merge `feature/<tarea> → staging`

**Al reanudar tras compresión:** FASE 0 debe reconstituir el entorno de control (relanzar agentes `EN_EJECUCION` según `control_environment` en el JSON de sesión) antes de continuar cualquier ejecución.

---

## 2026-03-17 — Estimación proactiva de contexto y CHECKPOINT_PREVENTIVO

**Problema observado (OBJ-001):** La compresión ocurrió durante ejecución activa, dejando el entorno de control sin capturar en el checkpoint de reanudación.

**Patrón:** Antes de iniciar cada fase mayor (FASE 2, 3, 4, 6), el orquestador estima el consumo esperado. Si la fase completa llevaría el contexto al **70%** → escribir checkpoint antes de empezar (no esperar el trigger reactivo del 60%).

**El checkpoint debe incluir sección `control_environment`:**
```json
{
  "control_environment": {
    "security_agent": "APROBADO|EN_EJECUCION|PENDIENTE",
    "audit_agent": "APROBADO|EN_EJECUCION|PENDIENTE",
    "coherence_agent": "APROBADO|EN_EJECUCION|PENDIENTE",
    "standards_agent": "APROBADO|EN_EJECUCION|PENDIENTE",
    "active_gates": ["GATE_2_T04a"],
    "pending_verdicts": []
  }
}
```

**CHECKPOINT_PREVENTIVO en FASE 4:** Antes de crear el worktree de cada tarea, el Domain Orchestrator verifica si tarea + gates cabrían en el contexto restante. Si no → escribe checkpoint completo primero, emite `CHECKPOINT_PREVENTIVO` al Master, y solo entonces crea el worktree.

---

## 2026-03-17 — Push de ramas artifact en FASE 8

**Patrón (OBJ-001):** Al cerrar un objetivo Nivel 2, pushear todas las ramas artifact al remoto como parte de FASE 8, junto con el push de main.

**Por qué:** Conserva trazabilidad completa del proceso PIV/OAC: qué hizo cada tarea, diffs por gate, historial de integración progresiva. Permite auditar la ejecución del protocolo a posteriori.

**Cómo:**
```bash
git push origin feature/T-* staging main
```
Ejecutar en FASE 8 después del merge Gate 3. Las ramas directivas (`agent-configs`) tienen su propio ciclo de push independiente.

---

## 2026-03-22 — Patrón: Separación contracts/ como capa canónica

Cuando múltiples agentes referencian los mismos criterios (gates, modelos, rubrics):
crear un directorio `contracts/` con archivos de fuente única. Los registry files referencian
por sección — nunca duplican el contenido.
Sesión origen: PIV/OAC v3.3 redesign (OBJ-002).

---

## 2026-03-13 — Auditoría antes de implementación

**Patrón de mayor impacto:** Un informe técnico exhaustivo ANTES de escribir código:
1. Identifica gaps que los tests no cubrían
2. Previene regresiones al conocer el estado real
3. Da contexto de seguridad a todos los agentes antes de que toquen el código

Aplicar en FASE 4 gate de plan: el plan debe incluir una fase de auditoría previa si el dominio tiene código existente.

---

## 2026-03-23 — Patrón Astillero: desacoplamiento de producto

**Evento:** Primer desacoplamiento ejecutado — EthQuery API extraída de lab/ a repo independiente.

**Producto desacoplado:** EthQuery API (OBJ-001)
**Repo destino:** https://github.com/DavidCaastro/ethquery-api.git
**Ramas transferidas:** main (27 commits), staging (26 commits), feature/T-01..T-05, fix/ci-broken-jobs
**Integridad verificada:** SHA main `d6376d0` == remoto PASS | SHA staging `3c05e64` == remoto PASS
**Skill documentado:** `skills/decoupling.md`

**Patrón operativo confirmado:**
- `git push <nuevo-remote> <ramas>` transfiere historia git completa sin pérdida
- El astillero (lab/) mantiene exclusivamente agent-configs tras la limpieza
- El producto desacoplado es completamente autónomo — no depende de lab/ para operar
- El repo destino debe estar vacío antes del push para evitar conflictos de historia

**Condición de aplicación:** Activar `skills/decoupling.md` cuando el usuario emite confirmación explícita de desacoplamiento con URL de repo destino.
