# skill: rust-tauri-ci

> Cargado por: StandardsAgent, DomainOrchestrator (dominio Rust/Tauri)
> Activación: cuando el proyecto usa Tauri 2.x + Rust + GitHub Actions CI

---

## 1. Propósito

Patrones y recetas para configurar CI/CD correcto en proyectos Tauri 2.x con Rust.
Basado en errores reales resueltos en Axonum (staging CI, 2026-03).

---

## 2. Dependencias del runner que NO vienen pre-instaladas

Ubuntu 24.04 (ubuntu-latest desde 2024) **no incluye** por defecto:

| Herramienta | Por qué se necesita | Fix |
|-------------|--------------------|----|
| `imagemagick` | Conversión PNG→RGBA antes de `cargo build` | `apt-get install -y imagemagick` |

Siempre instalar explícitamente en el step `Install system dependencies`:

```yaml
- name: Install system dependencies (Linux)
  run: |
    sudo apt-get update
    sudo apt-get install -y \
      libwebkit2gtk-4.1-dev \
      libgtk-3-dev \
      libayatana-appindicator3-dev \
      librsvg2-dev \
      patchelf \
      imagemagick      # ← OBLIGATORIO para conversión de iconos
```

---

## 3. Iconos PNG — requisito RGBA de Tauri

`tauri::generate_context!()` valida los iconos en **tiempo de compilación**.
Si algún PNG no es RGBA (color-type 6), el proc macro pánica y falla `cargo build`, `cargo clippy` y `cargo test`.

**Diagnóstico:** `icon <path>.png is not RGBA`

**Fix — step obligatorio antes de cualquier cargo command:**

```yaml
- name: Convert icons to RGBA
  run: |
    for icon in src-tauri/icons/*.png; do
      convert "$icon" -define png:color-type=6 "$icon"
    done
```

Colocar este step **después** de instalar system dependencies (imagemagick debe estar disponible).

---

## 4. Orden correcto del job `rust-checks`

```yaml
1. Checkout
2. Install Rust toolchain (stable + rustfmt + clippy)
3. Cache Cargo
4. Install system dependencies (incluye imagemagick)
5. Convert icons to RGBA          ← antes de cualquier cargo
6. cargo fmt --check
7. cargo clippy -- -D warnings
8. cargo test
```

---

## 5. clippy con `#![deny(clippy::all)]`

Con `#![deny(clippy::all)]` en `src/lib.rs`, **toda advertencia de clippy es un error de compilación**.

Lints frecuentes que rompen CI:

| Lint | Causa | Fix |
|------|-------|-----|
| `clippy::needless_return` | `return Ok(())` al final de un bloque `#[cfg(unix)]` | Quitar `return`, dejar `Ok(())` como expresión final |
| `clippy::derivable_impls` | `impl Default for Enum` manual cuando el default es la primera variante | `#[derive(Default)]` + `#[default]` en la variante |

---

## 6. rustfmt — comportamiento con Unicode en assert macros

`cargo fmt --check` expande `assert_eq!(a, b, "msg")` a multi-línea cuando el string del mensaje contiene **caracteres UTF-8 multi-byte** (á, é, ó, ú, ñ, etc.) que empujan la medición interna de ancho por encima del umbral de rustfmt para macros.

**Formato correcto para `assert_eq!` con 3 argumentos:**

```rust
// ✗ Puede fallar fmt si el mensaje tiene Unicode
assert_eq!(version, 1, "schema_version debe ser 1 tras migración inicial");

// ✓ Siempre correcto
assert_eq!(
    version, 1,
    "schema_version debe ser 1 tras migración inicial"
);
```

**Regla práctica:** Si el mensaje de un `assert_eq!` contiene vocales acentuadas o ñ, **siempre usar formato multi-línea**. `left, right,` van en la misma línea si caben juntos dentro de 100 chars; el mensaje va en la siguiente.

---

## 7. Tests de integración (`tests/*.rs`) — alineación con API real

Los tests de integración acceden **solo a la API pública** del crate. Errores comunes cuando el test se escribió antes que la implementación:

