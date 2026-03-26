# ADR-001 — DAG explícito antes de crear agentes

**Estado:** Aceptado | **Fecha:** 2026-03-23 | **Autor:** PIV/OAC Framework

---

## Contexto

Al diseñar el protocolo de orquestación, había dos alternativas para determinar qué tareas ejecutar y en qué orden:

**Opción A — DAG reactivo (estilo LangGraph/AutoGen):** el siguiente agente se selecciona dinámicamente basado en el output del agente anterior. No se conoce el grafo completo antes de iniciar.

**Opción B — DAG declarativo pre-ejecución:** antes de crear cualquier agente o worktree, el MasterOrchestrator construye el grafo completo de dependencias, lo presenta al usuario para validación, y solo entonces comienza la ejecución.

---

## Decisión

Se eligió **Opción B — DAG declarativo pre-ejecución**.

El MasterOrchestrator construye la tabla de tareas con dependencias, tipo (PARALELA/SECUENCIAL), número de expertos y dominio antes de activar el entorno de control. El DAG es validado por `DAGValidator` (detección de ciclos) y presentado al usuario para confirmación explícita.

---

## Razones

1. **Gate bloqueante pre-worktrees:** los worktrees y expertos cuestan tokens y tiempo. Un error de diseño en el grafo descubierto a mitad de ejecución es más caro que descubrirlo en el papel.

2. **Auditabilidad:** el DAG aprobado queda registrado en el checkpoint `.piv/active/<obj>.json`. Si hay una discrepancia post-ejecución entre lo planeado y lo ejecutado, el AuditAgent puede detectarla.

3. **Confirmación humana significativa:** el usuario confirma "qué" se va a hacer antes de que "suceda". Esto cumple el requisito de supervisión humana (EU AI Act Art. 14) de forma verificable.

4. **DAG dinámico compatible:** el protocolo permite extensión del DAG durante FASE 5 con tareas `RES` (investigación), pero solo agregando nodos — nunca modificando el contrato aprobado originalmente.

---

## Consecuencias

- El MasterOrchestrator debe ser capaz de inferir las tareas desde `specs/active/functional.md` sin información adicional del usuario.
- Si la spec no tiene suficiente información para construir el DAG, el sistema pregunta antes de asumir (regla permanente "Información insuficiente").
- El tiempo entre "enviar el objetivo" y "código ejecutándose" incluye la presentación y confirmación del DAG. Para objetivos simples esto es minutos; para complejos puede ser más.

---

## Alternativas consideradas y descartadas

**DAG reactivo (descartado):** sin visibilidad pre-ejecución, imposible detectar dependencias incorrectas hasta que fallan en runtime. No permite confirmación humana significativa. Elegido por LangGraph/AutoGen.

**Lista de tareas plana (descartado):** más simple pero sin capacidad de paralelismo seguro ni detección de ciclos. Usada por CrewAI en modo `sequential`.
