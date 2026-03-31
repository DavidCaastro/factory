# Átomo: domains/axonum/technical
> ACCESO: DomainOrchestrator, StandardsAgent, AuditAgent
> CROSS-IMPACT: quality/test_patterns, skills/rust-tauri-ci
> Decisiones técnicas y aprendizajes del proyecto Axonum (Tauri 2.x + Rust + libp2p).

---

## Stack técnico

- **Framework:** Tauri 2.x (Rust backend + React/TypeScript frontend)
- **P2P:** libp2p 0.54 (TCP, QUIC, Noise, Yamux, Kademlia, mDNS)
- **DB:** rusqlite 0.31 (bundled SQLite) — append-only audit log
- **Crypto:** argon2 (Argon2id) + chacha20poly1305 + zeroize
- **Anchor:** rs_merkle + ciborium (IOTA tangle stub)
- **Async:** tokio full
- **CI:** GitHub Actions ubuntu-latest (ubuntu-24.04)

## Módulos públicos del crate `axonum_lib`

```
pub mod anchor     — AnchorService::new(Arc<Mutex<Connection>>) → AnchorBatchResult
pub mod audit      — AuditManager::new(&Path, &str), AuditEventType (FromStr/Display SCREAMING_SNAKE_CASE)
pub mod commands   — Tauri invoke handlers
pub mod config     — PrivacyConfig (guarda en 0o600 en unix)
pub mod db         — migrations::initialize_db(&Connection), queries::insert_event(&Connection, &NewAuditEvent)
pub mod error
pub mod network    — session::SessionManager::new(usize), open_session(PeerId, Option<Multiaddr>)
pub mod node       — identity::NodeIdentity, mode::NodeMode (Default=User)
```

## Decisiones de API relevantes para tests

- `initialize_db` toma `&Connection` directa — NO `&Arc<Mutex<Connection>>`
- Para tests de integración: inicializar antes de envolver en Arc
- `AuditManager::new` abre su propio archivo — usar `tempfile::tempdir()` en tests
- `SessionManager` no persiste en DB — solo estado en memoria
- `AuditEventType::to_string()` produce SCREAMING_SNAKE_CASE (ej. `"NODE_STARTED"`)
- `MerkleRoot` es un newtype: `anchor.merkle_root.0` para el string

## CI — errores resueltos (2026-03)

Ver `skills/rust-tauri-ci.md` para el patrón completo.
Errores específicos resueltos: imagemagick, RGBA icons, clippy lint, assert_eq Unicode fmt,
integration test API mismatch (12 errores), FromStr scope, Debug derive.

## Frontend

- React 18 + TypeScript strict + Vite + Vitest + jsdom
- `@tauri-apps/api/core` — mock completo en test-setup.ts via `window.__TAURI_INTERNALS__`
- Tests usan `vi.mock("@tauri-apps/api/core")` en ConsentWizard, `vi.mock("../lib/ipc")` en Dashboard
- `aria-label="Modo privado"` (lowercase) en ConsentWizard, `"Modo Privado"` (uppercase) en Dashboard
