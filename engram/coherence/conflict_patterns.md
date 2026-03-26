# Átomo: coherence/conflict_patterns
> ACCESO: CoherenceAgent
> CROSS-IMPACT: ninguno registrado aún
> Tipos de conflictos entre expertos paralelos y sus resoluciones.

---

> Bootstrap v3.2 — patrones pre-cargados desde la definición del framework (2026-03-16).
> El CoherenceAgent añadirá entradas reales al cierre de sesiones con expertos paralelos.

---

## Patrones Bootstrap — Conflictos conocidos por diseño del framework

### P-01: Acceso simultáneo a módulo compartido entre capas
```
TIPO: SEMÁNTICO_MAYOR
DESCRIPCIÓN: Dos expertos (domain-layer y transport-layer) modifican simultáneamente
             el mismo módulo de autenticación o de modelos compartidos.
SEÑAL: Diffs de ambos expertos tocan el mismo archivo en la misma sección.
RESOLUCIÓN ESTÁNDAR: CoherenceAgent pausar al experto con menor avance →
                     Domain Orchestrator decide quién es responsable del módulo compartido →
                     El otro experto rebase sobre el resultado.
PATRÓN REUTILIZABLE: SÍ
LECCIÓN: Antes de lanzar expertos paralelos en tareas que comparten módulos de dominio,
         el Domain Orchestrator debe declarar explícitamente en el prompt de cada experto
         qué archivos son de su scope exclusivo vs. compartidos de solo-lectura.
```

### P-02: Naming conflict en constantes o enums entre expertos
```
TIPO: SEMÁNTICO_MENOR
DESCRIPCIÓN: Dos expertos definen constantes con el mismo propósito pero nombres distintos
             (e.g., STATUS_OK vs. HTTP_OK_CODE).
SEÑAL: grep en diffs muestra dos definiciones para el mismo concepto semántico.
RESOLUCIÓN ESTÁNDAR: Usar el nombre más descriptivo y consistente con el estilo del proyecto.
                     El CoherenceAgent propone la resolución; Gate 1 la aprueba.
PATRÓN REUTILIZABLE: SÍ
LECCIÓN: Los Domain Orchestrators deben establecer un glosario de constantes en el
         prompt de los expertos si el dominio tiene vocabulario específico.
```

### P-03: Conflicto de merge técnico en archivos de configuración
```
TIPO: TÉCNICO_GIT
DESCRIPCIÓN: Dos expertos modifican pyproject.toml, requirements.txt o conftest.py
             → marcadores <<<<<<< al hacer merge.
SEÑAL: git merge devuelve conflicto en archivos de configuración raíz.
RESOLUCIÓN ESTÁNDAR: CoherenceAgent evalúa ambas versiones → identifica si son
                     aditivas (se pueden combinar) o excluyentes (elegir una).
                     Aditivas: combinar manualmente preservando ambos cambios.
                     Excluyentes: escalar al Domain Orchestrator para decisión de diseño.
PATRÓN REUTILIZABLE: SÍ
LECCIÓN: Los archivos de configuración raíz deben asignarse a un solo experto.
         El segundo experto declara sus dependencias/fixtures en un archivo separado
         y el DO los integra antes del Gate 1.
```

## Formato de entrada

```
[FECHA] CONFLICTO en feature/<tarea>
TIPO: SEMÁNTICO_MENOR | SEMÁNTICO_MAYOR | SEMÁNTICO_CRÍTICO | TÉCNICO_GIT
EXPERTOS INVOLUCRADOS: <lista>
DESCRIPCIÓN: <qué diverge>
RESOLUCIÓN: <cómo se resolvió>
PATRÓN REUTILIZABLE: SÍ | NO
LECCIÓN: <si PATRÓN REUTILIZABLE=SÍ>
```

---

## Sesión 2026-03-22 — Redesign PIV/OAC v3.3

### Conflicto 1: Autoridad dual en Gate 1
- Agentes: CoherenceAgent (Gate 1) vs EvaluationAgent (scoring pre-Gate 1)
- Naturaleza: solapamiento de señales — uno provee métricas, otro emite veredicto
- Resolución: separación de dominios → EvaluationAgent = datos de entrada (scores 0-1), CoherenceAgent = único árbitro del veredicto
- Patrón generalizable: cuando un nuevo agente produce outputs que informan a un gate, declarar explícitamente si tiene capacidad de veto o es solo insumo. Default: insumo, no veto.

### Conflicto 2: Zero-Trust sobre memoria empírica (precedentes)
- Agentes: cualquier agente que cargue engram/precedents/ vs Zero-Trust Metodológico
- Naturaleza: outputs de sesiones anteriores usados sin gate de validación
- Resolución: estados explícitos REGISTRADO/VALIDADO. Solo post-Gate 3 = VALIDADO = elegible como input.
- Patrón generalizable: toda memoria empírica generada por agentes tiene estado de validación antes de ser elegible como input. No existe "confianza implícita" en memoria histórica.

### Conflicto 3: Escritura concurrente sobre el mismo archivo en tareas paralelas
- Agentes: T3 (protocolo) y T4 (skills+engram) — ambos podían necesitar agent.md
- Naturaleza: race condition de escritura en archivo compartido entre tareas paralelas
- Resolución: declarar escritor exclusivo por archivo en el DAG cuando hay riesgo de solapamiento. T3 = escritor exclusivo de agent.md. T4 = solo lectura de agent.md.
- Patrón generalizable: en DAGs paralelos, si dos tareas tocan el mismo archivo, una es escritora y la otra es lectora. Declarar en el plan antes de iniciar. CoherenceAgent debe verificar esta asignación.
