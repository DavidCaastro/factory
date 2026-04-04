---
name: feedback_decoupling_main
description: En el protocolo de desacoplamiento, main del astillero se resetea a orphan vacío — nunca se elimina
type: feedback
---

En el proceso de desacoplamiento (skills/decoupling.md), la rama `main` del astillero (lab/) NUNCA se elimina.

**Why:** `main` es la rama default de GitHub y el punto de entrada de todo producto nuevo. Eliminarla rompe el flujo del astillero y requiere crear la rama de nuevo manualmente.

**How to apply:** Al ejecutar el desacoplamiento:
- SÍ eliminar: `staging`, `feature/*`, `fix/*` (locales y en origin)
- SÍ resetear: `main` → orphan limpio con un README placeholder (`git checkout --orphan` + `git rm -rf .` + commit mínimo + `force-with-lease`)
- NUNCA: `git push origin --delete main`

Estado final correcto del astillero: `agent-configs` (framework) + `main` (orphan vacío, default).
