# SecOps Scanner — Protocolo y Configuración
> Versión: 0.1 | Rama: feature/secops-scanner → main → sec-ops (future directive)
> Módulo de análisis de seguridad semántico. 100% local. Sin LLM. Sin herramientas de terceros.

---

## Configuración

```yaml
# Modificar estos valores según el proyecto
scan_interval_hours: 6          # Intervalo T2 en background
max_payload_age_hours: 24       # T0 marca stale si el payload tiene más de N horas
targets:
  - artifact                    # Código del producto + dependencias (default)
  # - agent-configs             # Archivos de protocolo del framework
  # - sec-ops                   # El módulo se audita a sí mismo
```

---

## Exclusiones de Patrones de Diseño

Librerías cuyos sinks son patrones de diseño esperados, no vulnerabilidades.
El Taint Analyzer suprime hallazgos TAINT_FLOW para estas combinaciones librería/sink.

Para agregar una exclusión: `prefijo_paquete: sink1, sink2, ...`
El prefijo se compara contra el inicio del nombre del paquete (p.ej. `sqlalchemy` cubre `sqlalchemy-orm`).

```
# ORMs y drivers de base de datos — execute ES la API segura parametrizada
sqlalchemy: execute, cursor.execute
alembic: execute, cursor.execute
asyncpg: execute, cursor.execute
aiosqlite: execute, cursor.execute
psycopg2: execute, cursor.execute
pymysql: execute, cursor.execute
# Motores de templates — eval/exec son su razón de existir
mako: eval, exec, compile
jinja2: eval, exec, compile
chameleon: eval, exec, compile
# Syntax highlighters — compilan expresiones sobre datos de entrada por diseño
pygments: compile, re.compile, exec
# Serialización / parsing — procesan datos externos por diseño
pyyaml: yaml.load
# Frameworks HTTP — los sinks son su API pública
aiohttp: aiohttp
httpx: httpx.get, httpx.post
```

---

## Triggers

| ID | Cuándo | Comando | Bloquea sesión |
|---|---|---|---|
| T0 | Al iniciar sesión Claude Code | `python -m secops t0` | No — solo lectura |
| T1 | Pre-componente (Domain Orchestrator) | `python -m secops check --component <dep>` | No — solo lectura |
| T2 | Background cada 6h (cron/CI) | `python -m secops scan` | No — proceso hijo |
| CLI | Manual | Ver tabla abajo | No |

### CLI — tres niveles de granularidad

```bash
# Scan completo
python -m secops scan

# Solo una dependencia
python -m secops scan --dep axios
python -m secops scan --dep cryptography

# Solo un método/función dentro de una dependencia
python -m secops scan --dep axios --method buildFullPath
python -m secops scan --dep cryptography --method Cipher

# Output JSON (para integración con otras herramientas)
python -m secops scan --json

# T0 explícito
python -m secops t0

# T1 explícito
python -m secops check --component axios
```

---

## Output

| Archivo | Descripción | Versionado |
|---|---|---|
| `secops/bridge/payload.json` | SecurityAgent lee esto en T0 | No (runtime) |
| `secops/bridge/component_risk.json` | Domain Orchestrator consulta en T1 | No (runtime) |
| `secops/records/impact_analysis.jsonl` | Historial append-only con reachability | **Sí** — evidencia permanente |
| `secops/reports/YYYY-MM-DD_HH_scan.md` | Reporte humano-legible | No (runtime) |

---

## Schemas de Output

### payload.json (RF-09)

| Campo | Tipo | Descripción |
|---|---|---|
| `scan_timestamp` | string (ISO 8601) | Fecha y hora del último scan T2 completado |
| `risk_level` | string (LOW/MEDIUM/HIGH/CRITICAL/UNKNOWN) | Nivel de riesgo más alto encontrado en el scan |
| `findings_by_severity` | object | Conteo de hallazgos por severidad: `{CRITICAL, HIGH, MEDIUM, LOW, INFO}` |
| `total_findings` | integer | Total de hallazgos en el scan |
| `deps_scanned` | integer | Número de dependencias analizadas |
| `action_required` | boolean | True si hay hallazgos CRITICAL o HIGH con `reachable: true` |
| `summary_for_agent` | string | Resumen en lenguaje natural para SecurityAgent (sin parseo adicional) |
| `stale` | boolean | True si el payload tiene más de `max_payload_age_hours` horas |

### impact_analysis.jsonl (RF-08)

