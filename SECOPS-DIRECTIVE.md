# SECOPS-DIRECTIVE — Configuración de Rama Directiva

> **Rama:** `sec-ops` | **Rol:** pasivo, solo lectura para agentes | **Escritura:** `github-actions[bot]` exclusivamente

Esta rama almacena los resultados del scanner en `reports/`. SecurityAgent lee estos datos
en FASE 0 y dispara el scan automáticamente cuando los reportes están desactualizados.

---

## Targets de Scan

Manifests analizados en cada ejecución del workflow:

| Label | Ref git | Path en ref | Descripción |
|---|---|---|---|
| `piv-oac-sdk` | `agent-configs` | `sdk/pyproject.toml` | Dependencias runtime del SDK PIV/OAC |

Para agregar un nuevo target: editar `.github/workflows/secops-passive.yml`
y añadir el step correspondiente. No modificar este archivo.

---

## Estructura de Reportes

```
reports/
├── index.json                  # Inventario: dep → {version, last_scan, risk_level}
├── anthropic/
│   ├── latest.json             # Resultado del último scan
│   └── YYYY-MM-DD.json         # Snapshot diario
├── httpx/
│   ├── latest.json
│   └── YYYY-MM-DD.json
...
```

Los reportes son append-by-day: si el workflow corre 2x el mismo día, `latest.json`
y el snapshot del día se sobreescriben. Los snapshots de días anteriores se preservan.

---

## Protocolo SecurityAgent (FASE 0)

SecurityAgent lee `sec-ops:reports/index.json` al inicio de cada sesión Nivel 2.

**Flujo:**

1. `git show sec-ops:reports/index.json` → leer inventario
2. Para cada dep con `risk_level: CRITICAL | HIGH`:
   - `git show sec-ops:reports/<dep>/latest.json` → detalle de hallazgos
3. Consolidar alerta antes de presentar el DAG al usuario
4. Usuario decide: **aceptar riesgo** / **buscar alternativa** / **generar compliance doc**

**SecurityAgent NO bloquea automáticamente.** El veredicto es siempre del usuario.

**Si `index.json` no existe o tiene más de 48h:** SecurityAgent dispara `workflow_dispatch`
automáticamente via GitHub API (token `GH_TOKEN` desde MCP o variable de entorno) e informa
al usuario que el scan fue disparado. El DAG continúa sin esperar el resultado — los reportes
estarán disponibles en la próxima sesión. Si `GH_TOKEN` no está disponible, SecurityAgent
emite advertencia pasiva sin bloquear.

---

## Umbrales de Alerta

| Nivel | Acción de SecurityAgent |
|---|---|
| `CRITICAL` | Alerta prominente antes del DAG. Requiere decisión explícita del usuario |
| `HIGH` | Alerta en summary del DAG. Usuario decide |
| `MEDIUM` / `LOW` | Registrado en summary, sin interrupción |
| `CLEAN` | Sin acción — mención opcional en summary |

---

## Triggers del workflow

- **SecurityAgent FASE 0 (principal):** cuando `last_updated` es null o supera 48h, SecurityAgent
  dispara `workflow_dispatch` automáticamente via GitHub API con `ref: sec-ops`.
- **Manual:** `workflow_dispatch` desde GitHub Actions UI o via API con `GH_TOKEN`.
- **TTL de reporte:** 48h (stale si `last_updated` supera este umbral)
