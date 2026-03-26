# .piv/ — Checkpoint y Recuperación de Sesión PIV/OAC

Directorio de estado de sesión para el mecanismo de checkpoint/resume del marco PIV/OAC v3.2.
**No versionado** (incluido en `.gitignore`). Persiste entre sesiones de Claude Code.

---

## Propósito

Permite que una sesión interrumpida (context overflow, crash, cierre de terminal) sea
retomada desde el punto de falla sin re-ejecutar fases ya completadas.

---

## Estructura

```
.piv/
├── README.md                      ← Este archivo
├── active/
│   └── <objetivo-id>.json         ← Estado activo del objetivo en curso
├── completed/
│   └── <objetivo-id>.json         ← Objetivos finalizados (Gate 3 aprobado)
└── failed/
    └── <objetivo-id>.json         ← Objetivos terminados con error no recuperable
```

---

## Formato del Checkpoint (`<objetivo-id>.json`)

```json
{
  "objetivo_id": "OBJ-001",
  "objetivo_titulo": "Descripción breve del objetivo",
  "execution_mode": "DEVELOPMENT | RESEARCH | MIXED",
  "compliance_scope": "FULL | MINIMAL | NONE",
  "modo_meta": false,
  "fase_actual": 3,
  "fases_completadas": [1, 2],
  "timestamp_inicio": "2026-03-15T10:00:00Z",
  "timestamp_ultimo_checkpoint": "2026-03-15T10:45:00Z",
  "rama_base": "staging",
  "tareas": {
    "T-01": {
      "estado": "COMPLETADA | EN_EJECUCIÓN | PENDIENTE | BLOQUEADA | BLOQUEADA_POR_DISEÑO | INVESTIGACIÓN_REQUERIDA | INVALIDADA",
      "rama": "feature/T-01",
      "worktrees": [
        {"experto": "experto-1", "ruta": "worktrees/T-01/experto-1", "rama": "feature/T-01/experto-1"},
        {"experto": "experto-2", "ruta": "worktrees/T-01/experto-2", "rama": "feature/T-01/experto-2"}
      ],
      "gate_1_aprobado": true,
      "gate_2_aprobado": false,
      "gate_2_resultado": "PENDIENTE | APROBADO | RECHAZADO | BLOQUEADO_POR_HERRAMIENTA",
      "plan_rejection_count": 0,
      "plan_version_count": 0,
      "last_rejection_reason": null
    }
  },
  "agentes_activos": [],
  "dag_extensions": [],
  "mitigation_acknowledged": false,
  "notas_recuperacion": ""
}
```

### Estados de Tarea

| Estado | Significado |
|---|---|
| `PENDIENTE` | No iniciada, dependencias no completadas |
| `EN_EJECUCIÓN` | Expertos activos en sus worktrees |
| `GATE_1_PENDIENTE` | Expertos completados, esperando CoherenceAgent |
| `GATE_2_PENDIENTE` | Merge a feature/<tarea> completo, esperando Security+Audit+Standards |
| `COMPLETADA` | En staging, Gate 2 aprobado |
| `BLOQUEADA` | Gate rechazado — requiere revisión |
| `BLOQUEADA_POR_DISEÑO` | Spec insuficiente — el DO no sabe qué construir. Desbloqueo: usuario aclara el requisito. |
| `INVESTIGACIÓN_REQUERIDA` | DO sabe qué construir pero no puede decidir cómo. Desbloqueo: A) usuario responde, B) tarea RES en DAG. |
| `INVALIDADA` | Tarea ya completada o en progreso que debe rehacerse por cambio de objetivo. Desbloqueo: usuario confirma y Master reactiva la tarea. |

---

## Protocolo de Escritura (Domain Orchestrator)

Escribir checkpoint **después de cada evento significativo**:

1. Aprobación de Gate de Entorno de Control (FASE 2 completa)
2. Creación de worktrees (inicio FASE 4)
3. Completado de cada experto (FASE 5)
4. Aprobación de Gate 1 por CoherenceAgent
5. Aprobación de Gate 2 por Security+Audit+Standards
6. Merge a staging completado

```python
# Pseudocódigo — Domain Orchestrator escribe tras cada gate
checkpoint = read_checkpoint(objetivo_id)
checkpoint["tareas"][tarea_id]["gate_2_aprobado"] = True
checkpoint["timestamp_ultimo_checkpoint"] = now_utc()
write_checkpoint(objetivo_id, checkpoint)
```

---

## Protocolo de Lectura (FASE 0 — Master Orchestrator)

```
FASE 0: VERIFICAR CHECKPOINT EXISTENTE
  ├── Listar archivos en .piv/active/
  ├── Si existe <objetivo-id>.json con fase_actual < 8:
  │     → Presentar estado al usuario: "Sesión previa encontrada en FASE X"
  │     → Opciones: [R] Reanudar | [N] Nuevo objetivo | [A] Abandonar
  │     Si reanudar: cargar contexto y saltar a fase_actual
  │     Si abandonar: mover a .piv/failed/ con nota
  └── Si no existe: iniciar protocolo normal desde FASE 1
```

---

## Notas

- Los archivos en `.piv/active/` se mueven a `.piv/completed/` cuando Gate 3 es aprobado
- Los worktrees referenciados pueden no existir si fueron limpiados — el DO los recrea si es necesario
- No incluir credenciales, tokens o contenido de `security_vault.md` en ningún checkpoint

---

## logs_veracidad/intent_rejections.jsonl

Registro append-only de rechazos de intención (FASE 0 — VETO).
- Escritura: Master Orchestrator exclusivamente
- Formato: JSONL (una línea JSON por evento)
- Campos: timestamp, objective_sha256, reason_category, summary, agent, phase
- No modificar entradas existentes — solo append
