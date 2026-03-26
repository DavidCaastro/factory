# Diagramas de Flujo — PIV/OAC v3.2

> Documentación visual de los procesos del framework. Cada archivo contiene un diagrama Mermaid renderizable.
> Fuente canónica: archivos en `registry/`, `skills/`, y `CLAUDE.md`.

## Índice

| Archivo | Proceso | Agentes involucrados |
|---|---|---|
| [00_clasificacion_nivel.md](00_clasificacion_nivel.md) | Clasificación de nivel (N0 → N1 → N2) | Entry point |
| [01_fase0_preflight.md](01_fase0_preflight.md) | FASE 0: Preflight + recuperación de sesión | Master Orchestrator |
| [02_fase1_master_dag.md](02_fase1_master_dag.md) | FASE 1: Construcción del DAG | Master Orchestrator |
| [03_fase2_entorno_control.md](03_fase2_entorno_control.md) | FASE 2: Creación del entorno de control | Master + todos los superagentes |
| [04_fase3_5_ejecucion.md](04_fase3_5_ejecucion.md) | FASES 3–5: Domain Orchestrators + expertos | Domain Orchestrators, Specialists |
| [05_gate1_coherence.md](05_gate1_coherence.md) | Gate 1: Coherencia (subramas → rama de tarea) | CoherenceAgent |
| [06_gate2_quality.md](06_gate2_quality.md) | Gate 2: Calidad (feature → staging) | Security + Audit + Standards |
| [07_gate3_human.md](07_gate3_human.md) | Gate 3: Confirmación humana + merge a main | Master Orchestrator + usuario |
| [08_fase8_cierre.md](08_fase8_cierre.md) | FASE 8: Cierre, logs, métricas, engram | Audit + Standards + Compliance + Coherence |
| [09_init_protocol.md](09_init_protocol.md) | Protocolo INIT: entrevista 7Q → specs/active/ | Master Orchestrator |
| [10_session_continuity.md](10_session_continuity.md) | Continuidad de sesión: regla del 60% + FASE 0 | Master + Domain Orchestrators |
| [11_bloqueos.md](11_bloqueos.md) | Bloqueos: BLOQUEADA_POR_DISEÑO vs INVESTIGACIÓN_REQUERIDA | Domain Orchestrator → Master → usuario |
| [12_modo_meta.md](12_modo_meta.md) | Modo Meta: Framework Quality Gate | StandardsAgent + SecurityAgent |
| [13_evaluation_precedents.md](13_evaluation_precedents.md) | Ciclo completo de scoring 0-1, torneo entre expertos, y registro de precedentes post-Gate 3 | EvaluationAgent + CoherenceAgent + AuditAgent |

## Convenciones del diagrama

- **Rectángulos redondeados** `([...])`: puntos de inicio y fin
- **Rectángulos** `[...]`: acciones o estados
- **Rombos** `{...}`: decisiones binarias
- **`run_in_background=True`**: paralelismo real — se lanza en el mismo mensaje
- **Flechas con etiqueta** `-->|condición|`: ramas condicionales
- **Subgrafos**: agrupaciones lógicas de pasos relacionados

## Notas

- Los diagramas documentan el protocolo — la fuente canónica son los archivos de `registry/` y `skills/`
- En caso de discrepancia entre un diagrama y el registry correspondiente, el registry prevalece
- Actualizar estos diagramas es responsabilidad del StandardsAgent en FASE 8 de cada objetivo de framework
