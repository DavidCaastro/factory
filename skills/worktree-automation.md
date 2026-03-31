# Skill: Automatización de Worktrees

## Propósito
Protocolo para crear, nombrar y limpiar worktrees de forma consistente en objetivos Nivel 2.
Elimina errores manuales (doble-anidamiento, paths inconsistentes, worktrees huérfanos).

## Naming Convention

```
worktrees/<tarea>/<experto>
```

Ejemplos:
```
worktrees/auth-service/security-specialist
worktrees/auth-service/backend-specialist
worktrees/database-layer/schema-specialist
```

Reglas:
- Solo minúsculas, guiones, sin espacios
- Máximo 40 caracteres por segmento
- El directorio `worktrees/` está en `.gitignore` — no se versiona

## Ciclo de Vida de un Worktree

```
Domain Orchestrator crea worktree
        ↓
Specialist Agent trabaja en él
        ↓
Specialist termina → Gate 1 (CoherenceAgent)
        ↓
CoherenceAgent aprueba → merge a feature/<tarea>
        ↓
Domain Orchestrator elimina worktree
        ↓
Feature branch continúa hacia Gate 2
```

**El Domain Orchestrator es el único responsable de crear y eliminar worktrees.**
Los Specialist Agents nunca crean ni eliminan worktrees propios.

## Script de Automatización — tools/worktree-init.sh

Ver `tools/worktree-init.sh` para la implementación shell completa.

Uso rápido:
```bash
# Crear worktree para un experto
./tools/worktree-init.sh create <tarea> <experto> [rama-base]

# Listar worktrees activos del objetivo actual
./tools/worktree-init.sh list

# Limpiar worktree tras merge aprobado
./tools/worktree-init.sh cleanup <tarea> <experto>

# Limpiar todos los worktrees de una tarea
./tools/worktree-init.sh cleanup-task <tarea>
```

## Recuperación de Worktrees Huérfanos

Si un agente falla y deja un worktree sin limpiar:

```bash
# Listar todos los worktrees del repo
git worktree list

# Eliminar worktree huérfano manualmente
git worktree remove worktrees/<tarea>/<experto> --force

# Verificar que no quedan referencias stale
git worktree prune
```

AuditAgent verifica en el cierre de cada objetivo que `git worktree list` solo muestra el worktree principal.

## Verificaciones Pre-Creación

Antes de crear un worktree, el Domain Orchestrator verifica:
1. `worktrees/<tarea>/<experto>` no existe ya
2. La rama base existe y está actualizada
3. Hay espacio en disco suficiente (> 500 MB libre)
4. El nombre cumple la naming convention

Si alguna verificación falla, el Domain Orchestrator notifica al MasterOrchestrator antes de proceder.
