# Especificaciones de Arquitectura — [NOMBRE DEL PROYECTO]
> Cargado por: Master Orchestrator (construcción del DAG) + Domain Orchestrators
> Este módulo define el stack, la estructura de dominios y el DAG de tareas.
> Es la fuente de verdad para la orquestación — no para los requisitos de negocio.

---

## Stack Tecnológico

| Componente | Tecnología | Versión mínima | Restricción |
|---|---|---|---|
| [Componente] | [Tecnología] | [Versión] | [Restricción o —] |

> Completar antes del inicio del primer objetivo. El Master Orchestrator valida que exista
> al menos un componente documentado antes de construir el DAG.

---

## Arquitectura por Capas (obligatoria)

```
[Capa superior]    ← [Responsabilidad]
      ↓ (solo hacia abajo)
[Capa intermedia]  ← [Responsabilidad]
      ↓ (solo hacia abajo)
[Capa inferior]    ← [Responsabilidad]
```

**Regla:** Ninguna capa importa de la capa superior. Violación → rechazo en Gate 2.

> Ejemplo de referencia (stack Python/FastAPI):
> ```
> Transport Layer    ← FastAPI routers, Pydantic schemas, HTTP handlers
>       ↓
> Domain Layer       ← Lógica de negocio pura (sin imports de Transport)
>       ↓
> Data Layer         ← Adaptadores de base de datos / store
> ```

---

## Estructura de Módulos del Producto

```
[PENDIENTE — definir estructura de directorios del producto]
```

> Documentar al inicio del primer objetivo o antes de la FASE 3.
> Los Domain Orchestrators usan esta estructura para crear worktrees por dominio.

---

## Formato de Tarea en el DAG

Cada fila del DAG incluye el campo `Modo` cuando `execution_mode: MIXED`. En modos DEVELOPMENT o RESEARCH puros, el campo se omite (todas las tareas son del mismo tipo).

| Campo | Valores | Descripción |
|---|---|---|
| `Modo` | `DEV` / `RES` | Tipo de tarea. `DEV` = código + tests. `RES` = investigación + informe. Solo requerido en MIXED. |

El campo `Modo` determina: Specialist Agents instanciados, checklist de gate de calidad (StandardsAgent), y criterio de completitud (PASS/FAIL vs. confianza ALTA/MEDIA/BAJA).

**Regla de declaración:** El campo `Modo` debe ser declarado explícitamente — nunca inferido por el Master Orchestrator del texto de descripción de la tarea. Si el DAG MIXED no incluye el campo `Modo` en alguna tarea → el Master la marca como `BLOQUEADA_POR_DISEÑO` y solicita al usuario que declare el tipo antes de continuar.

---

## DAG de Tareas

| ID | Tarea | Tipo | Expertos | Depende de | Skills |
|---|---|---|---|---|---|
| T-01 | [nombre] | PARALELA / SECUENCIAL | [N] | — | [skills/...] |

> El Master Orchestrator construye este DAG en FASE 1 y lo presenta al usuario para confirmación.
> En modo MIXED añadir columna `Modo` (DEV/RES).

---

## Gestión de Orquestación (OAC)

- **Aislamiento:** Worktrees por experto (`./worktrees/<tarea>/<experto>/`)
- **Flujo de ramas:** `feature/<tarea>/<experto>` → `feature/<tarea>` → `staging` → `main`
- **Modelo de razonamiento:** Opus para planificación del DAG; Sonnet para generación de código; Haiku para validaciones mecánicas
