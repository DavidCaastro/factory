# Tutorial — Ejecutar un Objetivo Nivel 2 con PIV/OAC

> Este tutorial lleva al lector desde cero hasta el cierre completo de un objetivo Nivel 2.
> El ejemplo concreto usado a lo largo del tutorial es:
> **"Construir un endpoint de autenticación JWT (registro + login + refresh token)"**

---

## 1. Prerequisitos

Antes de empezar necesitas:

1. **Repositorio clonado** — el repo de tu proyecto debe existir localmente y tener `main` como rama base.
2. **Claude Code abierto** — ejecuta `claude` desde la raíz del repo. La sesión debe cargarse con `agent.md` como contexto del sistema.
3. **API key configurada** — variable de entorno `ANTHROPIC_API_KEY` presente.
4. **Specs activas** — el directorio `specs/active/` debe existir con al menos `functional.md` y `architecture.md` poblados con frontmatter válido. Si no existen, el MasterOrchestrator te pedirá completar la entrevista de inicio (`execution_mode: INIT`).
5. **Dependencias de validación** — `pip install pyyaml jsonschema` (o el entorno virtual del SDK ya las incluye).

Verifica el entorno antes de empezar:

```bash
python scripts/validate_env.py
python tools/validate-specs.py
```

Si `validate-specs.py` imprime `PASS` en todos los archivos, estás listo. Si hay `FAIL`, corrige el frontmatter antes de continuar (un solo fallo bloquea la construcción del DAG).

---

## 2. Paso 1 — Definir el objetivo

Escríbele al MasterOrchestrator exactamente lo que quieres construir. Cuanto más concreto, mejor DAG.

### Qué escribir en `specs/active/functional.md`

Antes de enviar el mensaje, asegúrate de que `functional.md` tenga los RFs que respaldan el objetivo. Por ejemplo:

```markdown
---
spec_name: functional
version: 1.0.0
status: ACTIVE
project_name: Auth Service
rf_count: 4
rfs_completed: 0
coverage_target: 100
---

### RF-AUTH-01 — Registro de usuario
| Atributo | Valor |
|---|---|
| Descripción | El sistema acepta email + password, crea cuenta y retorna JWT de acceso. |
| Criterio de aceptación | POST /auth/register retorna 201 con `{access_token, refresh_token}` |
| Estado | PENDIENTE |
| Evidencia | — |

### RF-AUTH-02 — Login
...

### RF-AUTH-03 — Refresh token
...

### RF-AUTH-04 — Validación de token en rutas protegidas
...
```

### Mensaje inicial al agente

```
Objetivo: Implementar autenticación JWT completa para el Auth Service.
RFs a cubrir: RF-AUTH-01, RF-AUTH-02, RF-AUTH-03, RF-AUTH-04.
Stack: FastAPI + PostgreSQL + python-jose.
```

El MasterOrchestrator ejecutará primero la clasificación de nivel. Como el objetivo toca autenticación, datos de usuario y nuevas dependencias, clasificará automáticamente como **Nivel 2** (los criterios de la matriz de riesgo aplican).

---

## 3. Paso 2 — MasterOrchestrator construye el DAG

Después de tu mensaje, el MasterOrchestrator:

1. Ejecuta `python tools/validate-specs.py` — si hay fallos, te los reporta y se detiene.
2. Lee `specs/active/functional.md` y `architecture.md`.
3. Descompone el objetivo en tareas y determina cuáles pueden ejecutarse en paralelo.

### Cómo leer el DAG

El MasterOrchestrator te presentará una tabla como esta:

```
DAG — Auth Service / JWT Auth

| Tarea          | Dominio  | Tipo       | Expertos | Depende de   |
|----------------|----------|------------|----------|--------------|
| db-schema      | Backend  | SECUENCIAL | 1        | —            |
| auth-core      | Backend  | PARALELA   | 2        | db-schema    |
| route-guards   | Backend  | PARALELA   | 1        | auth-core    |
| tests-auth     | QA       | PARALELA   | 2        | auth-core    |

Entorno de Control:
  SecurityAgent   → SÍ (siempre)
  AuditAgent      → SÍ (siempre)
  CoherenceAgent  → SÍ (siempre)
  StandardsAgent  → SÍ (siempre)
  ComplianceAgent → SÍ (compliance_scope: FULL)

Resumen de compliance:
  GDPR aplica (datos de usuario con email).
  OWASP Top 10 A07:2021 (Auth failures) requiere revisión explícita.
```

