# SecOps Scanner

Módulo de análisis de seguridad semántico para dependencias Python y JavaScript.
Opera 100% local, sin LLM, sin herramientas de terceros, sin bases de datos de CVEs.

---

## Qué hace y qué no hace

**Detecta** patrones conocidos de vulnerabilidades en el código fuente real de tus dependencias:
configuraciones que no se validan en todos los code paths, flujo de datos no confiables
hacia operaciones peligrosas, y cambios de comportamiento sospechosos entre versiones.

**No es** un sustituto de auditorías humanas, herramientas de análisis formal ni bases de datos
de CVEs. Un resultado limpio no garantiza ausencia de vulnerabilidades. Ver
[docs/reliability.md](docs/reliability.md) para el análisis detallado de limitaciones.

---

## Arquitectura — Modelo C4

### Nivel 1 — Contexto del sistema

```mermaid
C4Context
    title SecOps Scanner — Contexto del sistema

    Person(dev, "Developer / SecurityAgent", "Inicia sesión, ejecuta tareas, revisa hallazgos")

    System(secops, "SecOps Scanner", "Analiza dependencias del proyecto buscando vulnerabilidades mediante análisis semántico estático")

    System_Ext(pypi, "PyPI Registry", "Repositorio oficial de paquetes Python")
    System_Ext(npm, "npm Registry", "Repositorio oficial de paquetes JavaScript")
    System_Ext(project, "Proyecto activo", "Código fuente del producto bajo desarrollo")

    Rel(dev, secops, "Invoca via CLI / T0 / T1 / T2")
    Rel(secops, pypi, "Descarga código fuente de deps Python", "HTTPS + SHA-256")
    Rel(secops, npm, "Descarga código fuente de deps JavaScript", "HTTPS")
    Rel(secops, project, "Lee manifests y código fuente", "Lectura local")
    Rel(secops, dev, "Entrega payload.json + reportes Markdown + impact_analysis.jsonl")
```

### Nivel 2 — Contenedores

```mermaid
C4Container
    title SecOps Scanner — Contenedores

    Person(dev, "Developer / SecurityAgent")

    Container(cli, "CLI", "Python / argparse", "Interfaz de usuario: scan, t0, check")
    Container(orchestrator, "Orchestrator", "Python / main.py", "Coordina T0, T1, T2. Conecta detection → fetch → analyze → output")
    Container(analysis, "Analysis Layer", "Python", "Tres motores independientes: Taint, Contract, Behavioral Delta")
    Container(infra, "Infrastructure Layer", "Python", "Detección de lenguajes, descarga segura de fuentes, parsing AST")
    Container(output, "Output Layer", "Python", "Reportes Markdown, JSONL append-only, payload JSON para agentes")

    ContainerDb(cache, "deps_cache/", "Filesystem", "Código fuente de dependencias cacheado localmente")
    ContainerDb(bridge, "bridge/", "JSON", "payload.json + component_risk.json para consumo en sesión")
    ContainerDb(records, "records/", "JSONL", "impact_analysis.jsonl — evidencia append-only permanente")

    Rel(dev, cli, "Invoca comandos")
    Rel(cli, orchestrator, "Delega ejecución")
    Rel(orchestrator, infra, "detect → fetch → parse")
    Rel(orchestrator, analysis, "Pasa ParseResults")
    Rel(orchestrator, output, "Pasa Findings")
    Rel(infra, cache, "Lee / escribe código fuente")
    Rel(output, bridge, "Escribe payload.json")
    Rel(output, records, "Escribe impact_analysis.jsonl")
    Rel(dev, bridge, "Lee en T0 / T1 (solo lectura)")
```

### Nivel 3 — Componentes del Analysis Layer

