# Átomo: core/architecture_decisions
> ACCESO: Master Orchestrator, Domain Orchestrators
> CROSS-IMPACT: audit/gate_decisions
> Restricción: NO incluir credenciales, URLs de infraestructura ni valores del security_vault.

---

## 2026-03-12 — Inicialización del Marco PIV/OAC

**Estructura de archivos del framework confirmada:**
- `CLAUDE.md` → punto de entrada para Claude Code (cargado automáticamente en cada sesión)
- `agent.md` → marco extendido PIV/OAC (referencia, no cargar por defecto — lazy loading)
- `skills/` → carga perezosa por tarea específica del agente
- `registry/` → definiciones de sub-agentes y protocolos
- `worktrees/` → no versionado (.gitignore), estructura `<tarea>/<experto>/`

**Arquitectura por Capas (stack Python/FastAPI):**
- Flujo unidireccional: Transporte → Dominio → Datos
- Ninguna capa puede saltarse la inmediatamente superior
- La capa de Dominio no importa nada de Transport

---

## 2026-03-13 — Decisiones técnicas de implementación (stack Python/FastAPI)

**In-memory store:**
- `dict` para caché de tokens revocados (hashmap, O(1) por clave string) — NO list/array
- `deque(maxlen=10_000)` para audit_log (circular buffer previene OOM)
- `list(store.audit_log)` al serializar para FastAPI (deque no es serializable directamente)

**Middlewares FastAPI — orden de registro importa:**
- Last registered = innermost (ejecuta primero en la respuesta)
- `audit_log_middleware` se registra DESPUÉS de `security_headers` → más cercano al handler → ve `request.state` antes de que se limpie
- `security_headers` se registra primero → envuelve todo → aplica headers a todas las respuestas incluyendo 500

**request.state para audit log con status_code real:**
- Problema: `check_rate` hace append al audit_log ANTES del handler → status_code siempre 200
- Solución: `check_rate` escribe `request.state.audit_entry = {sin status_code}` → `audit_log_middleware` en main.py lo completa con `response.status_code` real tras el handler
- Los eventos 403/429/401 siguen siendo append directo (ya tienen el código correcto antes del handler)

**Exception handler + TestClient:**
- `raise_server_exceptions=True` en TestClient re-lanza excepciones aunque el handler las capture
- Testear el exception handler directamente con `asyncio.run(handler(mock_request, exc))`, NO provocando excepción real vía HTTP