Nota: `auth-core` tiene 2 expertos porque toca autenticación (criterio de riesgo: 2 o más enfoques técnicos válidos + riesgo alto de error).

---

## 4. Paso 3 — Confirmar el DAG

Antes de decir "sí", verifica:

- **Dependencias correctas** — ¿tiene sentido que `auth-core` dependa de `db-schema`? Sí, porque necesita la tabla `users` creada primero.
- **Número de expertos** — ¿es razonable 2 expertos en `auth-core`? Para JWT con refresh tokens sí; hay decisiones de diseño que se benefician de enfoques alternativos.
- **Compliance** — ¿el resumen menciona las regulaciones relevantes para tu proyecto?
- **Entorno de control** — todos los superagentes deben aparecer como SÍ (excepto ComplianceAgent si tu `compliance_scope` es `NONE`).

Si algo no cuadra, díselo al MasterOrchestrator antes de confirmar. Ajustará el DAG y te lo volverá a presentar. Solo cuando estés de acuerdo, responde:

```
Confirmo el DAG. Procede.
```

---

## 5. Paso 4 — Entorno de control se activa

Tras tu confirmación, el MasterOrchestrator crea la rama `staging` (si no existe) y lanza los superagentes **en paralelo real**:

```
[FASE 2] Lanzando entorno de control...
  ► SecurityAgent   (opus)   — run_in_background=True
  ► AuditAgent      (sonnet) — run_in_background=True
  ► StandardsAgent  (sonnet) — run_in_background=True
  ► CoherenceAgent  (sonnet) — run_in_background=True
  ► ComplianceAgent (sonnet) — run_in_background=True

[FASE 2] Esperando notificaciones de inicio...
  ✓ SecurityAgent   — LISTO
  ✓ AuditAgent      — LISTO
  ✓ StandardsAgent  — LISTO
  ✓ CoherenceAgent  — LISTO
  ✓ ComplianceAgent — LISTO

[FASE 2] Entorno de control activo. Continuando a FASE 3.
```

### Qué hace cada agente del entorno de control

| Agente | Rol principal | Cuándo preocuparse |
|---|---|---|
| **SecurityAgent** | Veto sobre planes y código. Evalúa OWASP, CVEs, credenciales, CORS. | Si emite REJECTED en el gate pre-código dos veces seguidas — hay un problema de diseño, no de implementación. |
| **AuditAgent** | Trazabilidad RF ↔ código. Verifica que cada RF tiene evidencia de cumplimiento. | Si dice que un RF no tiene evidencia — el experto no dejó el archivo:línea correspondiente. |
| **CoherenceAgent** | Consistencia entre expertos paralelos. Detecta conflictos entre subramas. | Si eleva un CONFLICTO CRÍTICO — requiere tu intervención directa. |
| **StandardsAgent** | Calidad: cobertura de tests, docstrings, complejidad ciclomática, lint. | Si está BLOQUEADO_POR_HERRAMIENTA (pytest-cov no disponible) — instala la herramienta antes de continuar. |
| **ComplianceAgent** | Marco legal: GDPR, OWASP-API-2023, licencias de dependencias. | Si emite BLOQUEADO — necesitas un Documento de Mitigación reconocido por ti. |

---

## 6. Paso 5 — Gate pre-código bloqueante

Antes de que los expertos escriban una sola línea, el Domain Orchestrator de Backend presenta su **plan detallado** a SecurityAgent, AuditAgent y CoherenceAgent simultáneamente.

### Cómo leer el veredicto

Un veredicto típico de gate pre-código aprobado:

```
[GATE PRE-CÓDIGO] Tarea: db-schema

SecurityAgent:
  APROBADO
  Sin riesgos identificados en el plan de schema.
  Nota: Confirmar que passwords se almacenan con bcrypt (hash), no plaintext.

AuditAgent:
  APROBADO
  RF-AUTH-01 respaldado por la creación de tabla users con campo email único.
  RF-AUTH-03 respaldado por tabla refresh_tokens.

CoherenceAgent:
  APROBADO (1 experto — monitor_diff no requerido)

Resultado: TODOS APRUEBAN — autorizado para crear worktrees y lanzar expertos.
```

### Qué hacer si hay REJECTED

Si SecurityAgent rechaza el plan:

```
SecurityAgent:
  REJECTED
  Razón: El plan almacena el JWT secret como variable de módulo Python (hardcoded).
  Solución requerida: Cargar desde variable de entorno; nunca desde código fuente.
  Archivo de referencia: skills/backend-security.md §Gestión de secretos
```

El Domain Orchestrator revisará el plan incorporando la corrección y enviará de nuevo al gate. Si es rechazado por segunda vez con el mismo problema, escala al MasterOrchestrator, que te lo notifica. En ese punto puedes intervenir con orientación adicional.

---

## 7. Paso 6 — Expertos trabajando en paralelo

Una vez aprobado el gate pre-código, el Domain Orchestrator crea los worktrees y lanza los expertos:

```
[FASE 5] Creando worktrees para tarea: auth-core
  git worktree add ./worktrees/auth-core/experto-1 -b feature/auth-core/experto-1
  git worktree add ./worktrees/auth-core/experto-2 -b feature/auth-core/experto-2

[FASE 5] Lanzando expertos en paralelo:
  ► SpecialistAgent experto-1 (auth-core) — run_in_background=True
  ► SpecialistAgent experto-2 (auth-core) — run_in_background=True
  ► CoherenceAgent.monitor_diff(experto-1, experto-2) — run_in_background=True
```

### Qué monitorear

Durante la ejecución paralela, CoherenceAgent puede notificarte:

```
[CoherenceAgent] CONFLICTO MENOR detectado
  Archivos en común: src/auth/tokens.py
  Experto-1: implementa verify_token() con python-jose
  Experto-2: implementa verify_token() con PyJWT
  Compatibles semánticamente — propuesta de reconciliación enviada al DO.
  Acción requerida del usuario: ninguna.
```

Un CONFLICTO MENOR se resuelve solo. Si ves CONFLICTO MAYOR o CRÍTICO, el sistema te notifica y espera tu decisión.

Los expertos también pueden quedar en estado `INVESTIGACIÓN_REQUERIDA` si la spec no tiene suficiente información para completar una tarea. En ese caso el DO te pregunta directamente.

---

## 8. Paso 7 — Gates 1 y 2

### Gate 1 — CoherenceAgent (merge de subramas a rama de tarea)

Cuando ambos expertos de `auth-core` terminan, CoherenceAgent emite:

```
COHERENCE MERGE AUTHORIZATION
  Tarea: feature/auth-core
  Subramas evaluadas: [feature/auth-core/experto-1, feature/auth-core/experto-2]
  Conflictos detectados: 1 | Resueltos: 1 | Pendientes: 0
  Estado final: COHERENTE
  AUTORIZADO para merge a feature/auth-core: SÍ
```

El Domain Orchestrator ejecuta los merges. Si hay un conflicto técnico de git (marcadores `<<<<<<<`), CoherenceAgent lo resuelve si es técnico puro (imports duplicados, etc.) o lo escala si es semántico.

### Gate 2 — Security + Audit + Standards (merge de rama de tarea a staging)

Después del Gate 1, los tres agentes revisan la implementación real:

```
[GATE 2] Tarea: auth-core

SecurityAgent:
  APROBADO
  • Sin credenciales hardcodeadas
  • JWT secret cargado desde os.environ["JWT_SECRET"]
  • bcrypt para hash de passwords (factor: 12)
  • pip-audit: 0 CVEs críticos en python-jose 3.3.0

AuditAgent:
  APROBADO
  • RF-AUTH-01: src/auth/register.py:47 — POST /auth/register
  • RF-AUTH-02: src/auth/login.py:31 — POST /auth/login
  • RF-AUTH-03: src/auth/tokens.py:89 — POST /auth/refresh
  • Trazabilidad completa

StandardsAgent:
  APROBADO
  • Cobertura: 94% (pytest-cov — medida, no estimada)
  • Sin código muerto
  • Complejidad ciclomática máx: 6
  • Docstrings presentes en funciones públicas

Resultado: TODOS APRUEBAN
  → git merge feature/auth-core → staging
  → git worktree remove ./worktrees/auth-core
```

Si alguno rechaza, el DO recibe la lista de dimensiones fallidas con archivos:línea y reanuda desde el plan (no desde cero). Un segundo rechazo del mismo código escala al MasterOrchestrator.

---

## 9. Paso 8 — Gate 3 — Tu confirmación final

Cuando **todas** las tareas del DAG están en `staging`, el MasterOrchestrator lanza una revisión integral de staging (Security + Audit en paralelo, más ComplianceAgent y StandardsAgent para documentación) y te presenta el estado completo:

```
[GATE 3] Estado del objetivo: Auth Service / JWT Auth

DAG:
  ✓ db-schema       COMPLETADA
  ✓ auth-core       COMPLETADA
  ✓ route-guards    COMPLETADA
  ✓ tests-auth      COMPLETADA

Revisión integral de staging:
  ✓ SecurityAgent   APROBADO (revisión completa de staging)
  ✓ AuditAgent      APROBADO (todos los RFs cubiertos)

Compliance (ComplianceAgent):
  ✓ GDPR: consentimiento no requerido (no se recolectan datos más allá de email)
  ✓ OWASP-API-2023: A07 revisado explícitamente
  ✓ Licencias: python-jose (MIT), bcrypt (Apache 2.0) — compatibles
  APROBADO_CON_DISCLAIMER: requiere revisión humana antes de despliegue

Documentación:
  ✓ README.md actualizado
  ✓ docs/deployment.md presente
  ✓ OpenAPI actualizado (POST /auth/register, /auth/login, /auth/refresh)

Rama: staging lista para merge a main.
¿Confirmas el merge? (escribe "confirmo" o "merge auth service" para proceder)
```

### Qué revisar antes de confirmar

Antes de escribir "confirmo":

1. **Lee el diff de staging** — `git diff main..staging` — ¿los cambios son los que esperabas?
2. **Revisa la cobertura reportada** — ¿el porcentaje es suficiente para tu `coverage_target`?
3. **Lee el disclaimer de Compliance** — ¿entiendes lo que dice?
4. **Verifica la documentación** — ¿el README describe correctamente los nuevos endpoints?

Si algo no te satisface, díselo al MasterOrchestrator antes de confirmar. La rama `staging` permanece intacta hasta que des luz verde.

---

## 10. Paso 9 — Cierre

Tras tu confirmación, el MasterOrchestrator ejecuta `git merge staging → main` y desencadena el cierre en paralelo:

### logs_veracidad

El AuditAgent genera tres archivos en `logs_veracidad/`:

- `acciones_realizadas.txt` — cada acción atómica del objetivo con timestamp
- `agentes_instanciados.txt` — todos los agentes lanzados, cuándo, con qué argumentos
- `conformidad_protocolo.txt` — verificación de que todas las fases se ejecutaron según el protocolo

### engram

Cada agente actualiza su átomo correspondiente:

- `engram/security/patterns.md` — SecurityAgent registra los patrones de seguridad aplicados
- `engram/audit/gate_decisions.md` — AuditAgent registra los veredictos de gate con rationale
- `engram/coherence/conflict_patterns.md` — CoherenceAgent registra los conflictos y cómo se resolvieron
- `engram/quality/code_patterns.md` — StandardsAgent registra patrones de calidad reutilizables

### metrics

El AuditAgent actualiza `metrics/sessions.md` con los valores **medidos** (nunca estimados):