```mermaid
C4Component
    title SecOps Scanner — Componentes del Analysis Layer

    Container_Boundary(analysis, "Analysis Layer") {
        Component(taint, "Taint Analyzer", "taint_analyzer.py", "Detecta flujo de datos no confiables (config.url, req.body, process.env) hacia sinks peligrosos (fetch, exec, Buffer.from) en ventana de 30 líneas")
        Component(contract, "Contract Verifier", "contract_verifier.py", "Detecta opciones de configuración con semántica de restricción (max*, allow*, limit*) que no se validan en todos los code paths")
        Component(delta, "Behavioral Delta", "behavioral_delta.py", "Compara call graphs entre versiones. Detecta edges nuevos hacia operaciones privilegiadas (red, procesos, env)")
    }

    Container_Boundary(infra, "Infrastructure Layer") {
        Component(ast, "AST Engine", "ast_engine.py", "Parser AST: Python (stdlib ast, completo) + JavaScript (parser propio, cobertura parcial)")
        Component(fetcher, "Source Fetcher", "fetcher.py", "Descarga código fuente desde PyPI/npm. Verifica SHA-256, rechaza symlinks y path traversal")
        Component(detect, "Language Detector", "detect.py", "Detecta lenguajes por manifests. Prioriza pyproject.toml sobre requirements.txt")
    }

    Rel(taint, ast, "Consume ParseResult")
    Rel(contract, ast, "Consume ParseResult")
    Rel(delta, ast, "Construye CallGraph desde ParseResult")
    Rel(ast, fetcher, "Lee archivos de deps_cache/")
    Rel(fetcher, detect, "Recibe lista de deps a descargar")
```

### Nivel 4 — Flujo de datos principal

```mermaid
sequenceDiagram
    participant CLI
    participant Orchestrator
    participant Detect
    participant Fetcher
    participant AST
    participant Motores
    participant Output

    CLI->>Orchestrator: run_full_scan(project_root)
    Orchestrator->>Detect: primary_manifests(root)
    Detect-->>Orchestrator: {python: [pyproject.toml], js: [package.json]}
    Orchestrator->>Detect: extract_dependencies(manifest)
    Detect-->>Orchestrator: [{name, version, language}]

    loop por cada dependencia
        Orchestrator->>Fetcher: fetch_dependency(name, version, lang)
        Note over Fetcher: Verifica SHA-256<br/>Rechaza symlinks y<br/>path traversal
        Fetcher-->>Orchestrator: Path a deps_cache/
        Orchestrator->>AST: parse_source_tree(dir, lang)
        AST-->>Orchestrator: [ParseResult]
    end

    Orchestrator->>Motores: taint_analyze(results, dep, version)
    Orchestrator->>Motores: contract_analyze(results, dep, version)
    Orchestrator->>Motores: delta_analyze(old, new, dep, v_old, v_new)
    Motores-->>Orchestrator: [Finding]

    Orchestrator->>Output: generate_report(findings, ...)
    Orchestrator->>Output: write_impact(findings, root, file)
    Orchestrator->>Output: write_payload(findings, bridge_dir)
    Output-->>CLI: {risk_level, findings_count, report_path}
```

---

## Instalación

```bash
# Requiere Python 3.11+
pip install -e .

# Sin dependencias de terceros en runtime — solo stdlib Python
```

---

## Uso rápido

```bash
# T0: leer estado de seguridad al iniciar sesión (< 1s, sin scan)
python -m secops t0

# Scan completo de todas las dependencias
python -m secops scan

# Scan de una dependencia específica
python -m secops scan --dep axios

# Scan de una función específica
python -m secops scan --dep axios --method buildFullPath

# Consultar riesgo de un componente (T1, para orquestadores)
python -m secops check --component axios

# Output JSON para integración con otras herramientas
python -m secops scan --json
```

---

## Exit codes

| Código | Significado |
|---|---|
| `0` | Limpio o riesgo LOW/MEDIUM — no requiere acción inmediata |
| `1` | Hallazgos CRITICAL o HIGH — requiere revisión |
| `2` | Error de uso (argumento inválido, directorio inexistente) |

---

## Outputs

| Archivo | Descripción | Destinatario |
|---|---|---|
| `secops/bridge/payload.json` | Risk level, conteos, resumen para agente | SecurityAgent (T0) |
| `secops/bridge/component_risk.json` | Riesgo por componente/dependencia | Domain Orchestrator (T1) |
| `secops/records/impact_analysis.jsonl` | Hallazgos con reachability, evidencia, acción sugerida | Evidencia permanente / responsible disclosure |
| `secops/reports/YYYY-MM-DD_HHMM_scan.md` | Reporte completo legible por humanos | Developer / revisión manual |

---

## Motores de análisis

### Taint Analyzer
Traza flujo de datos desde fuentes no confiables (`config.url`, `req.body`, `process.env`, etc.)
hacia sinks peligrosos (`fetch`, `exec`, `Buffer.from`, `innerHTML`, etc.).
Detecta paths sin sanitización intermedia en una ventana de análisis por archivo.

**Cobertura garantizada:** CVE-2025-27152 (axios SSRF), CVE-2025-58754 (axios DoS via data: URI).

