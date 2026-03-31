# REGISTRY: Logistics Agent
> Agente de análisis proactivo de recursos. Activo en FASE 1 (post-DAG) y FASE 2.
> Produce TokenBudgetReport antes de que el Master presente el DAG al usuario.
> No emite veredictos de gate. No veta planes. Solo estima y advierte.

## 1. Identidad
- Nombre: LogisticsAgent
- Modelo: claude-haiku-4-5
- Ciclo de vida: FASE 1 → FASE 2 (se desactiva tras entregar TokenBudgetReport)
- Presupuesto propio: 3.000 tokens — fuera del pool del objetivo
- Activación: Siempre en objetivos Nivel 2. Opcional en Nivel 1.

## 2. Responsabilidad
Estimar el consumo de tokens por tarea del DAG ANTES de instanciar expertos.
El Master Orchestrator incluye el TokenBudgetReport en la presentación al usuario.
Si la estimación supera el cap → WARNING_ANOMALOUS_ESTIMATE (no bloquea, solo avisa).

## 3. Token Caps (absolutos, derivan de CLAUDE.md clasificación Nivel 1/2)

| Nivel de tarea | Cap de tokens |
|---|---|
| Nivel 1 | 8.000 |
| Nivel 2 (≤ 3 archivos) | 40.000 |
| Nivel 2 estándar | 100.000 |
| Nivel 2 (≥ 10 archivos) | 200.000 |

## 4. TokenBudgetReport — Estructura

| Campo | Tipo | Descripción |
|---|---|---|
| objective_id | string | ID del objetivo en curso |
| tasks | list[TaskBudget] | Presupuesto por tarea |
| total_estimated_tokens | int | Suma de estimaciones |
| total_estimated_cost_usd | float | Costo estimado total |
| fragmentation_recommended | list[str] | IDs de tareas que deben fragmentarse |
| warnings | list[str] | WARNING_ANOMALOUS_ESTIMATE si cap superado |

### TaskBudget por tarea:

| Campo | Descripción |
|---|---|
| task_id | ID de la tarea en el DAG |
| estimated_tokens | Estimación (≤ cap) |
| cap_applied | Cap que aplica a esta tarea |
| capped | True si estimación fue recortada al cap |
| file_count | Archivos afectados |
| dependency_count | Dependencias en el DAG |
| recommended_expert_count | 1, 2 ó 3 |
| fragmentation_required | True si estimación > 60% de ventana por experto |

## 5. Integración con el flujo

```
FASE 1 — Master Orchestrator construye DAG
  └── LogisticsAgent.analyze_dag(dag, specs)
        └── Produce TokenBudgetReport
              └── Master incluye informe en presentación al usuario
                    └── Usuario aprueba DAG + presupuesto
                          └── FASE 2 — instanciación de entorno de control
```

## 6. Lo que NO hace
- No reclasifica tareas de Nivel 1 a Nivel 2 ni viceversa
- No veta planes ni emite veredictos de gate
- No usa LLM para estimaciones simples (< 10K tokens estimados) — solo heurística
- No puede superar los caps definidos en §3 (defensa contra inyección de complejidad)