Cada línea es un JSON con los siguientes campos:

| Campo | Tipo | Descripción |
|---|---|---|
| `date` | string (ISO 8601) | Fecha y hora del hallazgo |
| `dep` | string | Nombre de la dependencia afectada |
| `version` | string | Versión de la dependencia analizada |
| `finding_type` | string (TAINT_FLOW/CONTRACT_VIOLATION/BEHAVIORAL_ANOMALY) | Tipo de hallazgo del motor |
| `severity` | string (CRITICAL/HIGH/MEDIUM/LOW/INFO) | Severidad inferida por el motor |
| `reachable` | boolean \| null | True si el proyecto importa/usa la dependencia afectada; null si no se pudo determinar |
| `call_path` | string | Path relativo donde se importa la dependencia (ej: `src/app.js:12`) |
| `evidence` | string | Referencia `archivo:línea` de la evidencia en el código de la dependencia |
| `action` | string | Acción sugerida: `upgrade_required`, `monitor`, `investigate`, `review`, `URGENT: ...` |

> Archivo append-only. Las entradas existentes nunca se modifican. Deduplicación por `(dep, version, finding_type, evidence)`.

---

## Integración con SecurityAgent (PIV/OAC)

SecurityAgent debe ejecutar el siguiente paso **en FASE 0**, antes de cualquier gate:

```
SECOPS PRE-LOAD (FASE 0):
  python -m secops t0
  → Leer output: risk_level, summary_for_agent, stale, action_required

  Si risk_level = CRITICAL:
    → Emitir alerta al Master Orchestrator antes de Gate 2
    → Incluir summary_for_agent en el contexto del gate
  Si stale = True:
    → Registrar advertencia: "Datos SecOps desactualizados (>24h)"
    → Continuar — no bloquear por datos stale
  Si action_required = True:
    → Añadir al checklist Gate 2: revisar impact_analysis.jsonl
```

---

## Motores de análisis

| Motor | Archivo | Detecta |
|---|---|---|
| Taint Analyzer | `scanner/taint_analyzer.py` | Flujo de datos no confiables a sinks sin sanitización |
| Contract Verifier | `scanner/contract_verifier.py` | Opciones de config con semántica de restricción no enforceadas en todos los paths |
| Behavioral Delta | `scanner/behavioral_delta.py` | Nuevos comportamientos entre versiones (supply chain, cambios silenciosos) |

**Principio:** Los motores no usan bases de datos de CVEs ni patrones predefinidos de vulnerabilidades conocidas. Razonan desde la estructura semántica del código.

---

## Casos de referencia validados

| Caso | CVE / Evento | Motor que lo detecta |
|---|---|---|
| axios ≤1.7.9 SSRF | CVE-2025-27152 | Taint Analyzer + Contract Verifier |
| axios ≤1.13.x DoS | CVE-2025-58754 | Contract Verifier (maxContentLength ignorado en data: path) |
| axios@1.14.1 supply chain | Sin CVE — RAT inyectado | Behavioral Delta (edges nuevos a red/proceso) |

---

## Estructura de directorios

```
secops/
├── SECOPS.md              ← este archivo
├── __init__.py
├── __main__.py            ← python -m secops
├── scanner/
│   ├── __init__.py
│   ├── detect.py          ← RF-01
│   ├── fetcher.py         ← RF-02
│   ├── ast_engine.py      ← RF-03
│   ├── taint_analyzer.py  ← RF-04
│   ├── contract_verifier.py ← RF-05
│   ├── behavioral_delta.py  ← RF-06
│   ├── report.py          ← RF-07
│   ├── impact.py          ← RF-08
│   ├── bridge.py          ← RF-09
│   ├── main.py            ← RF-10/11/12
│   └── cli.py             ← RF-13
├── bridge/                ← payload.json, component_risk.json
├── records/               ← impact_analysis.jsonl, scans.jsonl
├── reports/               ← reportes .md por scan
└── deps_cache/            ← código fuente de deps (gitignored)
```

---

## Roadmap

| Versión | Feature |
|---|---|
| v0.1 (actual) | Taint + Contract + Delta para Python y JS. CLI tres niveles. |
| v0.2 | Análisis inter-archivo (taint cross-module). Parser JS completo (no regex). |
| v0.3 | Soporte Rust (cargo) y Go. Análisis de extensiones nativas (limitado). |
| v1.0 | Rama `sec-ops` como directive pasiva autónoma. Self-audit del framework. |
