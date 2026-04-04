# Especificaciones de Arquitectura — SecOps Scanner
> Cargado por: Master Orchestrator (construcción del DAG) + Domain Orchestrators
> Fuente de verdad para la orquestación — no para los requisitos de negocio.

---

## Stack Tecnológico

| Componente | Tecnología | Versión mínima | Restricción |
|---|---|---|---|
| Lenguaje principal | Python | 3.11 | Solo stdlib para análisis — sin dependencias de terceros en motores |
| AST Python | `ast` (stdlib) | 3.11 | No requiere instalación |
| AST JavaScript | Parser propio sobre `node --print` o implementación Python | Node 18 (opcional) | Si node no disponible → modo degradado (análisis de texto) |
| CLI | `argparse` (stdlib) | 3.11 | Sin click ni typer |
| Output JSON | `json` (stdlib) | 3.11 | — |
| Output Markdown | Template strings Python | — | Sin Jinja2 ni dependencias de templating |
| Descarga de fuente | `urllib` / `tarfile` (stdlib) | 3.11 | Sin requests — solo stdlib |
| Concurrencia T2 | `subprocess` / `threading` (stdlib) | 3.11 | T2 lanza proceso hijo, no bloquea sesión |

---

## Arquitectura por Capas

```
CLI Layer          ← cli.py — entrada de usuario, routing a trigger correcto
      ↓
Orchestration Layer ← main.py — coordina Detection + Fetch + Analysis + Output
      ↓
Analysis Layer     ← taint_analyzer.py, contract_verifier.py, behavioral_delta.py
      ↓
Infrastructure Layer ← detect.py, fetcher.py, ast_engine.py, progress.py
      ↓
Output Layer       ← report.py, impact.py, bridge.py
```

**Regla:** Ninguna capa importa de la capa superior. `ast_engine.py` no conoce a `taint_analyzer.py`. `report.py` no conoce a `main.py`. Violación → rechazo en Gate 2.

---

## Estructura de Módulos del Producto

```
secops/
├── SECOPS.md                    ← protocolo y configuración (scan_interval, targets, thresholds)
├── __main__.py                  ← entry point: python -m secops
│
├── scanner/
│   ├── main.py                  ← orquestador: coordina T0/T1/T2 y CLI
│   ├── detect.py                ← RF-01: detección de lenguajes por manifests
│   ├── fetcher.py               ← RF-02: descarga y caché de fuente de dependencias
│   ├── ast_engine.py            ← RF-03: parseo de fuente a AST por lenguaje
│   ├── progress.py              ← renderizado de barra de progreso en CLI (ProgressEvent + ConsoleProgressRenderer)
│   ├── taint_analyzer.py        ← RF-04: flujo fuente→sink sin sanitización
│   ├── contract_verifier.py     ← RF-05: opciones de config no enforceadas en todos los paths
│   ├── behavioral_delta.py      ← RF-06: nuevos edges en call graph entre versiones
│   ├── report.py                ← RF-07: generación de reporte Markdown
│   ├── impact.py                ← RF-08: escritura append-only de impact_analysis.jsonl
│   ├── bridge.py                ← RF-09: generación de payload.json para SecurityAgent
│   └── cli.py                   ← RF-13: interfaz CLI con tres niveles de granularidad
│
├── deps_cache/                  ← código fuente de dependencias (gitignored)
│   └── <dep>/<version>/         ← fuente real descargada por fetcher.py
│
├── bridge/
│   ├── payload.json             ← SecurityAgent lee esto en T0 (RF-09, RF-10)
│   └── component_risk.json      ← Domain Orchestrator consulta en T1 (RF-12)
│
├── records/
│   ├── scans.jsonl              ← historial append-only de scans ejecutados
│   ├── impact_analysis.jsonl    ← RF-08: hallazgos con reachability y evidencia
│   └── baseline.json            ← último estado limpio conocido para delta
│
└── reports/
    └── YYYY-MM-DD_HH_scan.md    ← RF-07: reportes humano-legibles por scan
```

**Archivos gitignored:** `deps_cache/`, `secops/reports/` — son artifacts de runtime. `impact_analysis.jsonl` SÍ se versiona (evidencia permanente para responsible disclosure). `bridge/payload.json` y `bridge/component_risk.json` están actualmente en el repo (commit `28153f5`) — decisión pendiente de usuario: excluir del repo o mantener como estado inicial conocido.

---

## DAG de Tareas

| ID | Tarea | Tipo | Expertos | Depende de | Skills |
|---|---|---|---|---|---|
| T-01 | Infraestructura base: detect + fetcher + ast_engine | SECUENCIAL | 1 | — | skills/testing.md, skills/layered-architecture.md |
| T-02 | Taint Analyzer | SECUENCIAL | 1 | T-01 | skills/backend-security.md, skills/testing.md |
| T-03 | Contract Verifier | PARALELA con T-02 | 1 | T-01 | skills/testing.md |
| T-04 | Behavioral Delta (call graph integrado en behavioral_delta.py) | PARALELA con T-02 | 1 | T-01 | skills/testing.md |
| T-05 | Output Engine: report + impact + bridge | SECUENCIAL | 1 | T-02, T-03, T-04 | skills/standards.md |
| T-06 | Triggers + CLI: main + cli + component_map | SECUENCIAL | 1 | T-05 | skills/testing.md |
| T-07 | Integración SecurityAgent: actualizar registry | SECUENCIAL | 1 | T-06 | skills/inter-agent-protocol.md |
| T-08 | Tests y validación contra casos axios conocidos | SECUENCIAL | 1 | T-07 | skills/testing.md |

**Verificaciones de gate por fase:**
- Tras T-01: detect + fetch + parse sin errores en proyecto real
- Tras T-02/T-03/T-04: detección correcta de CVE-2025-27152, CVE-2025-58754 y supply chain axios@1.14.1
- Tras T-06: los tres niveles de CLI producen output coherente
- Tras T-08: cobertura ≥90%, 0 falsos negativos en casos de referencia axios

---

## Gestión de Orquestación (OAC)

- **Aislamiento:** Worktrees por experto (`./worktrees/<tarea>/<experto>/`)
- **Rama de desarrollo:** `feature/secops-scanner` desde `main`
- **Flujo de ramas:** `feature/secops-scanner/<experto>` → `feature/secops-scanner` → `staging` → `main`
- **Post-main:** crear rama `sec-ops` como rama directive pasiva. Mover módulo. Configurar como standalone. **[PENDIENTE — aún no ejecutado]**
- **Modelo de razonamiento:** Sonnet para implementación de motores; Haiku para validaciones mecánicas y output templates

---

## Separación de Responsabilidades

| Componente | Responsabilidad única |
|---|---|
| `detect.py` | Solo detecta lenguajes. No descarga, no analiza. |
| `fetcher.py` | Solo descarga y cachea. No parsea, no analiza. |
| `ast_engine.py` | Solo parsea a AST. No analiza semántica. |
| `taint_analyzer.py` | Solo traza flujo fuente→sink. No genera reports. |
| `contract_verifier.py` | Solo verifica contratos de config. No genera reports. |
| `behavioral_delta.py` | Solo compara call graphs. No genera reports. |
| `report.py` | Solo genera Markdown. No analiza. |
| `bridge.py` | Solo genera payload.json + component_risk.json. No analiza. |
| `cli.py` | Solo parsea args y delega a main.py. |
| `progress.py` | Solo renderiza barra de progreso en stdout. Sin lógica de negocio. |