```
## sesion-2026-03-17-auth-service
objetivo: Auth Service / JWT Auth
first_pass_rate: 0.75   # Gate 2: 3 de 4 tareas aprobaron al primer intento
gate_rejections: 1      # auth-core rechazado por SecurityAgent (credenciales hardcodeadas)
veto_saturacion: 0
cobertura: 94
tareas: 4
expertos: 6
duracion_min: 47
```

### TechSpecSheet

El AuditAgent genera `compliance/auth-service/delivery/TECH_SPEC_SHEET.md` siguiendo ISO/IEC/IEEE 29148:2018 + ISO/IEC 25010:2023. Este documento es el entregable técnico formal del objetivo.

---

## 11. Troubleshooting — Los 5 problemas más comunes

### Problema 1: `validate-specs.py` retorna FAIL antes de iniciar

**Síntoma:**
```
[FAIL]   specs/active/functional.md
  Campo 'rf_count': 0 is less than the minimum of 1
```

**Solución:** El campo `rf_count` en el frontmatter de `functional.md` debe ser `>= 1`. Significa que declaraste 0 RFs. Agrega los RFs al archivo y actualiza el contador. El MasterOrchestrator no puede construir el DAG sin al menos 1 RF documentado.

---

### Problema 2: Gate pre-código rechazado dos veces seguidas

**Síntoma:** El MasterOrchestrator te escala con el mensaje:
```
ALERTA: Gate pre-código rechazado por SecurityAgent por segunda vez en la misma tarea.
Razón persistente: almacenamiento de tokens en localStorage (XSS-vulnerable).
Requiere orientación del usuario.
```

**Solución:** El plan del Domain Orchestrator tiene un defecto de diseño que no se resuelve con ajustes menores. Debes dar una indicación explícita de la solución técnica:
```
Usar httpOnly cookies para el access token. El refresh token va en el body, no en localStorage.
```

---

### Problema 3: CONFLICTO CRÍTICO entre expertos

**Síntoma:**
```
[CoherenceAgent] CONFLICTO CRÍTICO
  Expertos: auth-core/experto-1, auth-core/experto-2
  Archivo: src/auth/models.py
  RF comprometido: RF-AUTH-04
  Experto-1: tabla users sin campo is_active (asume todos activos)
  Experto-2: tabla users con campo is_active + filtro en login
  Impacto: comportamiento incompatible en autenticación de usuarios suspendidos
```

**Solución:** El MasterOrchestrator te presenta las opciones A y B. Elige explícitamente cuál es la correcta para tu sistema. En este caso, la opción correcta es casi siempre la que incluye `is_active` — pero eres tú quien decide.

---

### Problema 4: StandardsAgent en BLOQUEADO_POR_HERRAMIENTA

**Síntoma:**
```
StandardsAgent: BLOQUEADO_POR_HERRAMIENTA
  pytest-cov no disponible en el entorno actual.
  No es posible medir cobertura real. No se emitirá veredicto estimado.
```

**Solución:**
```bash
pip install pytest-cov
```
Luego notifica al Domain Orchestrator para que el StandardsAgent reintente el Gate 2. No intentes avanzar sin cobertura medida — un veredicto estimado no es aceptable en el protocolo.

---

### Problema 5: ComplianceAgent en BLOQUEADO en Gate 3

**Síntoma:**
```
ComplianceAgent: BLOQUEADO
  Regulación aplicable: GDPR
  Problema: No existe documentación de privacidad para datos de usuario (email).
  Acción requerida: Documento de Mitigación reconocido por el usuario.
```

**Solución:** El ComplianceAgent generará un borrador de `PRIVACY_NOTICE.md` en `compliance/auth-service/delivery/`. Léelo, ajústalo si es necesario, y responde:
```
Reconozco el documento de privacidad. Procede con el Gate 3.
```
El DISCLAIMER final del ComplianceAgent siempre incluirá "Requiere revisión humana antes de despliegue" — esto es por diseño y no significa que algo esté mal.

---

*Para el protocolo completo, ver `agent.md` y los flujos en `docs/flows/`.*
*Para la clasificación de nivel, ver `docs/flows/00_clasificacion_nivel.md`.*
