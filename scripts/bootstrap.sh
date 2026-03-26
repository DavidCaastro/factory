#!/usr/bin/env sh
# =============================================================================
# PIV/OAC Bootstrap — Environment Auto-Detection & Validation
# Portable: bash / sh / zsh · Linux · macOS · Windows (Git Bash / WSL)
#
# Uso:
#   sh scripts/bootstrap.sh           # detecta y escribe .piv/local.env
#   sh scripts/bootstrap.sh --check   # solo valida, no escribe
#
# Salida:
#   0 — entorno válido, .piv/local.env escrito
#   1 — una o más herramientas críticas faltan
# =============================================================================

CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

ERRORS=0
WARNINGS=0

ok()   { printf "  [OK] %-22s %s\n" "$1" "$2"; }
warn() { printf "  [!!] %-22s %s\n" "$1" "$2"; WARNINGS=$((WARNINGS+1)); }
fail() { printf "  [XX] %-22s %s\n" "$1" "$2"; ERRORS=$((ERRORS+1)); }

# ─── detección sin set -e ─────────────────────────────────────────────────────

# REPO_ROOT
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
  printf "[XX] No es un repositorio git o git no está en PATH. Abortando.\n"
  exit 1
fi

# OS_TYPE
_uname=$(uname -s 2>/dev/null)
case "$_uname" in
  Linux*)              OS_TYPE=linux ;;
  Darwin*)             OS_TYPE=darwin ;;
  MINGW*|MSYS*|CYGWIN*) OS_TYPE=windows ;;
  *)                   OS_TYPE=unknown ;;
esac

# GIT_CMD
GIT_CMD=$(command -v git 2>/dev/null) || GIT_CMD=""

# PYTHON_CMD — python3 primero, luego python
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
  _v=$(python3 --version 2>/dev/null) && PYTHON_CMD=python3
fi
if [ -z "$PYTHON_CMD" ] && command -v python >/dev/null 2>&1; then
  _v=$(python --version 2>/dev/null) && PYTHON_CMD=python
fi

# RUFF_CMD
RUFF_CMD=""
if command -v ruff >/dev/null 2>&1; then
  RUFF_CMD=ruff
elif [ -n "$PYTHON_CMD" ]; then
  $PYTHON_CMD -m ruff --version >/dev/null 2>&1 && RUFF_CMD="$PYTHON_CMD -m ruff"
fi

# PYTEST_CMD
PYTEST_CMD=""
if [ -n "$PYTHON_CMD" ]; then
  $PYTHON_CMD -m pytest --version >/dev/null 2>&1 && PYTEST_CMD="$PYTHON_CMD -m pytest"
fi

# PIP_AUDIT_CMD (opcional)
PIP_AUDIT_CMD=""
if command -v pip-audit >/dev/null 2>&1; then
  PIP_AUDIT_CMD=pip-audit
elif [ -n "$PYTHON_CMD" ]; then
  $PYTHON_CMD -m pip_audit --version >/dev/null 2>&1 && PIP_AUDIT_CMD="$PYTHON_CMD -m pip_audit"
fi

# ─── validación ───────────────────────────────────────────────────────────────

printf "\n===========================================================\n"
printf "  PIV/OAC Bootstrap -- Environment Validation\n"
printf "  Repo: %s\n" "$REPO_ROOT"
printf "  OS:   %s\n" "$OS_TYPE"
printf "===========================================================\n"
printf "\n--- Herramientas requeridas --------------------------------\n"

if [ -n "$GIT_CMD" ]; then
  ok "git" "$($GIT_CMD --version 2>/dev/null | head -1)"
else
  fail "git" "no encontrado en PATH"
fi

if [ -n "$PYTHON_CMD" ]; then
  ok "python" "$($PYTHON_CMD --version 2>/dev/null) -> $PYTHON_CMD"
else
  fail "python" "ni python3 ni python encontrados en PATH"
fi

if [ -n "$RUFF_CMD" ]; then
  ok "ruff" "$($RUFF_CMD --version 2>/dev/null | head -1) -> $RUFF_CMD"
else
  fail "ruff" "no disponible -- pip install ruff"
fi

if [ -n "$PYTEST_CMD" ]; then
  ok "pytest" "$($PYTEST_CMD --version 2>/dev/null | head -1) -> $PYTEST_CMD"
else
  fail "pytest" "no disponible -- pip install pytest pytest-cov"
fi

printf "\n--- Herramientas condicionales (compliance MINIMAL/FULL) ---\n"

if [ -n "$PIP_AUDIT_CMD" ]; then
  ok "pip-audit" "$PIP_AUDIT_CMD"
else
  warn "pip-audit" "no disponible -- gates emitiran BLOQUEADO_POR_HERRAMIENTA"
fi

printf "\n===========================================================\n"

if [ "$ERRORS" -gt 0 ]; then
  printf "  RESULTADO: BLOQUEADO -- %d herramienta(s) critica(s) faltante(s)\n" "$ERRORS"
  printf "  Corrige [XX] antes de iniciar un objetivo Nivel 2.\n"
  printf "===========================================================\n\n"
  exit 1
fi

if [ "$WARNINGS" -gt 0 ]; then
  printf "  RESULTADO: VALIDO con %d advertencia(s)\n" "$WARNINGS"
else
  printf "  RESULTADO: ENTORNO COMPLETAMENTE VALIDO\n"
fi
printf "===========================================================\n\n"

[ "$CHECK_ONLY" = "1" ] && exit 0

# ─── escritura de .piv/local.env ──────────────────────────────────────────────

mkdir -p "$REPO_ROOT/.piv"

cat > "$REPO_ROOT/.piv/local.env" <<EOF
# PIV/OAC Local Environment -- auto-generado por scripts/bootstrap.sh
# NO editar manualmente. Ejecutar: sh scripts/bootstrap.sh para regenerar.
# Este archivo esta en .gitignore -- nunca versionar.
# Generado: $(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date)

REPO_ROOT=$REPO_ROOT
OS_TYPE=$OS_TYPE
PYTHON_CMD=$PYTHON_CMD
GIT_CMD=${GIT_CMD:-git}
RUFF_CMD=$RUFF_CMD
PYTEST_CMD=$PYTEST_CMD
PIP_AUDIT_CMD=${PIP_AUDIT_CMD:-}
EOF

printf "  .piv/local.env escrito correctamente.\n\n"

# ─── hooks compartidos (.githooks/) ───────────────────────────────────────────

if [ -d "$REPO_ROOT/.githooks" ]; then
  git -C "$REPO_ROOT" config core.hooksPath .githooks
  chmod +x "$REPO_ROOT/.githooks/"* 2>/dev/null || true
  printf "  Hooks compartidos configurados: core.hooksPath = .githooks\n\n"
else
  printf "  [!!] .githooks/ no encontrado — hooks compartidos no configurados.\n\n"
fi

exit 0
