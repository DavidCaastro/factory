# ENGRAM — Context-Map (Índice de Relaciones)
> Escritura exclusiva: AuditAgent al cierre de cada sesión Nivel 2.
> Lectura: cualquier agente durante inicialización para resolver qué átomos cargar.
> Este archivo es la única fuente de verdad sobre qué átomo carga qué agente y qué cross-impacts existen.

---

## Cómo usar este índice

Cada agente, al inicializarse, lee SOLO su sección de este índice. Carga:
1. Átomos **PRIMARY**: siempre, sin condición
2. Átomos **CONDITIONAL**: solo si la condición de tarea se cumple
3. Átomos de **CROSS-IMPACT**: pre-cargados automáticamente cuando los indica el átomo primario

El agente NO lee átomos de otras secciones salvo que aparezcan como cross-impact explícito.

---

## Tabla de Acceso por Agente

### Master Orchestrator
```
PRIMARY:
  - core/architecture_decisions
  - core/operational_patterns
CONDITIONAL:
  - IF dominio identificado en DAG y existe engram/domains/<name>/ → core/architecture_decisions + domains/<name>/technical
  - IF objetivo nuevo sin precedentes en engram/ → ningún átomo adicional (construir desde cero)
ACCESO RESTRINGIDO: engram/security/ — NO accesible para Master Orchestrator
```

### SecurityAgent (+ sub-agentes SecurityAgent/*)
```
PRIMARY:
  - security/patterns
  - security/vulnerabilities_known
CONDITIONAL:
  - IF task involves auth/autenticación → +cross: domains/<nombre>/technical (si existe)
  - IF task involves new dependencies → +cross: security/sca_patterns (si existe)
  - IF gate review de un plan → +cross: audit/gate_decisions (evitar re-aprobar plan ya rechazado)
ACCESO EXCLUSIVO: engram/security/ (los átomos de este dominio son solo para SecurityAgent y sus sub-agentes)
```

### AuditAgent
```
PRIMARY:
  - audit/gate_decisions
  - audit/rf_coverage_patterns
CONDITIONAL:
  - IF cerrando sesión → todos los átomos donde hubo escritura en la sesión actual (para actualizar cross-impacts)
  - IF gate review de un plan → +cross: security/patterns (verificar que el plan no repite vulnerabilidades conocidas)
```

### CoherenceAgent
```
PRIMARY:
  - coherence/conflict_patterns
CONDITIONAL:
  - IF conflicto en dominio conocido → +cross: domains/<name>/technical (contexto de decisiones del dominio)
```

### StandardsAgent
```
PRIMARY:
  - quality/code_patterns
  - quality/test_patterns
CONDITIONAL:
  - IF dominio con historial → +cross: domains/<name>/technical (patrones de calidad específicos del dominio)
```

### ComplianceAgent
```
PRIMARY:
  - compliance/risk_patterns
CONDITIONAL:
  - IF objetivo similar a histórico → +cross: core/architecture_decisions (decisiones con implicaciones legales)
```

### Domain Orchestrators
```
PRIMARY:
  - domains/<nombre-dominio>/technical (si existe)
  - domains/<nombre-dominio>/patterns (si existe)
CONDITIONAL:
  - IF dominio nuevo → ningún átomo de dominio (crear al cierre)
  - IF dominio con historial de vulnerabilidades → SecurityAgent notifica cross-impact específico
```

### Specialist Agents (Expertos)
```
PRIMARY:
  - domains/<nombre-dominio>/patterns (si existe)
CONDITIONAL:
  - IF tarea relacionada con seguridad → SecurityAgent inyecta los fragmentos relevantes (nunca acceso directo a engram/security/)
```

### EvaluationAgent
```
PRIMARY:
  - precedents/INDEX.md (catálogo de precedentes VALIDADOS para el tipo de tarea actual)
CONDITIONAL:
  - IF tarea con historial de precedentes → cargar precedente VALIDADO más reciente del tipo
  - IF precedente disponible con score ≥ 0.85 → incluir como estrategia de partida
ACCESO RESTRINGIDO: engram/security/ — NO accesible para EvaluationAgent
ESCRITURA: solo en engram/precedents/ y solo post-Gate 3 por delegación de AuditAgent
```

---

## Registro de Cross-Impacts Activos

> Actualizado por AuditAgent al cierre de cada sesión. Lista los pares de átomos con relación de impacto cruzado.

