# Recomendación: Protección de Ramas en GitHub

> Documento de referencia para la configuración de branch protection rules del repositorio.
> Aplica al repo `factory` (y a cualquier repo que use el marco PIV/OAC).
> Configuración manual en: `https://github.com/<owner>/<repo>/settings/branches`

---

## Principio de diseño

Las reglas de protección siguen la tipología de ramas del marco PIV/OAC:

| Tipo | Ramas | Protección objetivo |
|---|---|---|
| **Directive** | `agent-configs` | Solo lectura — ningún push directo, ni del owner |
| **Artifact / delivery** | `main` | Solo el owner puede mergear; no force push |
| **Artifact / integration** | `staging` | Solo el owner puede pushear; no force push |
| **Artifact / execution** | `feature/*` | Solo el owner puede pushear; no force push |

---

## Regla 1 — `agent-configs` (rama directive, solo lectura)

**Branch name pattern:** `agent-configs`

| Setting | Valor | Razón |
|---|---|---|
| Require a pull request before merging | ✅ activado | Ningún cambio directo sin revisión |
| Required approvals | 1 | Al menos una aprobación antes de merge |
| Do not allow bypassing the above settings | ✅ activado | Aplica también al owner (admin bypass desactivado) |
| Lock branch | ✅ activado | Marca explícita de solo lectura |
| Block force pushes | ✅ activado | Protege el historial de versiones del marco |

**Efecto:** Nadie puede pushear directamente a `agent-configs`, incluyendo el owner.
Cualquier cambio al marco PIV/OAC requiere una Pull Request.

**Implicación operativa para Claude Code:**
Cuando el marco necesite ser actualizado (nuevas skills, correcciones de protocolo, engram),
el flujo correcto es:
1. Crear rama temporal `directive/update-<descripcion>` desde `agent-configs`
2. Aplicar cambios en esa rama
3. Abrir PR hacia `agent-configs`
4. Revisar y aprobar antes de merge

---

## Regla 2 — `main` (rama artifact/delivery)

**Branch name pattern:** `main`

| Setting | Valor | Razón |
|---|---|---|
| Restrict who can push to matching branches | ✅ `<owner>` | Solo el owner puede mergear a producción |
| Block force pushes | ✅ activado | Protege el historial de entregas |
| Require a pull request before merging | Opcional | Recomendado si hay colaboradores |

**Efecto:** Solo el owner puede pushear/mergear a `main`.
Cualquier colaborador externo necesitaría una PR aprobada por el owner.

---

## Regla 3 — `staging` (rama artifact/integration)

**Branch name pattern:** `staging`

| Setting | Valor | Razón |
|---|---|---|
| Restrict who can push to matching branches | ✅ `<owner>` | Solo el owner integra en pre-producción |
| Block force pushes | ✅ activado | Protege la integridad del gate final |

---

## Regla 4 — `feature/*` (ramas artifact/execution)

**Branch name pattern:** `feature/*`

| Setting | Valor | Razón |
|---|---|---|
| Restrict who can push to matching branches | ✅ `<owner>` | Solo el owner (o agentes bajo su sesión) trabajan en estas ramas |
| Block force pushes | ✅ activado | Evita pérdida de trabajo de expertos en subramas |

---

## GitHub Actions — permisos mínimos recomendados

Cuando se configure CI/CD (`.github/workflows/`), los workflows deben declarar
permisos explícitos siguiendo el principio de mínimo privilegio:

```yaml
# Para workflows que solo ejecutan tests (caso más común)
permissions:
  contents: read

# Para workflows que necesitan escribir (ej. actualizar badge de cobertura)
permissions:
  contents: write
  pull-requests: write   # solo si el workflow comenta en PRs

# NUNCA usar el permiso por defecto implícito sin declararlo:
# permissions: write-all  ← evitar
```

Si las branch protection rules bloquean al runner de Actions:
`Settings → Actions → General → Workflow permissions → Read and write permissions`

---

## Compatibilidad con el punto 2 (sistema productivo)

Estas reglas **no bloquean** la evolución hacia un sistema productivo:

- El owner mantiene escritura en todas las ramas artifact
- GitHub Actions puede correr tests y deployar con `contents: read` en la mayoría de casos
- El único ajuste necesario al implementar CI/CD es declarar explícitamente
  `permissions` en el workflow según lo que necesite hacer

---

## Cómo aplicar estas reglas

1. Ir a `https://github.com/<owner>/<repo>/settings/branches`
2. Click **"Add branch protection rule"** por cada regla
3. Introducir el **Branch name pattern** exacto (los wildcards `*` funcionan para `feature/*`)
4. Activar los settings indicados
5. Click **"Create"** o **"Save changes"**

> Las reglas se aplican en orden de especificidad. Una rama que coincide con varias reglas
> hereda las restricciones más estrictas de cada una.
