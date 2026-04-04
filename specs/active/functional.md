# Especificaciones Funcionales — SecOps Scanner
> ISO/IEC/IEEE 29148:2018 — Requerimientos Funcionales verificables
> Escritura: consolidado desde sesión de diseño 2026-04-03
> Un RF es CUMPLIDO solo si tiene evidencia de archivo:línea verificable

---

## Intención General del Sistema

SecOps Scanner es un módulo de análisis de seguridad autónomo que opera 100% local,
sin LLM ni herramientas de terceros. Detecta vulnerabilidades en dependencias mediante
análisis semántico propio (taint analysis, contract verification, behavioral delta)
y produce registros persistentes que SecurityAgent consume sin costo de contexto adicional.
Su objetivo es detectar riesgos conocidos y potenciales zero-days antes de que sean publicados.

---

## Requerimientos Funcionales

---

### RF-01 — Detección de lenguajes por manifests

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | El módulo lee el directorio del proyecto y detecta automáticamente los lenguajes presentes a partir de sus archivos de manifiesto: `requirements.txt` / `pyproject.toml` (Python), `package.json` (JS/TS), `Cargo.toml` (Rust), `go.mod` (Go). Sin input manual del usuario. |
| Criterio de aceptación | Dado un proyecto con cualquier combinación de manifests, `detect.py` retorna un dict `{lenguaje: [paths de manifests]}` correcto en <500ms. Sin falsos negativos para los 4 lenguajes soportados. |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/detect.py:detect_languages()` — retorna dict {lenguaje: [paths]} |

---

### RF-02 — Source Fetcher: descarga de fuente real de dependencias

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | Para cada dependencia detectada, el módulo descarga y cachea el código fuente real (no metadatos de versión) en `secops/deps_cache/<dep>/<version>/`. Solo descarga si la versión no está en caché. Soporta Python (PyPI sdist/wheel), JS (npm registry tarball). |
| Criterio de aceptación | Dado `requirements.txt` con N dependencias, `fetcher.py` descarga todas a `deps_cache/`. Segunda ejecución usa caché (0 descargas). Código fuente legible y completo en disco. |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/fetcher.py:fetch_dependency()` — descarga + caché + verificación SHA-256 |

---

### RF-03 — AST Engine: parseo de fuente a árbol sintáctico

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | El módulo parsea el código fuente de cada dependencia cacheada a su AST correspondiente. Python: módulo `ast` de stdlib. JS: parser propio sobre salida de `node --print` o implementación pura Python de parser JS mínimo. El AST resultante es navegable por los tres motores de análisis. |
| Criterio de aceptación | `ast_engine.py` parsea el código fuente de axios (JS) y cryptography (Python) sin errores. El AST expone nodos de tipo: función, llamada, asignación, import, acceso a propiedad. |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/ast_engine.py:parse_file(), parse_source_tree()` — soporta Python (ast stdlib) y JS |

---

### RF-04 — Taint Analyzer: flujo de datos no confiables a sinks

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | El motor traza el flujo de datos desde fuentes no confiables (input de usuario, red, variables de entorno, archivos externos) hasta sinks peligrosos (allocación de memoria sin límite, llamadas de red, ejecución de procesos, acceso a filesystem). Si hay un path fuente→sink sin nodo de sanitización/validación intermedio, genera un hallazgo `TAINT_FLOW`. No depende de patrones predefinidos — razona desde la estructura del flujo. |
| Criterio de aceptación | Dado el código fuente de axios ≤1.7.9, `taint_analyzer.py` genera hallazgo `TAINT_FLOW` en `buildFullPath.js` (URL externa → llamada de red sin validación de dominio). Dado axios 1.8.2 (corregido), no genera ese hallazgo. |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/taint_analyzer.py:analyze()` — traza SOURCES→SINKS, genera Finding tipo TAINT_FLOW |

---

