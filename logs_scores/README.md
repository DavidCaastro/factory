# logs_scores/
> Audit trail estructurado del proceso de evaluación 0-1.
> Escritura exclusiva: EvaluationAgent (append-only, JSONL).
> Lectura: AuditAgent (para TechSpecSheet y registro de precedentes).

## Propósito
Registra el detalle del proceso de scoring para cada Specialist Agent evaluado.
Permite reconstruir POR QUÉ un experto ganó sobre otro, con evidencia de herramienta.
Distinto de logs_veracidad/ (que registra acciones del framework) —
logs_scores/ registra calidad de outputs de expertos.

## Estructura de archivos
Un archivo JSONL por sesión: logs_scores/<session_id>.jsonl
Cada línea = un registro de score de un experto (ver schema en contracts/evaluation.md §Schema JSONL)

## Integridad
Al cierre de FASE 8, AuditAgent registra el SHA-256 del archivo de scores en engram/audit/gate_decisions.md.
Mecanismo idéntico al de logs_veracidad/ §Protocolo append-only.

## Retención
Los archivos de logs_scores/ son permanentes (no se eliminan tras Gate 3).
Son la evidencia auditable de por qué cada precedente obtuvo su score.

## Relación con engram/precedents/
logs_scores/<session_id>.jsonl → evidencia numérica del proceso
engram/precedents/<id>.md → síntesis del approach ganador (para uso como input futuro)
Ambos son complementarios. El precedente referencia al log de scores por objective_id.
