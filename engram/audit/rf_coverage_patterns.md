# Átomo: audit/rf_coverage_patterns
> ACCESO: AuditAgent
> CROSS-IMPACT: quality/test_patterns
> Patrones de cobertura de RFs y trazabilidad observados en sesiones anteriores.

---

## Patrón — Escritura en audit log antes de lanzar HTTPException

**Lección de trazabilidad:**
El audit log de dependencias como `check_rbac` y `check_rate` debe escribirse ANTES de lanzar la `HTTPException`. Es la única forma de capturar el evento cuando no hay middleware de respuesta implementado. Si se escribe después del lanzamiento, el evento no se registra.

---

## Formato de verificación estándar

```
RF-<id> (<descripción breve>):
  Estado: CUMPLIDO | INCUMPLIDO | PARCIAL
  Evidencia: <archivo:línea>
  Observación: <si PARCIAL o INCUMPLIDO>
```
