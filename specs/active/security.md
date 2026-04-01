# Especificaciones de Seguridad — PIV/OAC SDK v4.0
> Cargado por: SecurityAgent y SecurityAgent/* (exclusivamente)
> ⚠️ ACCESO RESTRINGIDO — igual que engram/security/
> Referencia de diseño: `specs/active/piv_oac_redesign_v4.md §4, §5, §11, §11b`

---

## Modelo de Amenazas (Threat Model)

| Categoría OWASP | Amenaza específica al SDK | Mitigación requerida | Estado |
|---|---|---|---|
| A01 — Broken Access Control | Agente instanciado sin validación de permisos | `AgentFactory` obliga paso por `PermissionStore.validate()` antes de instanciar | PENDIENTE |
| A01 — Broken Access Control | Gate bypaseado programáticamente | `PermissionStore` rechaza `gate:*:bypass` como permiso inválido | PENDIENTE |
| A01 — Broken Access Control | Herencia de permisos de padre a hijo | `InheritanceGuard.SAFE_INHERIT` excluye permisos, credenciales y capacidades | PENDIENTE |
| A02 — Cryptographic Failures | Mensaje inter-agente manipulado en tránsito | HMAC SHA-256 en `CryptoValidator`; `MessageTampered` sin reintento | PENDIENTE |
| A02 — Cryptographic Failures | Skill modificado en disco sin detección | Code Signing SHA-256 en `AtomLoader`; divergencia → `BLOQUEADO_POR_HERRAMIENTA` | PENDIENTE |
| A02 — Cryptographic Failures | Snapshot de herencia manipulado | Firma HMAC + TTL de 30min en `InheritanceGuard.validate_snapshot()` | PENDIENTE |
| A03 — Injection | Prompt injection en requests MCP | `MCPFilter._check_injection()` con patrones conocidos; `SecurityError` ante match | PENDIENTE |
| A03 — Injection | Credenciales embebidas en requests | `MCPFilter._check_credentials()` antes de pasar al factory | PENDIENTE |
| A04 — Insecure Design | Escalación de privilegios por herencia recursiva | Herencia limitada a single-level (padre → hijo); sin cadenas | PENDIENTE |
| A04 — Insecure Design | Confused Deputy — hijo hereda permisos de escritura | `InheritanceGuard` no propaga permisos; PermissionStore los asigna independientemente | PENDIENTE |
| A05 — Security Misconfiguration | Permiso `gate:*:bypass` configurado en YAML | Validación de config al cargar `piv_oac.yaml`: rechaza permisos de bypass | PENDIENTE |
| A05 — Security Misconfiguration | Redis sin autenticación en producción | Validación en `RedisStateStore.__init__()`: advertencia si URL sin credenciales en producción | PENDIENTE |
| A07 — Auth Failures | Permiso TTL vencido aceptado como válido | `PermissionStore._has_valid_permission()` verifica `expires_at > datetime.now()` | PENDIENTE |
| A09 — Logging Failures | Irregularidad de seguridad no registrada | `ExecutionAuditor.record_event()` registra todo evento; `generate_final_report()` nunca falla | PENDIENTE |
| DoW — Denial of Wallet | Input malicioso infla estimación de tokens | `LogisticsAgent` caps absolutos por nivel; `WARNING_ANOMALOUS_ESTIMATE` presentado al usuario | PENDIENTE |

---

## Requisitos de Seguridad del SDK

### Gestión de Secretos y Credenciales

- API keys resueltas exclusivamente desde variables de entorno (nunca hardcoded, nunca en YAML)
- `piv_oac.yaml` contiene solo referencias (`env_var: "ANTHROPIC_API_KEY"`), no valores
- `security_vault.md` en `.gitignore`
- `.env` en `.gitignore`
- Ningún agente del SDK escribe credenciales en logs, StateStore, ni en mensajes inter-agente
- `InheritanceGuard.SAFE_INHERIT` no incluye ningún atributo con "key", "secret", "token", "password", "credential"

### Integridad de Skills

- Todo skill cargado por `AtomLoader` tiene su SHA-256 verificado contra `skills/manifest.json`
- `skills/manifest.json` solo es modificable por `AtomLoader.register_skill()` con permiso `skill:write`
- El permiso `skill:write` solo puede concederse a StandardsAgent con TTL de 30 minutos
- Hash divergente → carga bloqueada + `SkillIntegrityError` + notificación al usuario antes de continuar
- Si `skills/manifest.json` está ausente → inicializar con manifest vacío (skills no cargables hasta registrar)

### Validación Criptográfica Inter-Agentes

- Todos los mensajes de gate firmados con HMAC SHA-256 antes de transmitir
- Verificación de: identidad del emisor, TTL del mensaje (5 minutos), integridad de firma
- `MessageTampered` (firma inválida o sender mismatch) → `SECURITY_VIOLATION` inmediato, sin reintento, reportado a `ExecutionAuditor`
- `MessageExpired` (TTL vencido, firma válida) → reintento con re-firma, máx. 3 intentos
- Un agente que reciba `MessageTampered` debe escalar al Master Orchestrator antes de continuar

### Gobernanza de Instanciación

- `AgentFactory` es el único punto de instanciación; cualquier otra vía lanza `InstantiationError`
- `PermissionStore.grant()` rechaza activamente permisos de la lista `FORBIDDEN_PERMISSIONS`
- Permisos tienen TTL máximo de 30 minutos; no existen permisos permanentes en el SDK
- Herencia de contexto: whitelist `SAFE_INHERIT`, single-level, TTL 30min, firma HMAC

### Filtrado de Input (MCPFilter)

- Todo request externo pasa por `MCPFilter` antes de llegar a `AgentFactory`
- Detecta prompt injection con patrones conocidos; ante detección → `SecurityError` + notificación al usuario
- Detecta credenciales embebidas en arguments; ante detección → `SecurityError`
- Rate limiting aplicado por `MCPFilter` antes de procesamiento

### Protección contra Denial of Wallet (DoW)

- `LogisticsAgent` aplica caps absolutos derivados de la clasificación Nivel 1/2 del protocolo
- Los caps no son configurables desde el input del objetivo ni desde YAML
- Estimación que supera cap → `WARNING_ANOMALOUS_ESTIMATE` presentado al usuario antes de continuar
- El usuario puede rechazar el objetivo o ajustar el scope, pero no subir el cap

---

## Dependencias de Seguridad

| Dependencia | Uso | Requisito de versión |
|---|---|---|
| `hmac` (stdlib) | HMAC SHA-256 para CryptoValidator e InheritanceGuard | Python ≥ 3.12 |
| `hashlib` (stdlib) | SHA-256 para AtomLoader (Code Signing) y artifact_ref CSP | Python ≥ 3.12 |
| `asyncio` (stdlib) | AsyncLockManager, GateEnforcer paralelo | Python ≥ 3.12 |
| `pip-audit` | Verificación de CVEs en dependencias | ≥ 2.7, ejecutar en Gate 2b |
| `redis[asyncio]` (opcional) | RedisStateStore | ≥ 5.0, solo si REDIS_URL configurada |

> Ejecutar `pip-audit` antes de Gate 2b. Resultado esperado: 0 CVEs críticos/altos.
> Las dependencias opcionales (redis, opentelemetry) no introducen CVEs en el path default.

## Dependencias Prohibidas — Denylist Permanente

Las siguientes dependencias están **permanentemente prohibidas** en cualquier componente del sistema.
Su presencia en `requirements.txt`, `pyproject.toml` o cualquier import es motivo de rechazo
automático en Gate 2b sin posibilidad de mitigación ni excepción.

| Paquete | Razón | Alternativa |
|---|---|---|
| `litellm` | Vulnerabilidad de seguridad — jamas utilizable en este sistema | `anthropic` SDK directo |

**Verificación obligatoria en Gate 2b (SecurityAgent):**
```bash
# Detectar dependencias prohibidas en requirements y código fuente
grep -rn "litellm" requirements*.txt pyproject.toml sdk/ 2>/dev/null && echo "FAIL: dependencia prohibida detectada" && exit 1 || echo "PASS: sin dependencias prohibidas"
```

> SecurityAgent ejecuta esta verificación con herramientas determinísticas antes de cualquier análisis LLM.
> Un hallazgo positivo es rechazo automático — no hay veredicto alternativo.

---

## Verificaciones Obligatorias en Gate 2b — SecurityAgent

```
# Secretos hardcodeados — ejecutar en src_dir = sdk/piv_oac/
grep -rn "api_key\s*=\s*['\"][^$]" sdk/piv_oac/
grep -rn "secret\s*=\s*['\"][^$]" sdk/piv_oac/
grep -rn "password\s*=\s*['\"][^$]" sdk/piv_oac/
grep -rn "ANTHROPIC_API_KEY\s*=\s*['\"]" sdk/piv_oac/

# CVEs en dependencias
pip-audit --requirement requirements.txt

# Verificar que FORBIDDEN_PERMISSIONS incluye los 6 permisos de bypass requeridos
grep -n "FORBIDDEN_PERMISSIONS" sdk/piv_oac/core/permission_store.py
grep -n "gate:.*bypass\|protocol:skip" sdk/piv_oac/core/permission_store.py
```

---

## Controles de Seguridad v4.0

### RS-MCPFILTER: MCPFilter como Primer Filtro

MCPFilter actúa como primer filtro de todo request externo antes de que llegue al factory.
Detecta y bloquea:
- Prompt injection (patrones conocidos en arguments y en contenido del request)
- Credenciales embebidas (api_key, secret, password, token en el request)
- Rate limiting: rechaza requests que superen el umbral configurado

Si detecta cualquiera de los anteriores → `SecurityError` + notificación al usuario.
El request no llega a AgentFactory.

### RS-INHERIT: InheritanceGuard

SAFE_INHERIT whitelist (solo estos 5 campos heredan de padre a hijo):
- `objective_id`, `task_scope`, `execution_mode`, `compliance_scope`, `parent_agent_id`

Reglas de verificación:
- TTL del snapshot heredado: 30 minutos con firma HMAC
- `InheritanceExpired` (TTL vencido): solicitar snapshot fresco al factory
- `InheritanceTampered` (firma inválida): `SECURITY_VIOLATION` inmediato — no reintentar

### RS-SIGN: Code Signing de Skills

Todo skill cargado por AtomLoader pasa verificación SHA-256 contra `skills/manifest.json`.
- Hash incorrecto → `BLOQUEADO_POR_HERRAMIENTA` + notificación al usuario
- Skill ausente del manifest → `BLOQUEADO_POR_HERRAMIENTA`
- Solo StandardsAgent con permiso `skill:write` puede actualizar el manifest
- El permiso `skill:write` se concede post-gate SecurityAgent con confirmación humana explícita
- El permiso expira en 30 minutos

### RS-PERM: Permisos Prohibidos

Los siguientes permisos NO pueden concederse por ningún medio (ni YAML, ni código, ni grant manual):

```
FORBIDDEN_PERMISSIONS = {
    "gate:*:bypass",
    "gate:security:bypass",
    "gate:audit:bypass",
    "gate:coherence:bypass",
    "gate:standards:bypass",
    "protocol:skip"
}
```

`PermissionStore.grant()` rechaza activamente estos permisos con `PermissionDenied`.
No existe una vía de override. La validación de config al cargar `piv_oac.yaml` también los rechaza.

---

## Limitaciones de Seguridad Conocidas

| Limitación | Impacto | Resolución en producción |
|---|---|---|
| `MCPFilter` detecta patterns de injection conocidos, no semántica arbitraria | Un prompt injection con redacción inusual puede no ser detectado | Complementar con revisión humana de objetivos sensibles + Zero-Trust Metodológico del protocolo |
| `FilesystemStateStore` no encripta datos en reposo | Checkpoints y artefactos de gate legibles en disco | Usar `RedisStateStore` con TLS + auth en entornos multi-usuario o compartidos |
| `skills/manifest.json` es un archivo de texto plano | Un atacante con acceso al filesystem puede reemplazar manifest y skill simultáneamente | Considerar signing del manifest con clave privada separada en v4.1 |
| TTL de permisos no persiste entre reinicios del proceso | En reinicio, `PermissionStore` comienza vacío y requiere re-concesión | Aceptable para uso con Claude Code; en despliegue continuo migrar a StateStore persistente |
