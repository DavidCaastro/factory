# Especificaciones de Investigación — Preguntas de Investigación (RQs)
> Módulo activo cuando `execution_mode: RESEARCH` o `execution_mode: MIXED`.
> Equivalente de `specs/functional.md` para objetivos de investigación.
> Cargado por: Master Orchestrator, AuditAgent, ResearchOrchestrator.
> NO cargar en modo DEVELOPMENT puro.

---

## Convención de RQs

Cada pregunta de investigación sigue el mismo contrato de verificabilidad que los RFs.
El criterio de resolución define qué evidencia constituye una respuesta satisfactoria —
sin criterio explícito, la RQ es irresolvable por diseño.

```markdown
### RQ-NN — [Título de la pregunta]

| Atributo          | Valor |
|---|---|
| Hipótesis         | [afirmación tentativa que se busca confirmar o refutar] |
| Tipo              | EXPLORATORIA / CONFIRMATORIA / COMPARATIVA |
| Criterio de resolución | [qué evidencia específica constituiría una respuesta satisfactoria] |
| Fuentes esperadas | [tipo: papers / documentación oficial / datos empíricos / benchmarks / etc.] |
| Alcance           | [qué entra en scope] |
| Exclusiones       | [qué queda fuera explícitamente] |
| Estado            | PENDIENTE / EN_PROGRESO / RESUELTA / IRRESOLVABLE |
| Hallazgo          | [síntesis del hallazgo — vacío hasta RESUELTA] |
| Evidencia         | [cita 1], [cita 2], ... |
| Confianza         | ALTA / MEDIA / BAJA |
| Razón si IRRESOLVABLE | [por qué no puede resolverse con los recursos disponibles] |
```

**Confianza ALTA:** ≥2 fuentes independientes TIER-1 o TIER-2 que coinciden.
**Confianza MEDIA:** 1 fuente TIER-2, o múltiples TIER-3 convergentes.
**Confianza BAJA:** Fuente única TIER-3, evidencia indirecta, o fuente no evaluable.

---

## RQs Activas

> Completar esta sección al iniciar un objetivo de investigación.
> El Master Orchestrator valida que exista al menos una RQ antes de construir el DAG.

*(sin RQs activas — objetivo de investigación no iniciado)*

---

## Historial de Objetivos de Investigación

| Objetivo | Fecha | RQs resueltas | RQs irresolubles | Confianza promedio |
|---|---|---|---|---|
| — | — | — | — | — |
