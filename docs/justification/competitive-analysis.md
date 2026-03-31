# PIV/OAC — Justificación Competitiva

> Versión: 1.0 | Fecha: 2026-03-23 | Audiencia: arquitectos, CTOs, equipos de ingeniería evaluando frameworks de orquestación de agentes

---

## 1. Resumen ejecutivo

PIV/OAC no es un framework de orquestación genérico. Es un **sistema de gobernanza estructurada para agentes de IA** con énfasis en audit trail completo, compliance integrado y gates bloqueantes verificados por herramientas deterministas. En el espectro de marcos disponibles, ocupa un nicho que hoy está vacío: **la intersección de orquestación multi-agente y gobierno empresarial de IA**.

**Úsalo cuando:**
- El output del sistema de IA tiene implicaciones regulatorias, legales o de seguridad
- Necesitas trazabilidad RF → código verificable para auditorías internas/externas
- El costo de un error en producción supera el costo de ciclos de revisión adicionales
- Operas en entornos sujetos a EU AI Act, HIPAA, SOC2, GDPR o similar

**No lo uses cuando:**
- Necesitas un prototipo en < 4 horas (usa LangChain o CrewAI Lite)
- El sistema no requiere ningún tipo de auditoría o gobernanza
- Tu equipo aún está explorando qué quiere construir (usa AutoGen notebooks)

---

## 2. Tabla comparativa de características

| Característica | PIV/OAC | LangGraph | CrewAI | AutoGen | Sem. Kernel | OpenHands |
|---|---|---|---|---|---|---|
| **Gates bloqueantes formalizados** | 4 gates (1/2/2b/3) | ✗ | ✗ | ✗ (proxy) | ✗ | ✗ |
| **Audit trail RF → código** | ✓ AuditAgent completo | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Agente de seguridad dedicado** | ✓ SecurityAgent (Opus) | ✗ | ✗ | Sandbox | Azure CSafety | Sandbox |
| **Evaluación legal integrada** | ✓ ComplianceAgent | ✗ | ✗ | ✗ | Parcial | ✗ |
| **Veto por intención maliciosa** | ✓ Nivel 0 obligatorio | ✗ | ✗ | ✗ | ✗ | ✗ |
| **DAG explícito pre-ejecución** | ✓ validado antes de crear agentes | Graph | Tasks | ✗ | ✗ | ✗ |
| **Memoria estructural por dominio** | ✓ 8 átomos engram | Thread state | Entity mem. | Conversation | Vector stores | Event stream |
| **Torneo multi-experto** | ✓ EvaluationAgent 5D | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Recovery de sesión (R/N/A)** | ✓ checkpoint .piv/ | Checkpointer | ✗ | ✗ | ✗ | Event replay |
| **CI/CD integrado en framework** | ✓ 12 jobs | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Detección de prompt injection** | ✓ regla permanente | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Modo RESEARCH epistemológico** | ✓ EpistemicAgent | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Cobertura de tests forzada** | ✓ ≥80% Gate 2b | ✗ | ✗ | ✗ | ✗ | Ejecuta tests |
| **Publicado en PyPI** | ✓ piv-oac | ✓ langgraph | ✓ crewai | ✓ pyautogen | ✓ semantic-kernel | ✗ |
| **Soporte multi-lenguaje** | Python | Python | Python | Python | Python/C#/Java | Python |
| **Comunidad activa** | En construcción | Grande | Grande | Grande | Grande | Grande |

---

## 3. Análisis por caso de uso

### 3.1 Sistemas de IA en industrias reguladas

**Contexto:** HIPAA (salud), PCI-DSS (finanzas), EU AI Act (sistemas de alto riesgo), SOC2.

| Requisito regulatorio | PIV/OAC | Alternativas |
|---|---|---|
| Audit trail de cada decisión automatizada | ✓ `logs_veracidad/` + engram append-only | Implementar manualmente |
| Evaluación de riesgos pre-despliegue | ✓ ComplianceAgent FASE 1 obligatoria | No existe |
| Control humano sobre acciones irreversibles | ✓ Gate 3 solo con confirmación explícita | `human_input=True` ad-hoc |
| Trazabilidad requisito → implementación → evidencia | ✓ AuditAgent RF coverage | No existe |
| Sin secretos en artefactos auditados | ✓ SecurityAgent Fase 1 grep + pip-audit | No existe |

