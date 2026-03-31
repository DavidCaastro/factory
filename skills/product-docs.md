# SKILL: Documentación de Producto — PIV/OAC v3.2
> Cargado por: StandardsAgent (checklist Gate 3) y DocumentationAgent (generación en FASE 8)
> Custodio: StandardsAgent (propone cambios al cierre, con gate SecurityAgent + confirmación humana)
> Referencia en CLAUDE.md: FASE 8 (generación) y Gate 3 (bloqueo si entregas faltantes)
>
> REGLA CRÍTICA: Gate 3 está BLOQUEADO si alguno de los entregables obligatorios está ausente
> o falla el checklist determinista del StandardsAgent. No se puede confirmar staging → main sin aprobación explícita de este skill.

---

## 1. Propósito

Este skill define:
- **Qué documentación de producto es obligatoria** antes de Gate 3
- **Cómo el DocumentationAgent la genera** en FASE 8
- **Qué verifica el StandardsAgent** (checks deterministas) antes de aprobar Gate 3

No aplica a documentación del framework (agent.md, skills/, registry/). Solo cubre documentación orientada al usuario final o equipo de operaciones del producto.

---

## 2. Entregables Obligatorios (DoD Gate 3)

Todo proyecto que alcance Gate 3 debe tener los siguientes archivos presentes y completos:

### 2.1 `README.md` — raíz del proyecto

Secciones obligatorias (en este orden, con estos encabezados exactos):

```
## Description
## Requirements
## Installation
## Environment Variables
## Run Locally
## Run Tests
```

- **Description**: qué hace el producto, su propósito principal.
- **Requirements**: versiones de runtime, sistema operativo, dependencias de sistema (no de paquete).
- **Installation**: pasos secuenciales para instalar desde cero. Sin asumir contexto previo.
- **Environment Variables**: tabla con nombre, descripción y si es obligatoria/opcional. Debe ser consistente con `.env.example`.
- **Run Locally**: comandos exactos para levantar el servicio en desarrollo.
- **Run Tests**: comando exacto para ejecutar la suite de tests (ej. `pytest --cov`).

### 2.2 `docs/deployment.md` — guía de despliegue en producción

Secciones obligatorias:

```
## Infrastructure
## Environment Variables
## Deployment Steps
## Security Checklist
## Rollback
```

- **Infrastructure**: plataforma recomendada, requisitos mínimos de CPU/RAM/disco, diagrama de red si aplica.
- **Environment Variables**: lista completa de variables requeridas en producción con descripción. Sin valores por defecto inseguros.
- **Deployment Steps**: pasos reproducibles para despliegue inicial y actualizaciones.
- **Security Checklist**: lista de verificación mínima pre-despliegue (ver §2.2.1).
- **Rollback**: procedimiento para revertir a la versión anterior.

#### 2.2.1 Security Checklist mínima para `docs/deployment.md`

```
[ ] Variables de entorno en gestor de secretos (no en código ni .env commiteado)
[ ] HTTPS habilitado con certificado válido
[ ] DEBUG desactivado en producción
[ ] CORS restringido a orígenes autorizados
[ ] Headers de seguridad configurados (HSTS, X-Content-Type-Options, etc.)
[ ] Logs sin datos sensibles (PII, tokens, contraseñas)
[ ] Firewall: solo puertos necesarios expuestos
[ ] Backups configurados si hay base de datos persistente
```

### 2.3 Referencia de API — proyectos REST

Aplica si el producto expone una API REST. Una de estas dos formas es válida:

**Opción A (preferida):** Schema OpenAPI válido generado automáticamente (ej. FastAPI `/openapi.json`).
- Verificar con: `curl <base_url>/openapi.json | python -m json.tool` → debe parsear sin error.

**Opción B:** `docs/api.md` con las siguientes secciones por cada endpoint:

```
### <MÉTODO> <ruta>
**Descripción**: qué hace el endpoint
**Auth**: requerida / no requerida / tipo
**Request body**: schema o N/A
**Query params**: nombre | tipo | obligatorio | descripción
**Response 200**: shape del body con ejemplo
**Errores**: código | condición | shape de body
```

Todos los endpoints del producto deben estar documentados. Ningún endpoint puede estar ausente en `docs/api.md` si se elige Opción B.

---

## 3. Checklist del StandardsAgent (determinista — Gate 3)

El StandardsAgent ejecuta los siguientes checks con herramientas. Ningún check puede estimarse; si una herramienta no puede ejecutarse → `BLOQUEADO_POR_HERRAMIENTA`.

### 3.1 README.md

```
[ ] Archivo existe: ls README.md → exit 0
[ ] Sección "Description":         grep -n "^## Description"         README.md
[ ] Sección "Requirements":        grep -n "^## Requirements"        README.md
[ ] Sección "Installation":        grep -n "^## Installation"        README.md
[ ] Sección "Environment Variables": grep -n "^## Environment Variables" README.md
[ ] Sección "Run Locally":         grep -n "^## Run Locally"         README.md
[ ] Sección "Run Tests":           grep -n "^## Run Tests"           README.md
[ ] Sin placeholders:              grep -rni "TODO\|FIXME\|lorem ipsum\|placeholder" README.md → vacío
```

### 3.2 Variables de entorno