### RF-05 — Contract Verifier: configuraciones que no se cumplen en todos los paths

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | El motor detecta opciones de configuración con semántica de restricción (nombres: `allow*`, `max*`, `limit*`, `restrict*`, `safe*`, `block*`) y verifica que estén chequeadas en TODOS los code paths que ejecutan el comportamiento que dicen restringir. Un path que ignora la opción genera un hallazgo `CONTRACT_VIOLATION`. |
| Criterio de aceptación | Dado axios ≤1.7.9, `contract_verifier.py` detecta `CONTRACT_VIOLATION` en `allowAbsoluteUrls`: la opción existe en el HTTP adapter pero los adapters XHR y Fetch no la chequean. Dado axios ≥1.8.2, no detecta esa violación. Dado axios ≤1.13.x, detecta `CONTRACT_VIOLATION` en `maxContentLength`/`maxBodyLength`: el path `data:` URI los ignora. |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/contract_verifier.py:verify()` — detecta RESTRICTION_PREFIXES no enforceados en todos los paths, genera CONTRACT_VIOLATION |

---

### RF-06 — Behavioral Delta: detección de nuevos comportamientos entre versiones

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | El motor construye el call graph de v_anterior y v_nueva de cada dependencia desde el AST. Compara los edges de ambos grafos. Edges nuevos en v_nueva que apuntan a operaciones privilegiadas (llamadas de red a hosts externos, ejecución de procesos, lectura de variables de entorno, escritura de archivos fuera del scope esperado) generan un hallazgo `BEHAVIORAL_ANOMALY`. Este motor es la defensa principal contra supply chain attacks. |
| Criterio de aceptación | Dado axios 1.14.0 vs 1.14.1 (supply chain attack), `behavioral_delta.py` detecta `BEHAVIORAL_ANOMALY`: edges nuevos hacia callbacks de red externos y ejecución de procesos inexistentes en 1.14.0. Dado axios 1.7.9 vs 1.8.2 (fix legítimo), genera hallazgo informativo pero no ANOMALY crítico. |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/behavioral_delta.py:analyze_delta(), build_call_graph()` — compara call graphs entre versiones, detecta edges nuevos a PRIVILEGED_OPERATIONS |

---

### RF-07 — Report Generator: reporte en lenguaje natural

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | El Output Engine genera `secops/reports/YYYY-MM-DD_HH_scan.md` con todos los hallazgos de los tres motores. El reporte incluye: dependencia afectada, tipo de hallazgo (TAINT_FLOW / CONTRACT_VIOLATION / BEHAVIORAL_ANOMALY), severidad inferida por el motor (no CVSS externo), evidencia de archivo:línea, y descripción en lenguaje natural del riesgo. Incluye TODOS los hallazgos sin filtro por severidad. |
| Criterio de aceptación | Tras un scan completo, el archivo `.md` existe, es legible, contiene todos los hallazgos detectados con su evidencia, y no requiere herramientas externas para generarse. |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/report.py:generate_report()` — genera `YYYY-MM-DD_HH_scan.md` con todos los hallazgos |

---

### RF-08 — Impact Analysis: registro de alcanzabilidad por hallazgo

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | El módulo escribe `secops/records/impact_analysis.jsonl` en modo append-only. Por cada hallazgo: `{date, dep, version, finding_type, severity, reachable, call_path, evidence, action}`. El campo `reachable` indica si el código del proyecto invoca el path vulnerable. Sirve como evidencia para reporte a la comunidad (responsible disclosure). |
| Criterio de aceptación | El archivo JSONL crece con cada scan. Cada entrada es JSON válido. El campo `reachable` refleja el resultado del Call Tracer para el proyecto activo. Entradas previas nunca se modifican (append-only verificable). |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/impact.py:append_findings()` — escribe `impact_analysis.jsonl` en modo append-only |

---

### RF-09 — SecurityAgent Bridge: payload pre-generado para consumo en sesión

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | El módulo genera `secops/bridge/payload.json` al final de cada scan. Este archivo es el único punto de contacto con el sistema PIV/OAC. SecurityAgent lo lee en FASE 0 sin ejecutar ningún scanner. Contiene: `scan_timestamp`, `risk_level` (LOW/MEDIUM/HIGH/CRITICAL), conteos por severidad, `component_risk` (mapa componente→hallazgos), `action_required`, `summary_for_agent` (texto para el agente). |
| Criterio de aceptación | `payload.json` es JSON válido. Se actualiza tras cada scan T2. SecurityAgent puede leerlo en <100ms. El campo `summary_for_agent` es una cadena de texto legible sin necesidad de parsear el resto del JSON. |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/bridge.py:write_payload(), write_component_risk()` — genera `payload.json` + `component_risk.json` |

---

### RF-10 — T0: trigger de sesión (solo lectura, sin escaneo)

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | Al iniciar sesión, el sistema lee `secops/bridge/payload.json` sin ejecutar ningún scanner. Si el archivo no existe o tiene más de 24h, registra advertencia pero no bloquea la sesión. El tiempo de ejecución de T0 es <1 segundo. |
| Criterio de aceptación | Con payload.json existente, T0 retorna en <1s. Con payload.json ausente, retorna advertencia y `risk_level: UNKNOWN` sin error fatal. Sin llamadas de red ni parseo de AST. |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/main.py:t0_session_read()` — lectura payload.json <1s, retorna UNKNOWN si ausente o corrompido |

