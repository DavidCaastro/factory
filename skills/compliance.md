# SKILL: Checklists de Compliance — PIV/OAC v3.2
> Cargado por: ComplianceAgent durante FASE 1 y Gate 3
> Este archivo contiene checklists de referencia técnica contra estándares conocidos y publicados.
> LIMITACIÓN CRÍTICA: Este skill NO garantiza compliance legal. Es una referencia técnica.
> Todo despliegue en producción requiere revisión por asesor jurídico calificado.

---

## Árbol de Selección de Checklists

```
¿El producto procesa datos personales?
├── SÍ → activar checklist GDPR/CCPA/LGPD según geografía
│         + checklist de privacidad por diseño
└── NO → solo checklist de seguridad técnica

¿El producto procesa datos de salud?
└── SÍ → activar checklist HIPAA (si mercado USA)

¿El producto procesa datos de pago?
└── SÍ → activar checklist PCI-DSS

Tipo de producto:
├── API pública → OWASP API Security Top 10
├── Aplicación web → OWASP Top 10 + WCAG 2.1 AA (si interfaz pública)
└── Servicio interno → controles mínimos ISO 27001
```

---

## Checklist: Protección de Datos Personales (GDPR / CCPA / LGPD)

*Referencia: GDPR Reglamento UE 2016/679, CCPA California Consumer Privacy Act, LGPD Lei 13.709/2018*

```
BASE LEGAL
[ ] El sistema tiene base legal documentada para cada tipo de procesamiento
    (consentimiento, contrato, interés legítimo, obligación legal)
[ ] El propósito del procesamiento está definido y limitado (principio de finalidad)

MINIMIZACIÓN DE DATOS
[ ] Solo se recopilan datos estrictamente necesarios para el propósito declarado
[ ] No se almacenan datos más tiempo del necesario (política de retención definida)

DERECHOS DEL INTERESADO
[ ] El sistema puede responder a solicitudes de acceso a datos (SAR)
[ ] El sistema puede ejecutar derecho al olvido (borrado de datos)
[ ] El sistema puede exportar datos en formato legible (portabilidad)

SEGURIDAD TÉCNICA
[ ] Datos en reposo cifrados (AES-256 o equivalente)
[ ] Datos en tránsito cifrados (TLS 1.2+ obligatorio, 1.3 recomendado)
[ ] Acceso a datos personales con registro de auditoría
[ ] Pseudonimización o anonimización donde aplica

TRANSFERENCIAS INTERNACIONALES
[ ] Si hay transferencia fuera de UE/EEE: mecanismo de transferencia válido
    (Cláusulas Contractuales Tipo, Decisión de Adecuación, etc.)

INCIDENTES
[ ] Proceso documentado para notificación de brechas (72h GDPR)
[ ] Log de incidentes de seguridad habilitado
```

---

## Checklist: OWASP API Security Top 10

*Referencia: OWASP API Security Top 10 2023*

```
API1 - Broken Object Level Authorization (BOLA)
[ ] Cada endpoint verifica que el usuario autenticado tiene acceso al objeto solicitado
[ ] Los IDs de objetos no son secuenciales ni predecibles (usar UUIDs)

API2 - Broken Authentication
[ ] Tokens con expiración configurada
[ ] Refresh tokens implementados si aplica
[ ] Rate limiting en endpoints de autenticación
[ ] Mensajes de error no distinguen "usuario no existe" de "contraseña incorrecta"

API3 - Broken Object Property Level Authorization
[ ] Los schemas de respuesta solo exponen campos autorizados para el rol del usuario
[ ] No se retornan campos sensibles innecesariamente (passwords, tokens internos)

API4 - Unrestricted Resource Consumption
[ ] Rate limiting global implementado
[ ] Paginación obligatoria en endpoints que retornan listas
[ ] Límites de tamaño en uploads

API5 - Broken Function Level Authorization
[ ] Endpoints administrativos protegidos por roles, no solo autenticación
[ ] Operaciones destructivas requieren confirmación o privilegio adicional

API6 - Unrestricted Access to Sensitive Business Flows
[ ] Flujos críticos (compra, transferencia, cambio de contraseña) tienen protección adicional

API7 - Server Side Request Forgery (SSRF)
[ ] URLs externas validadas contra whitelist si el servidor hace requests externos

API8 - Security Misconfiguration
[ ] Headers de seguridad HTTP presentes (HSTS, X-Content-Type-Options, CSP)
[ ] Stack trace no expuesto en respuestas de error en producción
[ ] Endpoints de diagnóstico (/health, /metrics) protegidos o no expuestos externamente

API9 - Improper Inventory Management
[ ] Versiones antiguas de la API desactivadas o redirigidas
[ ] Documentación de API no expuesta en producción si es sensible

API10 - Unsafe Consumption of APIs
[ ] Datos de APIs externas validados con esquemas estrictos antes de usar
[ ] Timeouts y circuit breakers para dependencias externas
```

