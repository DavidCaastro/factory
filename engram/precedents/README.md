# Engram — Precedents: Protocolo Operativo

## Definición
Un precedente es el registro del approach ganador (estrategia, no código) de una ejecución
que completó Gate 3 con score 0-1 ≥ 0.70.

## Estados de un Precedente

REGISTRADO: EvaluationAgent ha completado el scoring post-FASE 5c.
  - NO elegible como input en sesiones futuras
  - Almacenado temporalmente en .piv/active/<objective-id>_precedent_draft.json

VALIDADO: AuditAgent ha confirmado post-Gate 3.
  - Elegible como input en sesiones futuras
  - Escrito en engram/precedents/<precedent_id>.md + registrado en INDEX.md
  - Inmutable una vez escrito (crear nueva versión si el approach mejora)

## Escritor Exclusivo
AuditAgent. EvaluationAgent actúa como sub-agente (profundidad 1) para generar el borrador.
Ningún otro agente escribe en este directorio.

## Schema de Record Individual

Cada precedente es un archivo engram/precedents/<precedent_id>.md con frontmatter:

---
precedent_id: <string único — formato: <task_type>-<yyyymmdd>-<hash4>>
objective_id: <string — join con .piv/completed/>
task_type: <DEV | RESEARCH | META>
decision_made: <descripción corta del approach ganador>
rationale: <por qué ganó — qué evidencia lo sustenta>
outcome: <APROBADO | RECHAZADO | PARCIAL>
total_score: <float 0.0-1.0>
scores_breakdown:
  FUNC: <float>
  SEC: <float>
  QUAL: <float>
  COH: <float>
  FOOT: <float>
confidence_at_decision: <ALTA | MEDIA | BAJA>
superseded_by: <precedent_id | null>
framework_version: "v3.2"
estado: <REGISTRADO | VALIDADO>
---

## Cuerpo del precedente
<descripción completa del approach: qué se hizo, por qué funcionó, cuándo aplicar>

## Condiciones de Aplicabilidad
<cuándo usar este precedente vs cuándo no>

## Anti-patrones Descartados
<qué approaches tuvieron score más bajo y por qué — para no repetirlos>

## Restricción de Inmutabilidad
Una vez escrito en estado VALIDADO, el archivo es append-only.
Para superseder: crear nuevo precedente con superseded_by apuntando al anterior.
El archivo original permanece para auditoría histórica.
