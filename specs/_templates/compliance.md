# Especificaciones de Compliance — [NOMBRE DEL PROYECTO]
> Cargado por: ComplianceAgent + Master Orchestrator (FASE 0 y Gate 3)
> Define el perfil legal y de compliance del producto.
> DISCLAIMER: Este archivo es una referencia técnica. No constituye asesoramiento legal.

---

## Perfil del Producto

| Atributo | Valor |
|---|---|
| Tipo de producto | [PENDIENTE] |
| Procesa datos personales | [SÍ / NO — especificar qué tipo] |
| Procesa datos de salud | [SÍ / NO] |
| Procesa datos de pago | [SÍ / NO] |
| Mercado objetivo | [PENDIENTE] |
| Uso previsto | [PENDIENTE] |
| Audiencia | [PENDIENTE] |

---

## Evaluación de Riesgos de Uso

| Escenario de uso | ¿Permite usos malintencionados? | Mitigación |
|---|---|---|
| [escenario legítimo] | No | — |
| [escenario de riesgo potencial] | [nivel] | [mitigación] |

**Evaluación de intención (FASE 0):** [PENDIENTE — completar durante FASE 0 del primer objetivo.]

---

## Estándares de Compliance Aplicables

| Estándar | Aplicabilidad | Estado | Observaciones |
|---|---|---|---|
| OWASP API Security Top 10 (2023) | [SÍ / NO / CONTINGENTE] | PENDIENTE | — |
| OWASP Top 10 (2021) | [SÍ / NO / CONTINGENTE] | PENDIENTE | — |
| GDPR — Reglamento (UE) 2016/679 | [SÍ / NO / CONTINGENTE] | PENDIENTE | — |
| Licencias de dependencias | SÍ — siempre | PENDIENTE | Ejecutar pip-audit |

---

## Checklist GDPR (si aplica despliegue en UE)

> Estado: PENDIENTE — completar si el producto se despliega en la UE.

| Ítem | Estado |
|---|---|
| Base legal documentada para procesar datos personales | PENDIENTE |
| Política de privacidad disponible para usuarios | PENDIENTE |
| Mecanismo de ejercicio de derechos (acceso, borrado, portabilidad) | PENDIENTE |
| Datos en reposo cifrados | PENDIENTE |
| Datos en tránsito cifrados (TLS) | PENDIENTE |
| Proceso de notificación de brechas (72h) | PENDIENTE |
| Registro de actividades de tratamiento | PENDIENTE |

---

## Licencias de Dependencias

| Dependencia | Licencia | Compatible con uso previsto | Restricciones |
|---|---|---|---|
| [PENDIENTE — completar tras ejecutar pip-audit y revisar licencias] | — | — | — |

---

## Idiomas para Documentación de Despliegue

| Mercado de despliegue | Idiomas requeridos | Base legal |
|---|---|---|
| [PENDIENTE] | [PENDIENTE] | — |
| Despliegue en UE | Idioma oficial del país + inglés | GDPR Art. 12 |

---

## Documentos Generados

| Documento | Estado | Ruta |
|---|---|---|
| Informe de compliance | PENDIENTE (se genera post-merge a main) | `/compliance/<objetivo>_compliance.md` |
| Delivery Package | PENDIENTE | `/compliance/<objetivo>/delivery/` |
| Documento de Mitigación | PENDIENTE (solo si hay riesgos irresolubles) | — |
