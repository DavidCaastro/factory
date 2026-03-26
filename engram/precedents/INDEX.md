# Engram — Precedents Index
> Catálogo de precedentes VALIDADOS del framework PIV/OAC.
> Escritura exclusiva: AuditAgent (por delegación de EvaluationAgent post-Gate 3).
> Lectura: Master Orchestrator en FASE 1 (antes de construir el DAG).
> Solo precedentes en estado VALIDADO son elegibles como input.

## Cómo usar este índice

1. Master Orchestrator lee este índice en FASE 1
2. Filtra por task_type relevante al objetivo actual
3. Ordena por total_score descendente
4. El precedente de mayor score con outcome APROBADO es el candidato primario
5. Ver archivo individual para rationale completo y condiciones de aplicabilidad

## Catálogo de Precedentes

| precedent_id | task_type | total_score | outcome | framework_version | fecha | estado |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | VACÍO |

> Vacío en esta versión. Se llenará con el primer objetivo que complete Gate 3 post-redesign.

## Protocolo de Conflicto

Si dos precedentes del mismo task_type tienen scores incompatibles:
1. No eliminar ninguno
2. Añadir nota ⚠️ CONFLICTO al de score más bajo
3. EvaluationAgent/AuditAgent adjudica en la próxima sesión con score ≥ ambos
4. Hasta resolución: cargar ambos, el DO elige con justificación
