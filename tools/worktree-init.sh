#!/usr/bin/env bash
# tools/worktree-init.sh — Automatización de worktrees PIV/OAC
# Uso: ./tools/worktree-init.sh <create|list|cleanup|cleanup-task> [args...]
# Ver skills/worktree-automation.md para documentación completa.

set -euo pipefail

WORKTREES_DIR="worktrees"

# ── helpers ──────────────────────────────────────────────────────────────────

log()  { echo "[worktree-init] $*"; }
err()  { echo "[worktree-init] ERROR: $*" >&2; exit 1; }

validate_name() {
    local name="$1"
    [[ "$name" =~ ^[a-z0-9-]{1,40}$ ]] || err "Nombre inválido: '$name'. Solo minúsculas, dígitos y guiones (máx 40 chars)."
}

# ── comandos ─────────────────────────────────────────────────────────────────

cmd_create() {
    local tarea="${1:-}" experto="${2:-}" base_branch="${3:-HEAD}"
    [[ -n "$tarea" && -n "$experto" ]] || err "Uso: create <tarea> <experto> [rama-base]"
    validate_name "$tarea"
    validate_name "$experto"

    local wt_path="$WORKTREES_DIR/$tarea/$experto"
    local branch_name="feature/$tarea/$experto"

    [[ -d "$wt_path" ]] && err "Worktree ya existe: $wt_path"

    # Verificar espacio en disco (>500 MB)
    local free_mb
    free_mb=$(df -m . | awk 'NR==2 {print $4}')
    [[ "$free_mb" -gt 500 ]] || err "Espacio insuficiente: ${free_mb}MB libre (mínimo 500MB)"

    mkdir -p "$WORKTREES_DIR/$tarea"
    git worktree add -b "$branch_name" "$wt_path" "$base_branch"
    log "Worktree creado: $wt_path (rama: $branch_name)"
}

cmd_list() {
    log "Worktrees activos:"
    git worktree list
}

cmd_cleanup() {
    local tarea="${1:-}" experto="${2:-}"
    [[ -n "$tarea" && -n "$experto" ]] || err "Uso: cleanup <tarea> <experto>"

    local wt_path="$WORKTREES_DIR/$tarea/$experto"
    [[ -d "$wt_path" ]] || err "Worktree no encontrado: $wt_path"

    git worktree remove "$wt_path" --force
    git worktree prune
    log "Worktree eliminado: $wt_path"

    # Limpiar directorio de tarea si quedó vacío
    [[ -d "$WORKTREES_DIR/$tarea" ]] && rmdir --ignore-fail-on-non-empty "$WORKTREES_DIR/$tarea"
}

cmd_cleanup_task() {
    local tarea="${1:-}"
    [[ -n "$tarea" ]] || err "Uso: cleanup-task <tarea>"

    local task_dir="$WORKTREES_DIR/$tarea"
    [[ -d "$task_dir" ]] || err "Directorio de tarea no encontrado: $task_dir"

    for wt in "$task_dir"/*/; do
        [[ -d "$wt" ]] || continue
        git worktree remove "$wt" --force
        log "Eliminado: $wt"
    done

    git worktree prune
    rmdir --ignore-fail-on-non-empty "$task_dir"
    log "Tarea limpiada: $tarea"
}

# ── dispatch ─────────────────────────────────────────────────────────────────

CMD="${1:-}"
shift || true

case "$CMD" in
    create)       cmd_create "$@" ;;
    list)         cmd_list ;;
    cleanup)      cmd_cleanup "$@" ;;
    cleanup-task) cmd_cleanup_task "$@" ;;
    *)            err "Comando desconocido: '$CMD'. Opciones: create | list | cleanup | cleanup-task" ;;
esac
