# Especificaciones de Calidad — SecOps Scanner
> Cargado por: StandardsAgent (Gate 2), TestWriter (inicio de tarea de tests)
> ISO/IEC 25010:2023 — Non-Functional Requirements del producto

---

## Umbrales de Cobertura de Tests

| Tipo de módulo | Umbral requerido | Herramienta | Estado actual |
|---|---|---|---|
| Motores de análisis (taint, contract, delta) | 100% líneas + ramas | pytest-cov | ✗ FALLA — taint:88%, contract:86%, delta:96% |
| Infraestructura (detect, fetcher, ast_engine) | ≥90% | pytest-cov | ✗ FALLA — detect:42%, fetcher:19%, ast_engine:85% |
| Output Engine (report, impact, bridge) | ≥90% | pytest-cov | ✗ FALLA PARCIAL — report:25%, impact:13%, bridge:95% ✓ |
| CLI | ≥85% | pytest-cov | ✗ FALLA — cli:62% |
| Coverage gate en CI | ≥90% global | `--cov-fail-under=90` | ✗ FALLA — cobertura global: 66% (50/50 tests pasan) |

> Medición: `pytest-cov` ejecutado 2026-04-04 sobre commit `28153f5`. 50 tests, 0 fallos de ejecución. Cobertura insuficiente en módulos con poca cobertura de red/IO (fetcher, impact, report) y en paths de error de los motores.

**Nota:** Los motores de análisis requieren 100% porque son el núcleo de seguridad del módulo. Un path no cubierto en `taint_analyzer.py` es un posible vector de falso negativo.

---

## Casos de Test Obligatorios (Casos de Referencia)

Los siguientes casos deben pasar antes de Gate 2. Son los criterios de aceptación reales del módulo:

| Caso | Input | Resultado esperado | Motor |
|---|---|---|---|
| RF-04 axios ≤1.7.9 | Fuente de axios 1.7.9 | Hallazgo `TAINT_FLOW` en `buildFullPath.js` | Taint Analyzer |
| RF-04 axios ≥1.8.2 | Fuente de axios 1.8.2 | Sin hallazgo `TAINT_FLOW` en esa función | Taint Analyzer |
| RF-05 axios ≤1.7.9 | Fuente de axios 1.7.9 | `CONTRACT_VIOLATION` en `allowAbsoluteUrls` (XHR/Fetch adapters) | Contract Verifier |
| RF-05 axios ≤1.13.x | Fuente de axios 1.13.0 | `CONTRACT_VIOLATION` en `maxContentLength` (path data: URI) | Contract Verifier |
| RF-05 axios ≥1.8.2 | Fuente de axios 1.8.2 | Sin `CONTRACT_VIOLATION` en `allowAbsoluteUrls` | Contract Verifier |
| RF-06 supply chain | axios 1.14.0 vs 1.14.1 | `BEHAVIORAL_ANOMALY` — edges nuevos a red/proceso | Behavioral Delta |
| RF-06 fix legítimo | axios 1.7.9 vs 1.8.2 | Hallazgo informativo, no `BEHAVIORAL_ANOMALY` crítico | Behavioral Delta |
| RF-14 sin terceros | Entorno sin pip-audit/bandit/semgrep | Scan completa sin errores | Todos |
| RF-10 T0 vacío | Sin payload.json | Advertencia `UNKNOWN`, sin error fatal, <1s | Triggers |
| RF-13 CLI nivel 3 | `--dep axios --method buildFullPath` | Solo hallazgos de esa función | CLI |
| progress rendering | CLI con `--progress` | Barra de progreso en stdout, sin error | CLI + progress.py |
| progress T0/scan | `python -m secops t0` / `scan` | ProgressEvent emitido por cada fase | main.py + progress.py |

---

## Requisitos de Calidad de Código

| Métrica | Umbral | Herramienta | Estado actual |
|---|---|---|---|
| Errores de linting | 0 | ruff | NO VERIFICADO — pendiente ejecutar |
| Complejidad ciclomática por función | ≤10 | radon | NO VERIFICADO — pendiente ejecutar |
| Longitud máxima de función | 50 líneas | revisión manual | NO VERIFICADO |
| Dependencias de terceros en runtime | 0 | revisión de imports | CUMPLIDO — `pyproject.toml:dependencies=[]` |
| Uso de `eval` / `exec` en código propio | 0 | grep | NO VERIFICADO — pendiente ejecutar |

---

## Requisitos de Rendimiento

| Operación | Umbral máximo | Condición |
|---|---|---|
| T0 (lectura payload.json) | <1 segundo | Siempre |
| T1 (consulta component_risk.json) | <1 segundo | Siempre |
| CLI `--dep X --method Y` | <10 segundos | Dep en caché |
| CLI `--dep X` | <30 segundos | Dep en caché |
| T2 scan completo | <120 segundos | ≤20 deps en caché |
| Descarga de fuente (fetcher) | No aplica umbral | Red variable — no bloquea sesión |

---

## Requisitos de Documentación

| Elemento | Requisito | Estado actual |
|---|---|---|
| Funciones públicas de cada módulo | Docstring con Args, Returns, Raises | CUMPLIDO — docstrings presentes en funciones públicas |
| `SECOPS.md` | Protocolo completo: config, triggers, formato de output | CUMPLIDO — `secops/SECOPS.md` contiene config, triggers y formato |
| Casos de test | Comentario explicando qué vulnerabilidad real reproduce | CUMPLIDO — tests documentan CVEs y casos de referencia |
| `impact_analysis.jsonl` | Schema documentado con descripción de cada campo | NO VERIFICADO — pendiente revisar |
| `payload.json` | Schema documentado con descripción de cada campo | NO VERIFICADO — pendiente revisar |

---

## Definición de Hecho (Definition of Done)

Un objetivo se considera COMPLETADO solo cuando:

1. RF-01 a RF-15 en estado CUMPLIDO con evidencia de archivo:línea
2. Todos los casos de test obligatorios pasan (0 falsos negativos en referencias axios)
3. Cobertura global ≥90% verificada por pytest-cov, motores al 100%
4. ruff: 0 errores
5. 0 dependencias de terceros en runtime (verificado por revisión de imports)
6. 0 usos de `eval`/`exec` en código propio (verificado por grep)
7. T0 <1s verificado por test de rendimiento
8. Todos los gates PIV/OAC aprobados (Security + Audit + Standards + Coherence)
9. Rama `sec-ops` creada y módulo operativo como standalone
10. Merge a main con confirmación humana explícita