```
[ ] .env.example existe: ls .env.example → exit 0
[ ] Cada variable en config/ o settings también está en README.md y .env.example:
    - Extraer variables: grep -rh "os\.environ\[" app/ | grep -oP '(?<=\[")[^"]+' | sort -u
    - Verificar presencia de cada una en README.md y .env.example
    - Discrepancia → FAIL con lista de variables faltantes
```

### 3.3 docs/deployment.md

```
[ ] Archivo existe: ls docs/deployment.md → exit 0
[ ] Sección "Security Checklist": grep -n "^## Security Checklist" docs/deployment.md
[ ] Sin placeholders:             grep -ni "TODO\|FIXME\|lorem ipsum\|placeholder" docs/deployment.md → vacío
```

### 3.4 Referencia de API (si el proyecto expone API REST)

```
[ ] OpenAPI válido (Opción A): curl <base_url>/openapi.json | python -m json.tool → exit 0
    O bien:
[ ] docs/api.md existe (Opción B): ls docs/api.md → exit 0
[ ] Sin placeholders en docs/api.md: grep -ni "TODO\|FIXME\|lorem ipsum\|placeholder" docs/api.md → vacío
```

### 3.5 Resultado del checklist

- Todos los checks pasan → StandardsAgent emite `DOCS_GATE_PASS` → Gate 3 puede proceder
- Cualquier check falla → StandardsAgent emite `DOCS_GATE_FAIL` con lista de items fallidos → Gate 3 BLOQUEADO
- `DOCS_GATE_FAIL` no puede ser ignorado ni sobreescrito por otro agente

---

## 4. DocumentationAgent — Rol y Protocolo

El DocumentationAgent es un Specialist Agent instanciado por el Domain Orchestrator en FASE 8, después de que el código ha pasado Gate 2 y está en `staging`.

### 4.1 Contexto mínimo que carga (Lazy Loading)

```
1. specs/active/functional.md          → lista de RFs para describir features en README
2. specs/active/architecture.md        → stack, runtime, estructura de módulos
3. app/ (solo lectura estructural):
     - Archivos de configuración/settings → extraer variables de entorno
     - Archivos de rutas/endpoints        → extraer contratos de API
     - requirements.txt o pyproject.toml  → extraer dependencias y versiones
4. .env.example (si existe)     → base para sección Environment Variables
```

No carga: security_vault.md, logs_veracidad/, engram/, registry/, skills/.

### 4.2 Secuencia de generación

```
1. Leer specs/active/functional.md → listar features del producto (base para Description y api.md)
2. Leer configuración de la app → extraer lista canónica de variables de entorno
3. Leer archivos de rutas → extraer endpoints, métodos, paths, schemas de request/response
4. Generar README.md con todas las secciones obligatorias (§2.1)
5. Generar docs/deployment.md con todas las secciones obligatorias (§2.2)
6. Si expone API REST → verificar si OpenAPI está disponible (Opción A)
     Si no → generar docs/api.md (Opción B) con todos los endpoints extraídos en paso 3
7. Actualizar .env.example si hay variables no documentadas (sin valores reales)
8. Reportar al Domain Orchestrator: archivos generados + lista de variables + lista de endpoints
```

### 4.3 Gate de revisión del StandardsAgent

Antes de que el DocumentationAgent haga commit de los docs:

```
Domain Orchestrator → Agent(StandardsAgent.review_docs, run_in_background=False)
StandardsAgent ejecuta checklist §3 sobre archivos generados en el worktree
Si DOCS_GATE_PASS → Domain Orchestrator autoriza commit
Si DOCS_GATE_FAIL → DocumentationAgent corrige → repite gate (máx. 3 iteraciones)
Si 3 iteraciones sin PASS → escalar al Master Orchestrator → notificar usuario
```

El DocumentationAgent nunca hace commit sin aprobación del StandardsAgent.

---

## 5. Estándares de Formato

| Atributo | Estándar |
|---|---|
| Formato | Markdown (`.md`) |
| Idioma | Idioma del proyecto (definido en `specs/active/INDEX.md`); por defecto inglés si no se especifica |
| Referencias al framework | Prohibidas en documentos de producto (`README.md`, `docs/`) — ninguna mención a PIV/OAC, agent.md, worktrees, etc. |
| Valores de ejemplo en variables | Usar valores ficticios plausibles, nunca valores reales ni `<placeholder>` sin reemplazar |
| Comandos en bloques de código | Siempre en bloques ` ```bash ``` ` con el comando exacto ejecutable |
| Tablas de variables de entorno | Formato: `NOMBRE` \| Descripción \| Obligatoria (sí/no) \| Valor de ejemplo |

---

## 6. Integración con el Protocolo PIV/OAC

| Punto de integración | Acción |
|---|---|
| FASE 8 — inicio | Domain Orchestrator instancia DocumentationAgent |
| FASE 8 — generación | DocumentationAgent genera docs; StandardsAgent revisa antes de commit |
| Gate 3 — checklist | StandardsAgent ejecuta checklist §3; resultado `DOCS_GATE_PASS` o `DOCS_GATE_FAIL` |
| Gate 3 — bloqueo | Si `DOCS_GATE_FAIL` → staging → main BLOQUEADO sin excepción |
| FASE 8 — cierre | AuditAgent incluye resultado del docs gate en el TechSpecSheet (sección VII — Infraestructura y Despliegue) |
| skills/standards.md | El checklist §3 de este skill complementa el "Checklist de Entrega Pre-Producción" de `skills/standards.md` — ambos deben pasar |
