# factory

Repositorio de trabajo del framework PIV/OAC.

## Estructura de ramas

| Rama | Rol | Descripción |
|---|---|---|
| `agent-configs` | Directiva de framework | Framework PIV/OAC v4.0: CLAUDE.md, agent.md, contracts/, skills/, registry/, sdk/ |
| `sec-ops` | Directiva de seguridad | SecOps Scanner: análisis de dependencias, reportes segmentados en `reports/`, CI programado |
| `main` | Entrega de producto | Rama base para ramas de trabajo (`fix/<n>`, `feature/<n>`) → `staging` → `main` |
| `staging` | Integración | Gate de integración antes de main |

## Flujo de trabajo

```
fix/<nombre> ──→ staging ──→ main
feature/<nombre> ──↗
```

Las ramas directivas (`agent-configs`, `sec-ops`) no participan en este flujo.
Solo reciben merges de sus propias ramas de trabajo o commits de `github-actions[bot]`.

## Documentación

- Framework PIV/OAC: `git show agent-configs:agent.md`
- SecOps Scanner: `git show sec-ops:README.md`
- Reportes de seguridad: `git show sec-ops:reports/index.json`