---

### RF-11 — T2: scan completo en background

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | El scan completo (Detection + Source Fetch + AST + tres motores + Output) corre en background, sin bloquear la sesión activa. Intervalo configurable en `SECOPS.md` (default: 6h). Al finalizar actualiza `payload.json`, `impact_analysis.jsonl` y genera el reporte `.md`. |
| Criterio de aceptación | T2 completa sin interacción del usuario. El proceso no bloquea ninguna operación de Claude Code. `payload.json` tiene `scan_timestamp` actualizado tras cada ejecución. |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/main.py:run_t2_background()` — lanza subprocess hijo con `python -m secops scan`, no bloquea sesión |

---

### RF-12 — T1: trigger pre-componente

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | MEDIA |
| Descripción | Antes de que un Domain Orchestrator despache un specialist a trabajar en un componente, consulta `secops/bridge/component_risk.json`. Si el componente tiene hallazgos `CRITICAL` o `HIGH` con `reachable: true`, notifica al SecurityAgent antes de que el specialist arranque. Consulta en <1s (solo lectura de JSON). |
| Criterio de aceptación | Dado `component_risk.json` con componente `auth` en CRITICAL, T1 retorna alerta antes de despachar specialist. Dado componente `utils` en LOW, T1 retorna clear y el specialist arranca sin interrupción. |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/main.py:t1_component_check()` — consulta `component_risk.json` <1s, retorna nivel de riesgo del componente |

---

### RF-13 — CLI: trigger manual con tres niveles de granularidad

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | El módulo expone una CLI con tres niveles de granularidad: (1) `python -m secops scan` — scan completo de todas las dependencias detectadas; (2) `python -m secops scan --dep <nombre>` — scan de una dependencia específica; (3) `python -m secops scan --dep <nombre> --method <función>` — scan de una función/método específico dentro de una dependencia. Cada nivel produce output coherente con el scan completo. |
| Criterio de aceptación | Los tres comandos ejecutan sin error. `--dep axios` produce hallazgos solo relativos a axios. `--dep axios --method buildFullPath` produce hallazgos solo relativos a esa función. Output de nivel 3 es consistente con lo que el scan completo reportaría para esa función. |
| Estado | CUMPLIDO |
| Evidencia | `secops/scanner/cli.py:run()` — tres niveles: `scan` / `scan --dep` / `scan --dep --method`; routing a `main.py` |

---

### RF-14 — Cero dependencia de herramientas de terceros para análisis

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | ALTA |
| Descripción | Los tres motores de análisis (Taint, Contract, Behavioral Delta) no invocan pip-audit, bandit, semgrep, safety, trivy ni ninguna herramienta externa de seguridad. El análisis es propio. Las únicas dependencias externas permitidas son: stdlib de Python para AST parsing, y acceso de red controlado exclusivamente en el Source Fetcher. |
| Criterio de aceptación | El módulo completa un scan en un entorno sin pip-audit, bandit, semgrep ni trivy instalados. Sin errores de import ni de ejecución relacionados con herramientas de terceros. |
| Estado | CUMPLIDO |
| Evidencia | `pyproject.toml:dependencies=[]` — cero deps runtime. Motores usan solo stdlib (`ast`, `re`, `json`, `urllib`, `tarfile`) |

---

### RF-15 — Cobertura multi-rama: sec-ops, agent-configs y artifacts

| Atributo | Valor |
|---|---|
| Versión | v0.1 |
| Prioridad | MEDIA |
| Descripción | El módulo puede escanear tres superficies distintas: (1) rama `sec-ops` — el módulo se audita a sí mismo; (2) rama `agent-configs` — archivos de protocolo del framework (skills, registry, CLAUDE.md) analizados con Contract Verifier buscando gates bypasseables o permisos excesivos; (3) ramas artifact — código del producto y sus dependencias. La superficie a escanear es configurable en `SECOPS.md`. |
| Criterio de aceptación | Dado `target: agent-configs` en config, el scanner analiza archivos `.md` del framework y reporta inconsistencias contractuales detectables. Dado `target: artifact`, analiza el código Python/JS del producto. Los dos modos producen reportes con secciones diferenciadas. |
| Estado | CUMPLIDO |
| Evidencia | `secops/SECOPS.md:targets` — configurable: `artifact` / `agent-configs` / `sec-ops`. `secops/scanner/main.py` respeta el target al construir la lista de archivos a analizar |
