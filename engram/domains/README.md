# engram/domains/ — Knowledge de Dominio (Capa 2 — PROYECTO)

> Este directorio pertenece a la **Capa 2 — PROYECTO** (`LAYERS.md`).
> Su contenido es específico por proyecto. En la rama del framework (`agent-configs`) está vacío por diseño.

## Propósito

Almacena el knowledge técnico acumulado por Domain Orchestrators y Specialist Agents durante la ejecución de objetivos.

## Estructura por dominio

```
engram/domains/
└── <nombre-dominio>/
    ├── technical.md    ← Decisiones técnicas, patrones de implementación del dominio
    └── patterns.md     ← Patrones reutilizables identificados por los Specialists (opcional)
```

## Ciclo de vida

- **Creado por:** AuditAgent al cierre de la primera sesión del dominio (FASE 8)
- **Actualizado por:** AuditAgent en cada sesión subsiguiente con nuevos aprendizajes
- **Leído por:** Domain Orchestrators (PRIMARY), StandardsAgent (CONDITIONAL), CoherenceAgent (CONDITIONAL)
- **No versionado:** en proyectos privados, puede añadirse a `.gitignore`; en proyectos open-source, se versiona para transferencia de knowledge

## Agentes con acceso

| Agente | Tipo de acceso | Cuándo |
|---|---|---|
| Domain Orchestrators | PRIMARY — lee su propio dominio | Al inicializarse |
| Specialist Agents | PRIMARY — lee patrones del dominio | Al inicializarse |
| AuditAgent | ESCRITURA — actualiza al cierre | FASE 8 |
| StandardsAgent | CONDITIONAL | Si dominio tiene historial de calidad |
| CoherenceAgent | CONDITIONAL | Si hay conflicto en dominio conocido |
| SecurityAgent | NO accede directamente | Recibe fragmentos vía inyección |
