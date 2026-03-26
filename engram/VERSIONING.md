# Engram — Versioning y Rollback

> Escritura exclusiva: AuditAgent al cierre de cada sesión Nivel 2.
> Garantiza integridad e historial de los átomos de memoria.

---

## Formato de Snapshot

Antes de cualquier escritura en un átomo, AuditAgent genera un snapshot atómico:

```
engram/snapshots/<atom_path>/<ISO8601-timestamp>.md
```

Ejemplo:
```
engram/snapshots/core/architecture_decisions/2026-03-17T14:32:00Z.md
```

El snapshot contiene el contenido completo del átomo **previo** a la escritura.
Los snapshots son append-only: nunca se modifican ni eliminan.

---

## SHA-256 de Integridad

Cada átomo incluye en su encabezado (primera línea) un hash SHA-256 del contenido anterior:

```markdown
<!-- sha256-prev: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 -->
<!-- atom-version: 3 -->
<!-- last-updated: 2026-03-17T14:32:00Z | updated-by: AuditAgent | session: OBJ-004 -->
```

Formato de los campos:
- `sha256-prev`: SHA-256 del contenido completo del átomo antes de este write (hex lowercase)
- `atom-version`: contador de writes al átomo (empieza en 1)
- `last-updated`: ISO 8601 UTC
- `updated-by`: identidad del agente que escribe (solo AuditAgent está autorizado)
- `session`: identificador del objetivo activo

---

## Procedimiento de Rollback

Si AuditAgent detecta escritura corrupta o contenido inválido en un átomo:

```
1. Identificar el snapshot más reciente antes del write corrupto:
   ls engram/snapshots/<atom_path>/ → último timestamp previo a la corrupción

2. Restaurar:
   cp engram/snapshots/<atom_path>/<timestamp>.md engram/<atom_path>.md

3. Registrar el rollback en engram/audit/rollback_log.md:
   | timestamp | atom | reason | session_corrupted | snapshot_restored |

4. Notificar al Master Orchestrator con:
   ENGRAM_ROLLBACK: <atom> | RAZÓN: <descripción> | SESIÓN_AFECTADA: <id>
```

---

## Reglas de Consistencia

- Un átomo que supera **500 líneas** se atomiza en sub-átomos. El átomo padre pasa a ser índice.
- Dos agentes no pueden escribir el mismo átomo en la misma sesión (AuditAgent es el único escritor — esto previene conflictos por diseño).
- Si un átomo no tiene encabezado SHA-256, se trata como `version: 0` (pre-versioning) y en el próximo write se inicializa el header con `sha256-prev` = SHA-256 del contenido actual.

---

## Directorio de Snapshots

```
engram/
├── snapshots/                    ← Creado automáticamente por AuditAgent
│   ├── core/
│   │   ├── architecture_decisions/
│   │   │   ├── 2026-03-17T10:00:00Z.md
│   │   │   └── 2026-03-17T14:32:00Z.md
│   │   └── operational_patterns/
│   └── domains/
│       └── piv-challenge/
└── ...átomos activos...
```

`engram/snapshots/` está en `.gitignore` por defecto — solo se versiona si el operador lo activa explícitamente. Los átomos activos sí se versionan con git.