---

## Checklist: OWASP Top 10 (Aplicaciones Web)

*Referencia: OWASP Top 10 2021*

```
A01 - Broken Access Control
[ ] Principio de mínimo privilegio implementado
[ ] Control de acceso aplicado en servidor, no solo en cliente

A02 - Cryptographic Failures
[ ] Sin algoritmos débiles (MD5, SHA1 para contraseñas, DES)
[ ] BCrypt/Argon2/scrypt para hashing de contraseñas
[ ] Secretos no en código fuente ni en variables de entorno del sistema (usar vault/MCP)

A03 - Injection
[ ] ORM o prepared statements para todas las queries SQL
[ ] Inputs validados y sanitizados en capa de entrada
[ ] Sin eval() ni exec() con input del usuario

A04 - Insecure Design
[ ] Threat modeling realizado para flujos críticos
[ ] Separación de responsabilidades entre capas

A05 - Security Misconfiguration
[ ] Configuración de producción diferente de desarrollo (DEBUG=False, etc.)
[ ] CORS configurado restrictivamente

A06 - Vulnerable and Outdated Components
[ ] Dependencias sin vulnerabilidades conocidas (verificar con safety/snyk)
[ ] Proceso de actualización de dependencias documentado

A07 - Identification and Authentication Failures
[ ] Fuerza de contraseña mínima configurada
[ ] Bloqueo de cuenta tras intentos fallidos

A08 - Software and Data Integrity Failures
[ ] Integridad de dependencias verificada (hash/firma)
[ ] CI/CD con permisos mínimos

A09 - Security Logging and Monitoring Failures
[ ] Eventos de seguridad (login, acceso denegado, error 500) registrados
[ ] Logs sin datos sensibles (passwords, tokens, PII)

A10 - Server-Side Request Forgery
[ ] Ver API7 arriba
```

---

## Checklist: Licencias de Dependencias

```
[ ] Listar todas las dependencias directas con sus licencias
[ ] Listar dependencias transitivas críticas
[ ] Verificar compatibilidad con licencia del producto:
    - MIT, BSD, Apache 2.0 → compatible con casi todo
    - GPL v2/v3 → puede requerir que el producto sea GPL (copyleft)
    - LGPL → revisar si el uso es como biblioteca o incluido en el binario
    - AGPL → muy restrictiva si el producto es SaaS
    - Licencias comerciales → verificar términos de redistribución
[ ] Sin dependencias con licencia "sin licencia" (All Rights Reserved) sin acuerdo explícito
```

---

## Checklist: Uso Dual y Restricciones Especiales

```
[ ] ¿El producto puede ser usado para vigilancia masiva o rastreo de individuos sin consentimiento?
    SÍ → requiere Documento de Mitigación y controles técnicos de propósito
[ ] ¿El producto puede facilitar discriminación algorítmica (crédito, empleo, vivienda)?
    SÍ → requiere análisis de sesgo y documentación de limitaciones
[ ] ¿El producto incluye capacidades de IA/ML con decisiones que afectan personas?
    SÍ → activar checklist EU AI Act (si mercado UE) + documentación de limitaciones del modelo
[ ] ¿El producto podría exportarse a países con restricciones (tecnología dual)?
    SÍ → consultar con asesor legal especializado en comercio internacional
```

---

## Plantilla de Disclaimer Obligatorio

Todo informe generado por ComplianceAgent debe incluir:

```
---
DISCLAIMER: Este análisis es una referencia técnica basada en estándares públicos
conocidos a la fecha de generación ([FECHA]). No constituye asesoramiento legal
ni garantiza el cumplimiento de ninguna regulación aplicable. Las leyes y
regulaciones varían por jurisdicción y cambian con el tiempo. Este informe debe
ser revisado y validado por un asesor jurídico calificado antes del despliegue
del producto en producción o su distribución a terceros.
---
```
