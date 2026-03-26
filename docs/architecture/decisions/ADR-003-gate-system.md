# ADR-003 — Sistema de gates bloqueantes vs. revisiones recomendadas

**Estado:** Aceptado | **Fecha:** 2026-03-23 | **Autor:** PIV/OAC Framework

---

## Contexto

Para controlar la calidad del output de los agentes, había dos modelos:

**Opción A — Revisiones recomendadas:** los agentes emiten advertencias y recomendaciones que el humano puede ignorar. La ejecución continúa independientemente.

**Opción B — Gates bloqueantes:** ciertos puntos en el flujo requieren veredicto explícito `APROBADO` de agentes específicos antes de poder continuar. Un `RECHAZADO` detiene el flujo y requiere corrección.

---

## Decisión

Se eligió **Opción B — Gates bloqueantes** con 4 gates diferenciados:

| Gate | Momento | Responsable | Qué bloquea |
|---|---|---|---|
| Gate 2 | Pre-worktrees | SecurityAgent + AuditAgent | Creación de expertos |
| Gate 1 | Pre-merge subramas | CoherenceAgent | Merge de expertos a rama de tarea |
| Gate 2b | Pre-merge a staging | SecurityAgent + AuditAgent + StandardsAgent | Merge a staging |
| Gate 3 | Pre-merge a main | Todos + humano | Merge a producción |

---

## Razones

1. **El costo de corrección aumenta exponencialmente con el tiempo:** un problema de diseño detectado en Gate 2 (pre-código) cuesta minutos. El mismo problema detectado en Gate 3 (post-implementación) cuesta horas o días. Los gates tempranos son más baratos que la detección tardía.

2. **Separación de responsabilidades verificable:** cada gate tiene responsables específicos con checklists explícitos en `contracts/gates.md`. Esto hace que la responsabilidad de una aprobación sea trazable: "¿quién dijo que este código era seguro?" tiene una respuesta unívoca.

3. **Compliance auditable:** para EU AI Act Art. 9 (evaluación de riesgos), tener un gate documentado con veredicto explícito es evidencia de que el proceso de evaluación ocurrió. Una revisión recomendada no crea la misma trazabilidad.

4. **Prevención de sesgos de confirmación del orquestador:** sin gates, el Domain Orchestrator podría avanzar a producción con output subóptimo porque "se ve bien". Los gates obligan a que agentes especializados den una opinión independiente.

---

## Consecuencias

- El flujo de ejecución es más lento que en frameworks sin gates. Para proyectos que requieren velocidad máxima, PIV/OAC Nivel 1 (micro-tareas) omite la orquestación de gates.
- Un gate rechazado dos veces consecutivas escala al MasterOrchestrator, que notifica al usuario. El sistema no puede quedar bloqueado indefinidamente sin intervención humana.
- El Gate 3 **nunca** ejecuta el merge automáticamente. Requiere confirmación humana explícita en el turno actual. Esto es por diseño y no es configurable.
- El protocolo de doble rechazo ("mismo plan") está definido para distinguir ajustes cosméticos de problemas de diseño reales, evitando loops infinitos.

---

## Alternativas consideradas y descartadas

**Revisiones recomendadas (descartado):** usado por LangGraph, AutoGen, CrewAI. Flexible pero sin trazabilidad de quién aprobó qué. Un bug de seguridad puede llegar a producción si el humano ignora la advertencia.

**Un único gate final (descartado):** reduce overhead pero mueve toda la detección al final, cuando el costo de corrección es máximo. Equivalente al modelo de code review tradicional sin integración continua.