| Error | Causa | Fix |
|-------|-------|-----|
| `E0599: no function from_connection` | Test usa constructor hipotético | Usar el constructor real (`::new(...)`) |
| `E0308: expected &Connection, found &Arc<Mutex<Connection>>` | `initialize_db` toma `&Connection` directa | Llamar antes de envolver en Arc: `initialize_db(&conn); let db = Arc::new(Mutex::new(conn));` |
| `E0560: struct has no field payload` | Campo renombrado a `payload_json` | Actualizar nombre + agregar campos requeridos |
| `E0599: no function from_str` | `FromStr` no en scope en mod tests | Agregar `use std::str::FromStr;` dentro del módulo de test |
| `E0277: doesn't implement Debug` | Struct de producción sin `#[derive(Debug)]` | Agregar `#[derive(Debug)]` al struct |

---

## 8. Security audit con `cargo-audit` — patrón CVE

### Flujo estándar

```yaml
- name: Security audit (Rust)
  working-directory: src-tauri
  run: |
    cargo install cargo-audit --quiet
    cargo audit
```

`cargo audit` falla el job si encuentra advisories activos. Esto es el comportamiento correcto.

### Suprimir temporalmente un advisory (`--ignore`)

Cuando un advisory bloquea CI pero el fix (bump de dependencia, patch) aún no está listo:

```yaml
cargo audit --ignore RUSTSEC-XXXX-XXXX
```

**Reglas obligatorias:**
1. `--ignore` es un parche de emergencia, **nunca una solución permanente**.
2. Abrir rama `fix/remove-<advisory-id>` en el mismo sprint o el siguiente.
3. Eliminar el flag en el mismo commit que resuelve el root cause.
4. Dejar el flag tras resolver el root cause suprime silenciosamente reintroducciones futuras del mismo ID.

### Caso real: RUSTSEC-2025-0009 (ring vía libp2p)

| Fase | Acción |
|------|--------|
| Bloqueo | `libp2p 0.54` traía `ring` con advisory de criptografía |
| Parche temporal | `cargo audit --ignore RUSTSEC-2025-0009` en ci.yml |
| Root cause fix | Bump `libp2p 0.54 → 0.55` en `Cargo.toml` |
| Limpieza | Eliminar `--ignore` del ci.yml en el siguiente commit |

---

## 9. Arquitectura CI: promote.yml — auto-merge staging → main

El CI del producto usa dos workflows encadenados:

```
push a staging
    └─► ci.yml (rust-checks + frontend-checks + build-check)
            └─► si conclusion == 'success'
                    └─► promote.yml: git merge --ff-only origin/staging → main
```

**`promote.yml` (fragmento clave):**

```yaml
on:
  workflow_run:
    workflows: ["CI"]
    branches: [staging]
    types: [completed]

jobs:
  promote:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    steps:
      - run: |
          git checkout main
          git merge --ff-only origin/staging
          git push origin main
```

**Implicaciones:**
- **No hacer merge manual staging → main.** Promote.yml lo hace automáticamente.
- Para verificar si main ya recibió el cambio: `git rev-parse origin/main origin/staging` deben ser iguales.
- Si CI falla en staging, main queda protegido — el promote no corre.

---

## 10. Arquitectura del pipeline completo (estado producción)

```
push a staging
├── secret-scan          (patrones: password/secret/api_key/Bearer/sk-)
├── rust-checks          (fmt + clippy + audit@0.22.1 + llvm-cov ≥80%)
│     └── upload-artifact: coverage-rust.lcov (30 días)
│     └── upload-codecov: flag=rust
└── frontend-checks      (npm audit --omit=dev + lint + typecheck + vitest --coverage 85%)
      └── upload-artifact: coverage-frontend/ (30 días)
      └── upload-codecov: flag=frontend
          │
          ↓ (needs: secret-scan + rust-checks + frontend-checks)
          build-check     (npm run build + cargo build --release)
              │
              ↓ (workflow_run: CI success + SHA verified + actor != bot)
              promote.yml  → main (--ff-only)
```

