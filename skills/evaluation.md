# Skill: Evaluation
> Cargado por: EvaluationAgent al inicializarse en FASE 5.
> Propósito: Guía operativa para scoring 0-1 de outputs de Specialist Agents.
> Contrato de scoring: contracts/evaluation.md (cargar también).

## Cómo evaluar FUNC (Completitud funcional, peso 0.35)

FUNC mide qué porcentaje de los Acceptance Criteria (ACs) de specs/active/functional.md
están satisfechos en el output del experto.

Procedimiento:
1. Leer specs/active/functional.md → extraer lista de ACs del RF objetivo
2. Para cada AC, verificar con git show si existe evidencia en el worktree del experto
3. Evidencia aceptable: código que implementa el AC, test que lo verifica, o ambos
4. Score = ACs_satisfechos / ACs_totales

Señales de score bajo en FUNC:
- El experto implementó la funcionalidad pero no los casos límite del AC
- El AC especifica un comportamiento de error que no está manejado
- El experto resolvió el problema con un approach diferente al especificado (posible desviación arquitectural)

## Cómo evaluar SEC (Seguridad, peso 0.25)

SEC usa herramientas determinísticas. No usar juicio LLM para dimensiones con tool.

Procedimiento:
1. Ejecutar: git show feature/<tarea>/<experto>:src/ | semgrep --config auto (si disponible)
2. Alternativamente: git show + grep de patrones críticos (ver contracts/gates.md §Gate 2b)
3. Score = 1.0 - (findings_criticos / total_checks_ejecutados)
4. 0 findings críticos = score máximo en esta dimensión

BLOQUEADO_POR_HERRAMIENTA: Si semgrep/bandit no está disponible → registrar SEC: N/D en logs_scores/
y notificar al Domain Orchestrator. No estimar el score de SEC.

## Cómo evaluar QUAL (Calidad, peso 0.20)

Combina cobertura de tests y calidad de código.

Cobertura (0.15 del peso total):
- git show + pytest-cov si disponible → score = coverage_pct / 100
- Si no disponible → buscar tests en el worktree; su presencia puntúa, su ausencia no

Calidad (0.05 del peso total):
- ruff si disponible → score = 1.0 - (violations / max_violations_esperadas)
- max_violations_esperadas: usar umbral de specs/active/quality.md si existe, sino 0

## Cómo evaluar COH (Coherencia arquitectural, peso 0.15)

COH es la única dimensión mayoritariamente semántica. Rubric estructurado obligatorio:

Verificar con git show + lectura de specs/active/architecture.md:
[ ] El experto no viola las capas declaradas (Transport/Domain/Data o equivalente)
[ ] Los nombres de módulos/funciones siguen convenciones del proyecto (si declaradas)
[ ] Las dependencias introducidas están en el stack declarado
[ ] El approach no contradice decisiones de arquitectura documentadas en engram/core/

Score: 1.0 si todos los checks pasan, 0.75 si 1 falla, 0.50 si 2 fallan, 0.25 si 3+, 0.0 si contradice decisión crítica documentada.

## Cómo evaluar FOOT (Footprint mínimo, peso 0.05)

FOOT mide si el experto cambió más de lo necesario.

Procedimiento:
git diff --stat feature/<tarea>/<experto> -- vs el plan aprobado por Gate 2

Score = 1.0 si files_changed ≤ files_declared_in_plan
Score = files_declared / files_changed si files_changed > files_declared

Penalización adicional: cambios en archivos no relacionados con la tarea = score 0.0 en FOOT.

## Cuándo emitir RECOMENDACIÓN DE TERMINACIÓN TEMPRANA

Condición: score_intermedio_experto ≥ contracts/evaluation.md::early_termination_threshold
AND min_experts_activos ≥ contracts/evaluation.md::min_experts_to_compare

Formato de recomendación (enviar al Domain Orchestrator):
```
EVAL_EARLY_TERMINATION_RECOMMENDATION:
  expert_winner: <id>
  score_actual: <float>
  checkpoint: <n de N>
  reason: "score ≥ 0.90 en checkpoint <n>"
  experts_to_terminate: [<lista de ids>]
  preserve_branches: true
```

NO ejecutar terminación. Solo emitir la recomendación. El Domain Orchestrator decide.

## Cómo construir el ranking final (FASE 5c)

Al completar todos los expertos:
1. Calcular score agregado de cada experto: suma ponderada de 5 dimensiones
2. Ordenar de mayor a menor
3. El ganador es el de score más alto
4. En empate (diferencia < 0.03): notificar a CoherenceAgent para decisión de fusión selectiva
5. Registrar todos los scores en logs_scores/ JSONL (ganadores y perdedores)
6. Pasar ranking completo a CoherenceAgent como insumo para Gate 1

## Patrones de evaluación a evitar

- NO usar juicio LLM para dimensiones con herramienta asignada
- NO asumir score alto si la herramienta no pudo ejecutarse — usar BLOQUEADO_POR_HERRAMIENTA
- NO comparar scores de rubrics_version distintas como equivalentes
- NO acceder a engram/security/ — si necesitas contexto de seguridad, solicitarlo a SecurityAgent
