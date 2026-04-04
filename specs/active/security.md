# Especificaciones de Seguridad — SecOps Scanner
> Cargado por: SecurityAgent (exclusivamente)
> El módulo analiza código de terceros — su propia superficie de ataque es crítica.
> ⚠️ ACCESO RESTRINGIDO

---

## Modelo de Amenazas (Threat Model)

| Categoría | Amenaza | Mitigación requerida | Estado |
|---|---|---|---|
| A03 — Injection | Código malicioso en dependencia analizada ejecuta código del host durante el parseo AST | El AST parser NUNCA ejecuta el código analizado. Solo lectura de texto → árbol sintáctico. Sin `eval`, sin `exec`, sin `importlib` sobre código de terceros. | IMPLEMENTADO — `ast_engine.py` usa `ast.parse()` puro; sin `eval`/`exec` en todo el módulo |
| A04 — Insecure Design | El Source Fetcher descarga código arbitrario que podría contener payloads | Descarga a directorio aislado `deps_cache/` sin permisos de ejecución. El contenido nunca se importa como módulo Python. | IMPLEMENTADO — `fetcher.py` extrae a `deps_cache/`, nunca hace `import` del contenido |
| A05 — Security Misconfiguration | `payload.json` escribe datos sensibles (paths internos, secretos detectados) accesibles por otros procesos | `payload.json` contiene solo resúmenes y conteos. Ningún valor sensible literal. Paths absolutos truncados a relativos. | IMPLEMENTADO — `bridge.py:write_payload()` escribe solo `risk_level`, conteos y `summary_for_agent` |
| A09 — Logging Failures | `impact_analysis.jsonl` registra evidencia que podría exponer estructura interna del proyecto | El campo `call_path` en JSONL usa paths relativos. Ningún token, credencial ni valor de variable de entorno en los registros. | IMPLEMENTADO — `impact.py:append_findings()` usa paths relativos en todos los campos |
| Supply Chain | El propio módulo SecOps Scanner puede ser comprometido vía dependencias de desarrollo | El módulo tiene CERO dependencias de terceros en runtime. Solo stdlib Python. Sin `pip install` en el path de producción. | IMPLEMENTADO — `pyproject.toml:dependencies=[]` |
| Behavioral | Un atacante que controla una dependencia puede intentar que el Behavioral Delta no detecte cambios (evasión) | El delta compara AST completo, no hashes de archivo. Cambios ofuscados en texto siguen siendo visibles en AST. | IMPLEMENTADO — `behavioral_delta.py:build_call_graph()` opera sobre nodos AST, no texto |

---

## Principios de Seguridad del Módulo

### Aislamiento del código analizado
- El código de dependencias en `deps_cache/` **NUNCA se importa** como módulo Python
- `ast.parse()` es operación de lectura pura — no ejecuta el código
- Si el parser falla (código malformado) → excepción capturada → hallazgo `PARSE_ERROR`, continúa con siguiente dependencia
- Sin `subprocess` sobre código de dependencias. Sin `exec()`. Sin `eval()`.

### Descarga controlada
- `fetcher.py` descarga solo desde registros oficiales: PyPI (`https://pypi.org/`) y npm (`https://registry.npmjs.org/`)
- Verificación de integridad: hash SHA-256 del tarball antes de extraer (comparado contra el hash publicado en el registro)
- Si el hash no coincide → `FETCH_INTEGRITY_ERROR` → no se analiza esa dependencia → alerta inmediata en payload.json

### Output sin datos sensibles
- `payload.json`: solo `risk_level`, conteos, `summary_for_agent` (texto). Sin paths absolutos, sin valores de variables, sin credenciales.
- `impact_analysis.jsonl`: `call_path` usa paths relativos desde raíz del proyecto. Sin contenido de variables en runtime.
- `reports/*.md`: evidencia de archivo:línea, no contenido de línea si contiene datos sensibles.

### Sin autenticación de terceros
- El módulo no requiere API keys, tokens ni credenciales para operar
- Las únicas llamadas de red son del Source Fetcher a registros públicos (PyPI, npm)
- Sin telemetría, sin callbacks externos, sin beaconing

---

## Requisitos de Seguridad del Módulo

### Gestión de Secretos
- Ninguna credencial en código fuente del módulo
- `SECOPS.md` (config) no contiene secretos — solo rutas y umbrales
- `.env` ignorado en `.gitignore` del módulo

### Audit del propio módulo (RF-15)
- El módulo puede escanearse a sí mismo (`target: sec-ops`)
- Los tres motores deben pasar sin hallazgos críticos sobre el propio código del scanner
- Cualquier hallazgo sobre código propio es bloqueante para Gate 2

### Verificación de integridad de fuente descargada
| Verificación | Mecanismo | Bloqueante |
|---|---|---|
| Hash del tarball | SHA-256 vs registro oficial | Sí — no analizar si falla |
| Completitud de la descarga | Verificar que el tarball es extraíble | Sí |
| Ausencia de symlinks maliciosos | Verificar paths en tarball antes de extraer | Sí |

---

## Limitaciones de Seguridad Conocidas v0.1

| Limitación | Impacto | Resolución futura |
|---|---|---|
| JS parser en modo degradado sin Node | Análisis JS basado en texto, no AST real | v0.2: implementar parser JS puro en Python o requerir Node |
| Taint analysis inter-módulo limitado | No traza flujo a través de múltiples archivos de la misma dep en v0.1 | v0.2: análisis inter-archivo |
| Behavioral delta requiere versión anterior en caché | Si es primera vez con una dep, no hay baseline para comparar | Registrar como `NO_BASELINE` — no es error, solo sin historial |
| Análisis de código nativo (C extensions) | No analiza extensiones `.so`/`.pyd` | Fuera de scope v0.1 — documentado como limitación |
