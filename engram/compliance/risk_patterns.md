# Átomo: compliance/risk_patterns
> ACCESO: ComplianceAgent
> CROSS-IMPACT: core/architecture_decisions
> Patrones de riesgo legal/ético recurrentes identificados en objetivos anteriores.

---

> Bootstrap v3.2 — patrones pre-cargados desde la definición del framework (2026-03-16).
> El ComplianceAgent añadirá entradas reales al cierre de sesiones Nivel 2.

---

## Patrones Bootstrap — Riesgos conocidos por tipo de producto

### R-01: API con autenticación y datos de usuario → GDPR
```
FECHA: 2026-03-16 (bootstrap)
TIPO: Legal
DESCRIPCIÓN: Cualquier API que almacene o procese emails, IPs, nombres de usuario
             o identificadores persistentes activa obligaciones GDPR en mercados UE.
             El almacenamiento in-memory sin persistencia NO exime de GDPR si los datos
             son procesados (principio de minimización aplica al procesamiento, no solo al almacenamiento).
RESOLUBLE CON CÓDIGO: PARCIAL
RESOLUCIÓN O MITIGACIÓN: Implementar: derecho de acceso (GET /me), derecho de borrado (DELETE /me),
                          retención limitada de logs, consentimiento explícito si aplica.
                          Lo que el código NO puede resolver: política de privacidad, DPA con subprocesadores.
PATRÓN REUTILIZABLE: SÍ
```

### R-02: Tokens JWT sin revocación en store persistente → riesgo de sesión post-logout
```
FECHA: 2026-03-16 (bootstrap)
TIPO: Seguridad
DESCRIPCIÓN: JWT con store de tokens revocados in-memory pierde su lista al reiniciar el servicio.
             Tokens emitidos antes del reinicio quedan activos aunque el usuario haya hecho logout.
RESOLUBLE CON CÓDIGO: SÍ
RESOLUCIÓN O MITIGACIÓN: Usar Redis u otro store externo persistente para la lista de revocación.
                          Alternativa: JWTs de corta duración (≤15min) con refresh tokens.
PATRÓN REUTILIZABLE: SÍ
```

### R-03: Herramienta interna sin autenticación → riesgo de uso malintencionado
```
FECHA: 2026-03-16 (bootstrap)
TIPO: Ético / Uso Dual
DESCRIPCIÓN: Herramientas internas sin auth pueden ser expuestas accidentalmente y usadas
             para acceder a datos de usuarios sin consentimiento.
RESOLUBLE CON CÓDIGO: SÍ
RESOLUCIÓN O MITIGACIÓN: Toda herramienta con acceso a datos de usuarios debe tener
                          autenticación aunque sea interna. Principio de menor privilegio.
PATRÓN REUTILIZABLE: SÍ
```

## Formato de entrada

```
[FECHA] RIESGO en <objetivo>
TIPO: Legal | Ético | Seguridad | Reputacional | Uso Dual
DESCRIPCIÓN: <qué riesgo>
RESOLUBLE CON CÓDIGO: SÍ | NO
RESOLUCIÓN O MITIGACIÓN: <si SÍ> | ref: compliance/<objetivo>_mitigation.md <si NO>
PATRÓN REUTILIZABLE: SÍ | NO
```