**Limitación principal:** ventana de análisis por archivo. Flujos interprocedurales o
data flow a través de variables intermedias pueden no detectarse.

### Contract Verifier
Verifica que opciones de configuración con semántica de restricción (`allow*`, `max*`, `limit*`,
`restrict*`, `safe*`, `block*`) se validen en **todos** los code paths que ejecutan
la operación que dicen restringir.

**Cobertura garantizada:** opciones ignoradas en adapters secundarios (XHR/Fetch vs HTTP),
límites de tamaño que no se aplican en paths alternativos (data: URI).

**Limitación principal:** detecta verificación por presencia de nombre, no por semántica.
Una verificación que existe pero no aplica el límite efectivamente puede pasar.

### Behavioral Delta
Construye call graphs de dos versiones y detecta edges nuevos hacia operaciones privilegiadas:
llamadas de red externas (`CRITICAL`), ejecución de procesos (`CRITICAL`), acceso a variables
de entorno (`HIGH`), escritura de archivos (`HIGH`).

**Cobertura garantizada:** supply chain attacks que introducen nuevas llamadas de red o
ejecución de procesos (caso real: axios@1.14.1 RAT).

**Limitación principal:** no detecta ataques que reutilizan operaciones ya existentes
modificando solo sus argumentos (ej: cambiar destino de `fetch` sin añadir nueva llamada).

---

## Cobertura de tests

| Módulo | Cobertura | Tests |
|---|---|---|
| `behavioral_delta.py` | 97% | Supply chain real, fix legítimo, call graph |
| `bridge.py` | 95% | Payload generation, T0/T1 read |
| `cli.py` | 95% | Todos los comandos, exit codes, arg validation |
| `detect.py` | 98% | Todos los parsers (requirements, package.json, Cargo.toml, go.mod, pyproject.toml) |
| `report.py` | 97% | Contenido Markdown, agrupación, jerarquía de riesgo |
| `contract_verifier.py` | 86% | CVE-2025-27152, CVE-2025-58754, principios |
| `taint_analyzer.py` | 85% | CVE-2025-27152, CVE-2025-58754, sanitización |
| `fetcher.py` | 86% | Hash integrity, symlinks, path traversal, zip-slip |
| `impact.py` | 83% | Append-only, deduplicación, reachability |
| **Total** | **88%** | **150 tests** |

Tests de integración verifican el pipeline completo con código real de los CVEs documentados.

---

## Limitaciones conocidas

Ver [docs/reliability.md](docs/reliability.md) para análisis detallado de:
- Qué tipos de vulnerabilidades detecta con fiabilidad
- Falsos positivos y falsos negativos documentados
- Contextos en los que **no debe usarse como garantía única** de seguridad

---

## Estructura del módulo

```
secops/
├── SECOPS.md                    # Configuración: scan_interval, targets, thresholds
├── __main__.py                  # Entry point: python -m secops
├── scanner/
│   ├── main.py                  # Orquestador T0 / T1 / T2 / run_full_scan
│   ├── detect.py                # Detección de lenguajes por manifests
│   ├── fetcher.py               # Descarga segura de fuentes (SHA-256, anti path-traversal)
│   ├── ast_engine.py            # Parser AST Python + JavaScript
│   ├── taint_analyzer.py        # Motor: flujo fuente→sink
│   ├── contract_verifier.py     # Motor: contratos de configuración
│   ├── behavioral_delta.py      # Motor: delta de call graph entre versiones
│   ├── report.py                # Generación de reporte Markdown
│   ├── impact.py                # Registro append-only JSONL
│   ├── bridge.py                # payload.json para SecurityAgent
│   ├── cli.py                   # CLI argparse
│   └── progress.py              # Barra de progreso en terminal
├── bridge/
│   ├── payload.json             # Estado de riesgo actual (T0)
│   └── component_risk.json      # Riesgo por componente (T1)
└── records/
    └── impact_analysis.jsonl    # Evidencia permanente append-only
```

---

## CI

El módulo incluye workflow de CI (`.github/workflows/secops-ci.yml`) que valida en cada
push a `staging` y `main`:

1. Integridad estructural — archivos críticos presentes
2. Cero dependencias runtime — `dependencies=[]` verificado
3. Linting — ruff sin errores
4. Tests + cobertura — pytest ≥85% global, motores ≥85%
5. Sin secretos hardcoded — scan de credenciales en código fuente
