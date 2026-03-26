# Métricas de Precedentes — Schema
> Esquema para el seguimiento histórico del sistema de precedentes.
> Actualizado por AuditAgent en FASE 8b (post-Gate 3).
> Solo precedentes en estado VALIDADO se incluyen en estas métricas.

## Campos por Precedente Registrado

| Campo | Tipo | Descripción |
|-------|------|-------------|
| precedent_id | string | Identificador único del precedente |
| objective_id | string | Sesión de origen |
| task_type | enum: DEV/RESEARCH/META | Tipo de tarea |
| total_score | float [0.0, 1.0] | Score del approach ganador |
| framework_version | string | Versión del framework al momento del registro |
| fecha_validacion | ISO 8601 | Cuándo pasó a estado VALIDADO |
| veces_cargado | int | N sesiones donde este precedente fue cargado como input |
| score_promedio_acumulado | float | Promedio de scores de sesiones que usaron este precedente |
| superseded | bool | Si fue supersedido por un precedente más reciente |

## Evolución del Sistema de Precedentes (métricas agregadas)

Registrar en metrics/sessions.md al cierre de cada sesión que registra o usa un precedente:

```
PRECEDENTES_ACTIVOS: <N validados en engram/precedents/>
PRECEDENTES_USADOS_SESION: <N cargados como input en esta sesión>
SCORE_MEJORA_VS_PRECEDENTE: <score_sesion_actual - score_precedente_usado | N/A si no se usó>
```

## Interpretación
- SCORE_MEJORA_VS_PRECEDENTE > 0: el sistema mejoró respecto al precedente (candidato a superseder)
- SCORE_MEJORA_VS_PRECEDENTE < 0: el precedente sigue siendo mejor que la nueva ejecución
- SCORE_MEJORA_VS_PRECEDENTE = N/A: no se usó precedente (primera ejecución del tipo de tarea)

La tendencia de SCORE_MEJORA a lo largo de sesiones mide la convergencia del sistema.
Un sistema convergente mostrará SCORE_MEJORA ≈ 0 o negativo después de varias sesiones
(el precedente es ya tan bueno que es difícil mejorarlo).
