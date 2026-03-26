# Skill: Change Management y Automatización de Documentación

## Propósito

Define el proceso integrado para gestionar cambios en el framework PIV/OAC: validación previa al commit, generación automática de changelog y registro del histórico de solicitudes de cambio.

---

## 1. Validación Pre-Commit (obligatoria)

Antes de cada commit que incluya archivos `.md`, el hook `.githooks/pre-commit` ejecuta `scripts/validate_docs.py` sobre los archivos staged.

### Qué valida

| Check | Severidad si falla | Descripción |
|---|---|---|
| Vocabulario obsoleto | ALTO | VETO_CASCADA, session_learning.md (→ engram/core/), EN_PROGRESO (tarea), project_spec.md, docs/tutorials/quickstart.md (eliminado) |
| Referencias de archivo rotas | ALTO | Links `[text](path)` que no resuelven |
| Secciones §Nombre no encontradas | MEDIO | Referencias de sección que no existen en el archivo target |
| Números de sección duplicados | MEDIO | Dos secciones `## N.` con mismo número |
| Gate 2b incompleto | ALTO | Mención de Gate 2b sin los 3 agentes (Security+Audit+Standards) |

### Comportamiento

- **Issues CRÍTICO/ALTO**: commit bloqueado. Corregir antes de proceder.
- **Issues MEDIO/BAJO**: commit permitido. Issues quedan registrados en output.
- **Bypass**: `git commit --no-verify` — solo en emergencia. Registrar bypass en AuditAgent (`acciones_realizadas.txt`).

### Ejecución manual

```bash
# Validar archivos staged (mismo comportamiento que pre-commit):
python scripts/validate_docs.py --staged

# Validar todos los .md del repo:
python scripts/validate_docs.py --all

# Validar archivos específicos:
python scripts/validate_docs.py CLAUDE.md registry/audit_agent.md
```

---

## 2. Generación de Changelog (FASE 8)

El AuditAgent genera o actualiza `docs/CHANGELOG.md` al cerrar cada objetivo Nivel 2, como parte de FASE 8.

### Cuándo ejecutar

```
FASE 8 — paso adicional (post TechSpecSheet):
  AuditAgent ejecuta: python scripts/generate_changelog.py
  Resultado: docs/CHANGELOG.md actualizado con los commits del objetivo cerrado.
  Staged y commiteado como parte del commit de cierre de sesión.
```

### Formato del changelog

Basado en [Conventional Commits](https://www.conventionalcommits.org/):
- `feat(scope): descripción` → sección "Nuevas funcionalidades"
- `fix(scope): descripción` → sección "Correcciones"
- `docs(scope): descripción` → sección "Documentación"
- Organizado por mes (descendiente) y tipo de cambio.

### Ejecución manual

```bash
# Regenerar changelog completo:
python scripts/generate_changelog.py

# Preview sin escribir:
python scripts/generate_changelog.py --dry-run

# Solo desde un commit específico:
python scripts/generate_changelog.py --since=HEAD~20
```

---

## 3. Histórico de Solicitudes de Cambio

Cada solicitud de cambio significativa (Nivel 2 o cambio de framework) queda registrada en el historial a través de múltiples fuentes:

### Fuentes de historial

| Fuente | Qué registra | Quién escribe |
|---|---|---|
| `docs/CHANGELOG.md` | Cambios en el codebase (por commit convencional) | AuditAgent (FASE 8) vía script |
| `metrics/sessions.md` | Objetivos completados con métricas DORA | AuditAgent (FASE 8) |
| `engram/audit/gate_decisions.md` | Decisiones de gate y razones de rechazo | AuditAgent (en tiempo real) |
| `logs_veracidad/acciones_realizadas.txt` | Log append-only de todas las acciones | AuditAgent (en tiempo real) |
| Mensajes de commit (`git log`) | Intención de cada cambio | Framework (por convención) |

### Convención de mensajes de commit

```
type(scope): descripción en español o inglés

# Tipos válidos:
feat      — nueva funcionalidad
fix       — corrección de bug o inconsistencia
refactor  — reestructuración sin cambio funcional
docs      — solo documentación
test      — solo tests
chore     — tareas de mantenimiento (deps, hooks, scripts)
ci        — cambios en CI/CD o scripts de automatización
```

### Ejemplos de commits bien formados

```
docs(gates): alinear Gate 2b con Security+Audit+Standards en todos los archivos
fix(audit): corregir referencia a session_learning.md → .piv/active/
feat(change-management): agregar validate_docs.py y pre-commit hook
chore(bootstrap): configurar core.hooksPath para .githooks compartidos
```

---

## 4. Configuración del Entorno (bootstrap)

Para activar los hooks compartidos en un nuevo entorno:

```bash
sh scripts/bootstrap.sh
# Esto ejecuta: git config core.hooksPath .githooks
# y escribe .piv/local.env con las variables del entorno detectado.
```

Los hooks en `.githooks/` son parte del repositorio y se versionan. `.git/hooks/` es local y no se versiona.

---

## 5. Integración en FASE 8 (protocolo)

```
FASE 8 — Adición change-management:
  ├── (existente) AuditAgent genera logs de veracidad
  ├── (existente) AuditAgent registra métricas en metrics/sessions.md
  ├── (existente) AuditAgent genera TechSpecSheet
  ├── [NUEVO] AuditAgent ejecuta: python scripts/generate_changelog.py
  │     Si el script falla → registrar BLOQUEADO_POR_HERRAMIENTA en acciones_realizadas.txt
  │     No bloquear cierre de FASE 8 por fallo de changelog (INFORMACIONAL)
  └── (existente) AuditAgent actualiza engram/
```

---

## 6. Referencias Cruzadas

| Archivo | Relación |
|---|---|
| `scripts/validate_docs.py` | Validador ejecutado por el pre-commit hook |
| `scripts/generate_changelog.py` | Generador del changelog desde git log |
| `.githooks/pre-commit` | Hook que ejecuta validate_docs.py en staged files |
| `.githooks/pre-push` | Hook que ejecuta el suite de tests del SDK |
| `scripts/bootstrap.sh` | Configura `core.hooksPath` y escribe `.piv/local.env` |
| `docs/CHANGELOG.md` | Changelog generado (fuente de verdad de cambios) |
| `metrics/sessions.md` | Métricas DORA por objetivo (complementario al changelog) |
| `registry/audit_agent.md` | AuditAgent — ejecuta el changelog en FASE 8 |
