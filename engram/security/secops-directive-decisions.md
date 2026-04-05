# Engram: SecOps Directive Decisions

> **Escritor exclusivo:** AuditAgent (post-Gate 3)
> **Lector:** SecurityAgent (FASE 0), MasterOrchestrator (resumen de riesgo)
> **Propósito:** Historial de decisiones del usuario ante hallazgos de la rama directiva `sec-ops`

---

## Formato de entrada

Cada decisión registrada por AuditAgent sigue este schema:

```
---
fecha: YYYY-MM-DDTHH:MM:SSZ
objetivo_id: OBJ-XXX
dep_name: <nombre>
dep_version: <version>
risk_level: CRITICAL | HIGH
findings_count: N
decision: ACEPTAR_RIESGO | BUSCAR_ALTERNATIVA | GENERAR_COMPLIANCE_DOC
justificacion: <texto libre del usuario>
accion_tomada: <qué se hizo — alternativa elegida, doc generado, etc.>
---
```

---

## Decisiones registradas

<!-- AuditAgent añade entradas aquí. No modificar manualmente. -->