**promote.yml garantías:**
- SHA integrity: compara `github.event.workflow_run.head_sha` vs `git rev-parse origin/staging`. Si divergen (push nuevo mientras CI corría) → abort exit 1. Ningún commit no verificado llega a main.
- Actor restriction: bots (dependabot, github-actions) no alcanzan main automáticamente
- `--ff-only`: historial lineal garantizado. Falla si main tiene commits que staging no tiene.

**release.yml (v*.*.*) garantías:**
- Matrix ubuntu/windows/macos — universal binary en macOS (aarch64 + x86_64 via lipo)
- Ubuntu: imagemagick + conversión RGBA antes de tauri-action
- macOS: Pillow via pip para conversión RGBA (PEP 668 — usar actions/setup-python@v5)
- TAURI_SIGNING_PRIVATE_KEY firma los binarios y latest.json del auto-updater (Minisign)
- releaseDraft: true — publicación manual obligatoria (Gate 3 humano)

---

## 11. Qué garantiza y qué NO garantiza CI verde

**GARANTIZA (verificado por herramientas determinísticas en cada run):**
- 0 errores de formato rustfmt
- 0 warnings de clippy (-D warnings)
- 0 errores de tipo TypeScript (tsc --noEmit strict)
- 0 errores ESLint
- 0 vulnerabilidades CRITICAL/HIGH en deps Rust (cargo-audit 0.22.1 vs RustSec advisory-db)
- 0 vulnerabilidades HIGH/CRITICAL en deps npm de producción (npm audit --omit=dev)
- 0 secretos hardcodeados detectables por los 5 patrones regex del secret-scan
- Cobertura de líneas Rust ≥ 80% (cargo llvm-cov --fail-under-lines 80)
- Cobertura frontend ≥ 85% branches/functions/lines/statements (vite.config.ts)
- El build de producción completo compila (npm run build + cargo build --release)
- Solo commits verificados llegan a main (promote.yml SHA integrity check)

**NO GARANTIZA (requiere Gate 3 manual o tests adicionales):**
- El flujo P2P completo funciona (IT-01 a IT-07 — tests de integración PENDIENTE)
- Cobertura por módulo individualmente (audit/ 100%, identity.rs 100% — solo se verifica global)
- 0 unwrap() en rutas críticas de producción (requiere grep manual)
- 0 dangerouslySetInnerHTML (requiere grep manual)
- CSP explícito configurado en tauri.conf.json (verificación manual)
- Rate limiting por PeerId implementado (pendiente implementación)
- Firmado de código OS (Windows EV / Apple Developer ID — diferido v0.2)

---

## 12. Checklist completo de CI Rust/Tauri antes de merge a main

```
□ imagemagick en apt-get (rust-checks, build-check, release Ubuntu)
□ Step "Convert icons to RGBA" antes de primer cargo command (todos los jobs Linux)
□ Pillow via pip para conversión RGBA en macOS (usar actions/setup-python@v5 por PEP 668)
□ assert_eq! con mensajes Unicode → formato multi-línea (evita cargo fmt fail)
□ cargo fmt --check pasa
□ cargo clippy -- -D warnings pasa (0 errores)
□ cargo audit --version 0.22.1 (pin — 0.21.0 no soporta CVSS 4.0) sin advisories activos
□ cargo llvm-cov --fail-under-lines 80 pasa (≥ 80% cobertura de líneas)
□ Umbrales vitest definidos en vite.config.ts (85%) — NO en flags CLI
□ Archivos excluidos de cobertura frontend: main.tsx, App.tsx, ipc.ts, types.ts
□ secret-scan: sin matches en password/secret/api_key/Bearer/sk- hardcodeados
□ npm audit --audit-level high --omit=dev sin CVEs high/critical en producción
□ CODECOV_TOKEN configurado en GitHub Secrets (fail_ci_if_error: true)
□ Tests de integración usan API real, no constructores hipotéticos
□ FromStr en scope en módulos de test que lo usen
□ Structs usados en {:?} tienen #[derive(Debug)]
□ promote.yml: SHA integrity + actor restriction activos
□ --ignore en cargo-audit es siempre temporal — eliminar en el ciclo del fix definitivo
```
