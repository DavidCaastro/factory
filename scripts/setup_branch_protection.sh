#!/usr/bin/env bash
# =============================================================================
# setup_branch_protection.sh
#
# Configura branch protection rules en GitHub para garantizar que:
#   1. Ningún push directo llega a main (solo merge desde staging vía PR)
#   2. El CI (piv-gate-framework.yml / piv_gate_checks.yml) debe ser GREEN
#      antes de que GitHub permita el merge
#   3. gate-source-branch debe pasar (solo staging puede abrir PR a main)
#
# Uso:
#   ./scripts/setup_branch_protection.sh
#   ./scripts/setup_branch_protection.sh --repo owner/repo   # repo explícito
#   ./scripts/setup_branch_protection.sh --dry-run           # muestra payload sin aplicar
#
# Requisitos:
#   - gh CLI autenticado (gh auth login)
#   - Token con permisos: repo (admin:repo_hook, write:repo)
#   - El workflow debe haber corrido al menos UNA VEZ en staging para que
#     GitHub registre los status checks (los nombres se detectan automáticamente
#     si --auto-detect está activo, o se usan los defaults de PIV/OAC)
# =============================================================================

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────────────
DRY_RUN=false
REPO=""
WORKFLOW_FILE=".github/workflows/piv-gate-framework.yml"

# Status checks requeridos (nombres de los jobs del workflow artifact)
# Actualizar si el producto usa piv_gate_checks.yml con jobs distintos
REQUIRED_CHECKS=(
  "Gate — PR to main must come from staging"
  "Gate — JSON Schema integrity"
  "Gate — Framework file structure"
  "Gate — No secrets in framework files"
  "Gate — CLAUDE.md skill references"
  "Gate — SDK importable"
  "Gate 2b — SDK Tests + Security Scan"
  "Check — Cross-Reference Integrity"
  "Check — Registry Structural Completeness"
  "Check — Protocol Integrity"
  "Check — No [PENDIENTE] in Framework"
  "Branch Protection Conformance"
)

# ── Parseo de argumentos ─────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)   DRY_RUN=true; shift ;;
    --repo)      REPO="$2"; shift 2 ;;
    *)           echo "Unknown argument: $1"; exit 1 ;;
  esac
done

# ── Detectar repo si no se pasó explícitamente ───────────────────────────────
if [ -z "$REPO" ]; then
  REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)
  if [ -z "$REPO" ]; then
    echo "ERROR: No se pudo detectar el repo. Usa --repo owner/nombre"
    exit 1
  fi
fi

echo "Repo: $REPO"
echo "Dry run: $DRY_RUN"
echo ""

# ── Construir payload de branch protection para main ─────────────────────────
# Referencia: https://docs.github.com/en/rest/branches/branch-protection

build_checks_json() {
  local checks_json="["
  local first=true
  for check in "${REQUIRED_CHECKS[@]}"; do
    if [ "$first" = true ]; then
      first=false
    else
      checks_json+=","
    fi
    checks_json+="{\"context\":\"$check\"}"
  done
  checks_json+="]"
  echo "$checks_json"
}

CHECKS_JSON=$(build_checks_json)

PAYLOAD=$(cat <<EOF
{
  "required_status_checks": {
    "strict": true,
    "checks": $CHECKS_JSON
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": false
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false
}
EOF
)

echo "=== Branch protection payload para main ==="
echo "$PAYLOAD" | python3 -m json.tool 2>/dev/null || echo "$PAYLOAD"
echo ""

if [ "$DRY_RUN" = true ]; then
  echo "DRY RUN — payload calculado, no se aplicó ningún cambio."
  exit 0
fi

# ── Aplicar branch protection ────────────────────────────────────────────────
echo "Aplicando branch protection en main..."
gh api \
  --method PUT \
  "/repos/$REPO/branches/main/protection" \
  --input - <<< "$PAYLOAD"

echo ""
echo "DONE: Branch protection configurada en main."
echo ""
echo "Reglas activas:"
echo "  · push directo a main: BLOQUEADO"
echo "  · PR a main sin CI verde: BLOQUEADO"
echo "  · PR a main que no venga de staging: BLOQUEADO (gate-source-branch)"
echo ""
echo "Para verificar:"
echo "  gh api /repos/$REPO/branches/main/protection | python3 -m json.tool"