**Ventaja diferencial:** En una auditoría, PIV/OAC produce `TechSpecSheet` (ISO/IEC/IEEE 29148 + ISO/IEC 25010) automáticamente en FASE 8. Ningún competidor genera documentación de auditoría de calidad normativa.

---

### 3.2 Desarrollo de software con múltiples expertos paralelos

**Contexto:** equipo quiere usar agentes paralelos con código real, no solo texto.

LangGraph y AutoGen resuelven la coordinación mediante grafos de estado y conversaciones. El problema: **no verifican que el output sea correcto antes de integrarlo**.

PIV/OAC agrega:
- **Gate 1 (CoherenceAgent):** verifica semánticamente que los aportes de expertos A y B son compatibles antes del merge
- **Gate 2b:** semgrep + pip-audit + pytest-cov con umbrales reales antes de integrar a staging
- **EvaluationAgent:** selecciona el mejor output mediante scoring 5D objetivo (FUNC/SEC/QUAL/COH/FOOT)

**Resultado:** se reduce el riesgo de integrar código de agente que pasa la ejecución pero tiene vulnerabilidades de seguridad o cobertura insuficiente.

---

### 3.3 Proyectos con alta deuda de protocolo

**Contexto:** el equipo lleva meses de desarrollo de agentes y los outputs son inconsistentes entre sesiones.

La causa más común: **ausencia de memoria estructural entre sesiones**. LangGraph y AutoGen tienen checkpoints de conversación, pero no diferencian entre "decisión arquitectónica de este objetivo" y "patrón de seguridad reutilizable" y "precedente de gate aprobado".

PIV/OAC resuelve esto con el sistema engram:

```
engram/
├── core/architecture_decisions.md    ← decisiones que no se repiten
├── audit/gate_decisions.md           ← historial de veredictos con rationale
├── security/patterns.md              ← patrones de ataque conocidos y mitigados
├── coherence/conflict_patterns.md    ← conflictos resueltos → no vuelven a surgir
├── quality/code_patterns.md          ← patrones de calidad que StandardsAgent reutiliza
└── precedents/                       ← solo post-Gate 3: validados en producción real
```

El resultado es que cada sesión comienza con el aprendizaje de todas las sesiones anteriores, segmentado por dominio y solo accesible al agente correcto (Zero-Trust Metodológico).

---

### 3.4 Equipo nuevo adoptando IA generativa para código de producción

**Contexto:** adopción de agentes en una base de código existente con requisitos de calidad y revisión obligatoria.

**Problema con CrewAI / LangGraph:** el agente puede producir código que compila pero viola convenciones del proyecto, introduce dependencias no aprobadas, o genera cobertura insuficiente. El equipo humano debe revisar cada línea.

**PIV/OAC reduce la carga de revisión humana porque:**
1. El código ya pasó SecurityAgent antes de llegar a la revisión humana
2. La cobertura de tests ya está medida (≥80%) — no hay que pedirla
3. Las dependencias nuevas ya pasaron pip-audit
4. Hay un TechSpecSheet que explica qué se hizo y por qué

La revisión humana (Gate 3) se convierte en una confirmación de calidad, no en una revisión desde cero.

---

## 4. Matriz de selección de framework

```
¿Necesitas audit trail formal + compliance?
    ├── SÍ → ¿equipo Python con tiempo de setup > 1 día?
    │         ├── SÍ → PIV/OAC
    │         └── NO → PIV/OAC Lite (en roadmap) o agregar ComplianceAgent manualmente
    └── NO → ¿orquestación compleja con estado persistente?
              ├── SÍ → LangGraph (grafos) o AutoGen (conversación multi-agente)
              └── NO → CrewAI (simplicidad de roles) o LangChain (cadenas simples)

¿Necesitas calidad verificada por herramientas en cada merge?
    ├── SÍ → PIV/OAC (Gate 2b) o LangGraph + pipeline CI propio
    └── NO → cualquier framework con CI personalizado

¿Múltiples expertos paralelos con evaluación comparativa?
    ├── SÍ → PIV/OAC (EvaluationAgent) — sin equivalente directo
    └── NO → AutoGen Swarm o CrewAI hierarchical

¿Modo exploración / prototipo en < 4 horas?
    └── NO usar PIV/OAC. Usar CrewAI o AutoGen notebooks.
```

