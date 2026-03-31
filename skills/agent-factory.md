# Skill: Agent Factory — Instanciación Controlada de Agentes

## Propósito
Protocolo para la instanciación controlada de agentes en el framework PIV/OAC.
Todo agente debe crearse a través del punto único de control (AgentFactory).
Este skill es implementado por el Master Orchestrator y los Domain Orchestrators.

## 1. Principio: Factory como Punto Único

Todo agente del framework se instancia siguiendo esta secuencia:
1. Validar que el solicitante tiene permiso para el tipo de agente pedido (PermissionStore)
2. Proyectar el contexto heredado del padre (InheritanceGuard)
3. Resolver el proveedor LLM según configuración (ProviderRegistry)
4. Instanciar el agente con contexto seguro
5. Registrar la instanciación en ExecutionAuditor

La instanciación directa fuera de este flujo es PROTOCOL_DEVIATION.

## 2. PermissionStore — Permisos con TTL

### Regla fundamental
`gate:*:bypass` NO EXISTE como permiso válido. Ningún grupo ni usuario puede concederlo.
Los gates solo se aprueban por agentes responsables o confirmación humana (Gate 3).

### FORBIDDEN_PERMISSIONS (ninguno puede concederse)
- `gate:*:bypass`
- `gate:security:bypass`
- `gate:audit:bypass`
- `gate:coherence:bypass`
- `gate:standards:bypass`
- `protocol:skip`

### TTL de permisos
- Default: 30 minutos
- El permiso `skill:write` (StandardsAgent): 30 minutos post-confirmación humana
- Permisos vencidos se tratan como no concedidos

## 3. InheritanceGuard — Herencia Controlada de Contexto

### SAFE_INHERIT (whitelist explícita)
Solo estos 5 atributos pueden pasar de agente padre a hijo:
- `objective_id`
- `task_scope`
- `execution_mode`
- `compliance_scope`
- `parent_agent_id`

**Todo lo demás (permisos, credenciales, api_keys, capabilities) NO se hereda.**
Los permisos del hijo los asigna PermissionStore, nunca el padre.

### Reglas de herencia
- MAX_INHERITANCE_DEPTH = 1 — solo padre → hijo. Sin cadenas recursivas.
- El snapshot de contexto heredado lleva firma HMAC + TTL de 30 minutos
- `InheritanceExpired`: snapshot vencido → solicitar snapshot fresco al factory
- `InheritanceTampered`: firma inválida → SECURITY_VIOLATION inmediato

## 4. Code Signing de Skills

### Propósito
Verificar integridad de skills antes de cargarlos. Previene modificación no autorizada
entre la escritura por StandardsAgent y la carga por un agente.

### Flujo de carga
1. AtomLoader busca el skill en `skills/manifest.json`
2. Si no está en manifest → BLOQUEADO_POR_HERRAMIENTA
3. Si está: cargar contenido del archivo
4. Calcular SHA-256 del contenido
5. Comparar con hash en manifest
6. Si no coincide → BLOQUEADO_POR_HERRAMIENTA (notificar usuario)
7. Si coincide → cachear y retornar

### Quién puede actualizar el manifest
Solo StandardsAgent con permiso `skill:write` (concedido post-gate SecurityAgent
con confirmación humana explícita). El permiso expira en 30 minutos.

### skills/manifest.json — formato
```json
{
  "version": "1.0",
  "generated_at": "<ISO8601>",
  "signed_by": "StandardsAgent",
  "objective_id": "<id>",
  "skills": {
    "<skill-name>": {
      "path": "skills/<name>.md",
      "sha256": "<hash>",
      "last_updated": "<ISO8601>",
      "gate_verified": true
    }
  }
}
```

## 5. Proveedor Default
Si no hay configuración multi-proveedor activa → Anthropic.
El sistema nunca falla por ausencia de proveedores alternativos.
El cambio de proveedor para un agente requiere que el modelo alternativo
cumpla la capacidad requerida para ese rol (no se degrada sin aprobación explícita).