| Átomo A | Átomo B | Dirección | Naturaleza del impacto | Sesión origen |
|---|---|---|---|---|
| security/patterns | domains/<nombre>/technical | A→B | Patrones de seguridad del dominio impactan decisiones técnicas locales | — |
| quality/test_patterns | domains/<nombre>/technical | A→B | Patrones de testing aplican directamente al dominio | — |
| core/operational_patterns | audit/gate_decisions | A→B | Patrones operativos de agentes impactan calidad de los gates | 2026-03-13 |
| security/vulnerabilities_known | audit/gate_decisions | A→B | Planes rechazados en gate pueden estar motivados por vulns conocidas | 2026-03-13 |
| domains/piv-challenge/cycle_learnings | quality/test_patterns | A→B | Patrones de testing del ciclo piv-challenge refinan patrones generales de testing | 2026-03-16 |
| domains/piv-challenge/cycle_learnings | quality/code_patterns | A→B | Lecciones de str-Enum y firmas abstractas refinan patrones generales de código | 2026-03-16 |
| domains/axonum/technical | quality/test_patterns | A→B | Patrones de test Rust/Tauri (API alignment, FromStr scope, Debug derive) refinan test_patterns | 2026-03-24 |
| domains/axonum/technical | skills/rust-tauri-ci | A→B | Decisiones técnicas de Axonum validan el skill de CI Rust/Tauri | 2026-03-24 |
| precedents/INDEX.md | core/operational_patterns | A→B | Precedentes validan y refinan patrones operativos | — |
| precedents/INDEX.md | quality/code_patterns | A→B | Approaches ganadores refinan patrones de código | — |

---

## Registro de Átomos — Estado

| Átomo | Última actualización | Sesiones consultado | Estado |
|---|---|---|---|
| core/architecture_decisions | 2026-03-12 | 1 | ACTIVO |
| core/operational_patterns | 2026-03-17 | 2 | ACTIVO |
| security/patterns | 2026-03-13 | 3 | ACTIVO |
| security/vulnerabilities_known | 2026-03-13 | 2 | ACTIVO |
| audit/gate_decisions | 2026-03-13 | 1 | ACTIVO |
| audit/rf_coverage_patterns | 2026-03-13 | 1 | ACTIVO |
| quality/test_patterns | 2026-03-13 | 2 | ACTIVO |
| quality/code_patterns | 2026-03-13 | 1 | ACTIVO |
| coherence/conflict_patterns | — | 0 | VACÍO |
| compliance/risk_patterns | — | 0 | VACÍO |
| domains/<nombre>/technical | — | 0 | VACÍO — se crea por AuditAgent al cierre del primer objetivo del dominio |
| domains/piv-challenge/cycle_learnings | 2026-03-16 | 0 | ACTIVO — OBJ-001 (piv-challenge v0.1.0) |
| domains/axonum/technical | 2026-03-24 | 0 | ACTIVO — Axonum v0.1.0 (Tauri 2.x + Rust CI fixes) |
| precedents/INDEX.md | — | 0 | VACÍO — se crea con primer precedente VALIDADO |

> Átomos en estado VACÍO: se crean con primer contenido cuando un agente genera aprendizajes en esa dimensión.
> Átomos no consultados en >10 sesiones → AuditAgent los marca como REVISAR para posible archivado.

### LogisticsAgent
PRIMARY: ninguno (no aprende — solo estima)
CONDITIONAL: ninguno
ESCRITURA: ninguna (no escribe en engram/)
NOTA: LogisticsAgent no acumula conocimiento entre sesiones. Sus caps son fijos.
      Sus estimaciones mejoran si el ejecutor humano ajusta los parámetros de heurística.

### ExecutionAuditor
PRIMARY: ninguno (no consume contexto de engram al inicializarse)
CONDITIONAL: ninguno
ESCRITURA: engram/audit/gate_decisions.md — añade irregularidades CRITICAL detectadas
           para que SecurityAgent las consulte en sesiones futuras.

---

## Protocolo de Conflicto entre Átomos

Si AuditAgent detecta que una nueva lección contradice un átomo existente:

1. NO sobreescribir el átomo existente
2. Añadir la nueva lección con nota `⚠️ CONFLICTO con entrada [fecha]`
3. Si el conflicto es sobre seguridad → SecurityAgent adjudica en la próxima sesión
4. Si el conflicto es sobre calidad/patrones → StandardsAgent adjudica al cierre
5. Hasta resolución: ambas versiones coexisten; agentes deben leer AMBAS y aplicar criterio
