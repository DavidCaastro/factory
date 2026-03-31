# Skill: Product Decoupling — Extracción de Producto a Repo Independiente

## Propósito

Define el protocolo para extraer un producto terminado (ramas `main`, `staging`, `feature/*`, `fix/*`) desde el repo astillero (`lab`) hacia un repositorio independiente, preservando la historia git completa.

El repo astillero (`lab`) mantiene exclusivamente la rama directiva (`agent-configs`) y queda limpio para el siguiente producto.

---

## Modelo "Astillero"

```
lab/ (repo astillero — permanente)
├── agent-configs  ← framework PIV/OAC, skills, registry, engram
└── <producto>     ← ramas de construcción (temporales)
    ├── main
    ├── staging
    └── feature/* / fix/*

           ↓ DECISIÓN HUMANA: "desacoplar"

lab/                           <producto>/ (repo independiente)
├── agent-configs  ← intacto   ├── main      ← historia completa
└── (limpio)                   ├── staging
                                ├── feature/*
                                └── fix/*
```

---

## Pre-requisitos

| Requisito | Verificación |
|---|---|
| Gate 3 del producto aprobado | `main` contiene el producto listo para producción |
| Repo destino creado en GitHub | Vacío, sin README ni .gitignore |
| URL del repo destino disponible | `https://github.com/<org>/<producto>.git` |
| Confirmación humana explícita | Turno actual del usuario |

---

## Protocolo de Ejecución

```
PASO 1 — Registrar remote destino
  git remote add <producto> <url>
  git ls-remote <producto>               ← verificar repo vacío y accesible

PASO 2 — Push de ramas de producto (historia completa)
  git push <producto> main staging
  git push <producto> --tags             ← transferir tags si los hay
  git push <producto> feature/<T-*>...   ← todas las ramas de tareas
  git push <producto> fix/<*>...         ← ramas de correcciones

PASO 3 — Verificación de integridad
  SHA local main    == SHA <producto>/main    → PASS
  SHA local staging == SHA <producto>/staging → PASS
  Conteo de commits: git log --oneline main | wc -l  (igual en ambos repos)

PASO 4 — [GATE: CONFIRMACIÓN HUMANA EXPLÍCITA]
  Presentar al usuario:
    - SHAs verificados
    - Lista de ramas transferidas
    - Lista de ramas a eliminar del astillero
  Sin confirmación explícita: DETENER. No continuar.

PASO 5 — Limpieza del astillero (solo tras Gate 4 aprobado)
  # Eliminar staging y ramas feature/fix — NUNCA main
  git worktree remove --force worktrees/<*>         ← si hay worktrees activos
  git push origin --delete staging feature/<*> fix/<*>
  git branch -D staging feature/<*> fix/<*>
  git remote remove <producto>                       ← limpiar remote temporal

PASO 5b — Resetear main a orphan limpio (punto de partida del próximo producto)
  git checkout --orphan main-fresh
  git rm -rf .
  echo "# Astillero — próximo producto\n\nRama lista para el siguiente objetivo PIV/OAC." > README.md
  git add README.md
  git commit -m "chore: astillero limpio — listo para próximo producto"
  git branch -D main
  git branch -m main-fresh main
  git push origin main --force-with-lease
  git checkout agent-configs

  ⚠️  REGLA: main NUNCA se elimina del astillero. Es la rama default de
  GitHub y el punto de entrada de todo producto nuevo. Solo se resetea
  a orphan limpio. No hacer: git push origin --delete main.

PASO 5c — Activar branch protection en el repo destino
  Una vez transferido el producto a su repo independiente, activar rulesets:
    GitHub → <repo-producto> → Settings → Branches → Add branch ruleset
      Target: main
      ✅ Require a pull request before merging
      ✅ Require status checks to pass → nombres exactos de los jobs CI del producto
      ✅ Block force pushes
  ⚠️  NO activar en el astillero (lab) — impide el flujo ágil de desarrollo.
  ⚠️  Solo activar POST-decoupling en el repo de producción independiente.

PASO 6 — Registro en engram
  AuditAgent escribe en engram/core/operational_patterns.md:
    - Producto desacoplado: <nombre>
    - Repo destino: <url>
    - Fecha: <ISO 8601>
    - Commits transferidos: <n>
    - main reseteada a orphan: SÍ

PASO 7 — Estado final del astillero
  Ramas en lab/: agent-configs (framework) + main (orphan con README)
  main sigue siendo la rama default de GitHub
  Próximo producto: entregar objetivo → PIV/OAC construye sobre main existente
```

---

## Verificación de Integridad (Paso 3)

```bash
# SHA de main en astillero
LOCAL_SHA=$(git rev-parse main)

# SHA de main en repo destino
REMOTE_SHA=$(git ls-remote <producto> refs/heads/main | cut -f1)

# Comparar
[ "$LOCAL_SHA" = "$REMOTE_SHA" ] && echo "PASS" || echo "FAIL — integridad comprometida"
```

Si cualquier SHA no coincide → **ABORTAR**. Investigar antes de continuar.

---

## Lo que se preserva en el producto desacoplado

| Artefacto | ¿Se preserva? | Nota |
|---|---|---|
| Historia git completa | Sí | Todos los SHAs, autores, timestamps |
| Mensajes de commit | Sí | Conventional commits incluidos |
| Tags de versión | Sí | `git push --tags` |
| Ramas de feature/fix | Sí | Trazabilidad completa del trabajo |
| CI/CD workflows | Sí | `.github/workflows/` viaja con main |
| Specs del producto | Sí | `specs/active/` viaja con main |

## Lo que NO viaja al producto

| Artefacto | Queda en | Razón |
|---|---|---|
| `agent-configs` | lab/astillero | Framework — no es código de producto |
| `engram/`, `skills/`, `registry/` | lab/astillero | Conocimiento del orquestador |
| `metrics/sessions.md` | lab/astillero | Historial del astillero, no del producto |
| `sdk/` | lab/astillero | SDK del framework, no del producto |

---

## Iniciar un nuevo producto tras el desacoplamiento

`main` ya existe y está vacía — no hay que crearla.

```
1. git checkout agent-configs          # confirmar rama directiva activa
2. Definir specs/active/ del nuevo producto
3. Entregar objetivo al sistema → PIV/OAC construye sobre main existente
```

Estado esperado del astillero entre productos:
- `agent-configs` → framework completo (rama directiva)
- `main` → orphan con README placeholder (rama default de GitHub, vacía)

---

## Referencias Cruzadas

| Archivo | Relación |
|---|---|
| `CLAUDE.md` | Regla Separación Directiva/Artefacto |
| `registry/orchestrator.md` | Master Orchestrator — Gate 3 pre-desacoplamiento |
| `engram/core/operational_patterns.md` | Registro de productos desacoplados |
| `metrics/sessions.md` | Historial de objetivos — permanece en astillero |
