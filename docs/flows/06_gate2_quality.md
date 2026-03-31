# Flujo 06 — Gate 2: Calidad (merge feature → staging)
> Proceso: Triple gate — Security + Audit + Standards aprueban antes de merge a staging.
> Fuente: `registry/security_agent.md`, `registry/audit_agent.md`, `registry/standards_agent.md`, `CLAUDE.md` §FASE 6

```mermaid
flowchart TD
    START([Gate 1 aprobado — rama feature/<tarea> consolidada]) --> GATE2_LAUNCH

    subgraph GATE2_LAUNCH["Lanzar Gate 2 en PARALELO REAL"]
        GL1["Domain Orchestrator lanza simultáneamente:"]
        direction LR
        GL2["Agent(SecurityAgent\nrevisión de implementación\nrun_in_background=True)"]
        GL3["Agent(AuditAgent\nrevisión de implementación\nrun_in_background=True)"]
        GL4["Agent(StandardsAgent\nrevisión de calidad\nrun_in_background=True)"]
        GL1 --> GL2
        GL1 --> GL3
        GL1 --> GL4
    end

    subgraph SEC_CHECK["SecurityAgent — Checklist"]
        SC1["• Sin vulnerabilidades OWASP Top 10\n• Sin credenciales hardcodeadas\n• JWT/Auth correcto si aplica\n• pip-audit / $PIP_AUDIT_CMD sin CVEs críticos\n• CORS / headers de seguridad correctos"]
        SC1 --> SC2{Veredicto}
        SC2 -->|APROBADO| SEC_OK[Security: ✓]
        SC2 -->|RECHAZADO| SEC_FAIL["Security: ✗\nRazón específica + archivo:línea"]
    end

    subgraph AUD_CHECK["AuditAgent — Checklist"]
        AC1["• Todos los RFs del objetivo cubiertos\n• Sin acciones no documentadas\n• Trazabilidad: código ↔ RF\n• Logs de auditoria presentes si aplica"]
        AC1 --> AC2{Veredicto}
        AC2 -->|APROBADO| AUD_OK[Audit: ✓]
        AC2 -->|RECHAZADO| AUD_FAIL["Audit: ✗\nRFs sin cobertura + detalle"]
    end

    subgraph STD_CHECK["StandardsAgent — Checklist (modo DEV)"]
        ST1["[TESTS]\n• Cobertura verificada con pytest-cov (nunca estimada)\n• Happy path + casos límite + rutas de error\n• Sin tests skip sin justificación\n\n[DOCUMENTACIÓN]\n• Docstrings en funciones/clases públicas\n• OpenAPI actualizado si aplica\n\n[CALIDAD]\n• Sin código muerto ni imports sin usar\n• Complejidad ciclomática ≤ 10\n• Sin magic numbers hardcodeados\n\n[MANTENIBILIDAD]\n• SRP — funciones con responsabilidad única\n• Sin efectos secundarios ocultos"]
        ST1 --> ST2{pytest-cov\ndisponible?}
        ST2 -->|NO| ST_BLOCK["BLOQUEADO_POR_HERRAMIENTA\nNo emitir veredicto estimado\nReportar al DO para resolver"]
        ST2 -->|SÍ| ST3{Veredicto}
        ST3 -->|APROBADO| STD_OK[Standards: ✓]
        ST3 -->|RECHAZADO| STD_FAIL["Standards: ✗\nDimensiones fallidas + razón por dimensión"]
    end

    subgraph STD_CHECK_RES["StandardsAgent — Checklist (modo RESEARCH)"]
        SR1["[COBERTURA DE RQs]\n• Todas las RQs: RESUELTA o IRRESOLVABLE\n• Ninguna PENDIENTE o EN_PROGRESO\n\n[SOPORTE EVIDENCIAL]\n• Afirmaciones centrales citan ≥1 fuente con Tier\n• Sin afirmaciones apoyadas solo en TIER-4 o TIER-X\n\n[ESTRUCTURA DEL INFORME]\n• Secciones obligatorias presentes\n• Limitaciones sustantivas (no vacías)\n\n[COHERENCIA INTERNA]\n• Hallazgos consistentes entre sí\n• Conclusiones se derivan de hallazgos"]
        SR1 --> SR2{Veredicto}
        SR2 -->|APROBADO| STD_OK
        SR2 -->|RECHAZADO| STD_FAIL
    end

    GL2 --> SEC_CHECK
    GL3 --> AUD_CHECK
    GL4 --> STD_CHECK

    SEC_OK & AUD_OK & STD_OK --> TRIPLE_OK

    subgraph TRIPLE_OK["Los TRES aprueban"]
        TO1["Domain Orchestrator ejecuta merge:\ngit merge feature/<tarea> → staging\nEliminar worktrees de la tarea:\ngit worktree remove ./worktrees/<tarea>"]
        TO1 --> TO2["Actualizar checkpoint JSON:\nTarea → COMPLETADA\ngate_2_aprobado: true"]
    end

    subgraph ANY_FAIL["Alguno rechaza"]
        AF1{1er rechazo?}
        AF1 -->|SÍ| AF2["Devolver al DO con lista específica\nde dimensiones fallidas + archivos:línea\nDO reanuda desde el plan (no desde cero)"]
        AF1 -->|2do rechazo del mismo código| AF3["Escalar al Master Orchestrator\nNotificar al usuario"]
        AF2 --> GATE2_LAUNCH
    end

    SEC_FAIL --> ANY_FAIL
    AUD_FAIL --> ANY_FAIL
    STD_FAIL --> ANY_FAIL

    subgraph ROLLBACK["Rollback Post-Gate (si merge falla o problema crítico post-merge)"]
        RB1["1. Notificar Master con hash del commit pre-merge\n2. git revert <merge-commit-hash> en staging\n   (NUNCA git reset --hard — historial append-only)\n3. Reapertura rama feature/<tarea> si fue eliminada\n4. Registrar causa en AuditAgent\n5. Presentar al usuario: estado + causa + opciones\nTarea vuelve a: GATE_PENDIENTE"]
    end

    TO2 --> STAGING_DONE([Tarea en staging — esperar demás tareas del DAG])
```