---

## 5. Alineación con EU AI Act (2026)

El EU AI Act clasifica los sistemas de IA de alto riesgo (Anexo III) como sujetos a:
- Documentación técnica completa antes del despliegue
- Registro de logs para trazabilidad post-incidente
- Evaluación de riesgos antes de cada versión
- Supervisión humana sobre decisiones de alto impacto

| Requisito EU AI Act | Mecanismo PIV/OAC | Estado |
|---|---|---|
| Documentación técnica (Art. 11) | TechSpecSheet (ISO/IEC/IEEE 29148) FASE 8 | ✓ Implementado |
| Registro de logs (Art. 12) | `logs_veracidad/` append-only + engram con SHA-256 | ✓ Implementado |
| Evaluación de riesgos (Art. 9) | ComplianceAgent FASE 1 obligatoria | ✓ Implementado |
| Supervisión humana (Art. 14) | Gate 3 con confirmación explícita, Gate 3 recordatorio | ✓ Implementado |
| Robustez y exactitud (Art. 15) | EvaluationAgent FUNC/SEC/QUAL scoring | ✓ Implementado |
| Gestión de sesgos | ComplianceAgent + disclaimer obligatorio | Parcial |

PIV/OAC es, a fecha de este documento, el único framework de orquestación de agentes con alineación explícita con EU AI Act en su diseño arquitectónico.

---

## 6. Costo total de compliance (TCComp)

Para un proyecto que requiere auditoría formal:

| Actividad | Sin PIV/OAC | Con PIV/OAC |
|---|---|---|
| Generar documentación técnica de auditoría | 2–5 días/dev | Automático (FASE 8) |
| Verificar cobertura de requisitos | Manual, por sprint | AuditAgent en cada Gate 2b |
| Evaluación legal de dependencias | Consulta externa | ComplianceAgent FASE 1 |
| Revisión de seguridad pre-merge | Code review manual | SecurityAgent Gate 2/2b |
| Trazabilidad post-incidente | Búsqueda manual en git | `logs_veracidad/` + engram |
| **Total estimado por objetivo** | **3–8 días adicionales** | **< 0.5 días (Gate 3)** |

El ROI se justifica en el primer objetivo que requiera documentación de compliance.

---

## 7. Cuando la comparación no favorece a PIV/OAC

Ser honesto sobre las limitaciones actuales:

| Limitación | Impacto | Solución planificada |
|---|---|---|
| Comunidad en construcción | Sin soporte comunitario ni ejemplos externos | Apertura de repositorio + ejemplos en `examples/` |
| Solo Python | No viable para proyectos Node/Go/Java | SDK multi-lenguaje no en roadmap inmediato |
| Overhead de protocolo alto para proyectos pequeños | ≥ 4h de setup para proyectos simples | Perfil Lite (roadmap modular_v1.0) |
| Sin interfaz visual de estado | Visibilidad solo por CLI | `piv status` + dashboard OTel planificado |
| Monolítico (v0.1.x) | No componible con otros frameworks | Arquitectura modular en roadmap Sprint P3 |

---

## 8. Conclusión

PIV/OAC no compite directamente con LangGraph, CrewAI o AutoGen en el espacio de prototipado rápido. Compite con la ausencia de gobernanza estructurada en todos ellos.

La pregunta no es "¿PIV/OAC vs LangGraph?" sino "¿quién verifica que el agente hizo lo correcto?". En los frameworks existentes, esa responsabilidad recae 100% sobre el desarrollador humano. En PIV/OAC, el sistema verifica formalmente la calidad, seguridad, coherencia y compliance antes de que el código llegue a revisión humana.

Para equipos que construyen sistemas de IA que van a producción en contextos donde el error tiene costo real, PIV/OAC reduce el riesgo de forma estructural y verificable, no solo por convención.
