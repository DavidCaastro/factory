# INIT — Protocolo de Entrevista Estructurada
> Cargado por: Master Orchestrator cuando `execution_mode: INIT` en `specs/active/INDEX.md`
> o cuando `specs/active/` no existe.
> Propósito: generar `specs/active/` completo desde input mínimo del usuario.
> Output: 6 archivos en `specs/active/` listos para ejecución, sin ambigüedades.

---

## Cuándo Activar

INIT se activa si se cumple cualquiera de:
- `execution_mode: INIT` en `specs/active/INDEX.md`
- El directorio `specs/active/` no existe
- El usuario indica que quiere iniciar un proyecto nuevo

INIT **no se activa** si `specs/active/` existe y `execution_mode` ≠ `INIT`.

---

## Protocolo de Entrevista — 7 Preguntas Adaptativas

El Master Orchestrator formula las 7 preguntas en **un solo bloque** — nunca una por una.
Cada respuesta alimenta el árbol de decisión para inferir las dimensiones del spec.
Si el usuario responde "no sé" o delega → Claude decide con el criterio más restrictivo y seguro
compatible con lo declarado, lo anuncia explícitamente, y el usuario puede corregirlo en la revisión.

### Preguntas base

```
Q1. ¿Qué problema resuelve el sistema y quién lo usa?
    → Determina: tipo de producto, perfil de usuarios, compliance_scope base

Q2. ¿Los usuarios se autentican? ¿Existen roles o niveles de acceso distintos?
    → Determina: modelo de auth, RBAC/ABAC, aislamiento de datos entre usuarios

Q3. ¿Qué tipo de datos maneja el sistema?
    (personales, financieros, médicos, internos, públicos, combinación)
    ¿En qué mercados o jurisdicciones operará? (UE, EEUU, global, solo interno, etc.)
    → Determina: compliance_scope definitivo, cifrado, retención, GDPR/HIPAA/CCPA

Q4. ¿Cuáles son las 3 a 5 capacidades principales que debe tener el sistema?
    (lista libre — Claude infiere los RFs, ACs y dependencias entre módulos)
    → Determina: functional.md completo, DAG de tareas, priorización de RFs

Q5. ¿Qué tecnología usas o prefieres? Si no tienes preferencia, ¿quieres que proponga?
    → Determina: architecture.md stack, vulnerabilidades conocidas del stack,
      skills a cargar en cada tarea

Q6. ¿Qué restricciones existen? (equipo, plazo, integraciones externas, presupuesto)
    → Determina: scope del MVP, prioridad de RFs, riesgos de dependencias externas,
      decisiones de arquitectura condicionadas

Q7. ¿Qué significa para ti que el sistema está listo para entregarse?
    Si no tienes criterio propio, aplico los estándares del framework.
    → Determina: quality.md umbrales, DoD, criterios de Gate 3
```

---

## Árbol de Decisión Implícito

El contenido de cada pregunta siguiente se ajusta según las respuestas anteriores:

| Condición detectada en Q1-Q2 | Ajuste en preguntas siguientes |
|---|---|
| Múltiples tipos de usuario | Q2 profundiza en modelo de roles y permisos por recurso |
| Sistema monousuario | Q2 se enfoca en aislamiento de sesión y protección de cuenta |
| API pública / consumida por terceros | Q3 añade: rate limiting, API keys, SLA |
| Herramienta interna sin auth | compliance_scope → NONE automático, Q3 omite GDPR |
| Datos personales o financieros confirmados | Q3 profundiza en regulación aplicable por mercado |
| Usuario delega stack en Q5 | Claude propone stack justificado según tipo de producto y Q3 |
| Usuario delega DoD en Q7 | Claude aplica: 90% cobertura, 0 ruff, 0 pip-audit, docs obligatorios |

---

## Reglas de Inferencia

Cuando una respuesta es vaga, incompleta o delegada:

1. **Inferir el escenario más restrictivo y seguro** compatible con lo declarado
2. **Declararlo explícitamente** en el resumen previo a la escritura
3. **Justificarlo** con el estándar o criterio aplicado
4. **No preguntar de nuevo** — el usuario corrige en la revisión final, no durante la entrevista

**Nunca inferir — siempre preguntar explícitamente en el resumen de confirmación:**

| Dimensión | Por qué no se puede inferir |
|---|---|
| Jurisdicción / mercados de operación | Determina qué regulación aplica (GDPR, HIPAA, CCPA, LGPD…) — un error aquí invalida todo el compliance_scope |
| Existencia de datos personales de terceros | Si el usuario no menciona datos personales pero el sistema los procesa implícitamente → compliance_scope incorrecto |
| Integración con sistemas de pago reales | Trigger de PCI-DSS — no es inferible desde "gestión de pagos" sin confirmación |
| Retención de datos obligatoria por contrato | Requisito legal contractual, no técnico — no hay default seguro |

Si alguna de estas dimensiones queda sin respuesta tras la entrevista → incluir pregunta directa
en el resumen de confirmación antes de escribir los specs. No escribir specs con estas dimensiones
sin confirmar.

**Se puede inferir (con anuncio explícito en el resumen):**

Ejemplos de inferencia por defecto:

| Situación | Inferencia |
|---|---|
| No declara compliance | compliance_scope: MINIMAL si hay auth; NONE si no hay auth |
| No declara stack | FastAPI + PostgreSQL + JWT para APIs; stack según tipo para otros |
| No declara umbral de cobertura | 90% global (estándar del framework) |
| No declara modelo de auth | JWT stateless con expiración corta (≤60 min) |
| No declara roles | Un solo rol de usuario autenticado con aislamiento por owner_id |
| No declara mercado | **No inferir.** Preguntar explícitamente en el resumen de confirmación: "¿En qué jurisdicciones operará el sistema?" — nunca asumir regulación específica. Si el usuario no responde → compliance_scope: MINIMAL sin asignar regulación concreta; el compliance se resuelve en su revisión |

---

## Output — Resumen de Confirmación

Antes de escribir ningún archivo, Claude presenta al usuario:

```
He inferido lo siguiente a partir de tus respuestas.
Confirma o corrige — después escribo los specs/active/:

· Nombre del proyecto: [inferido]
· Tipo de producto: [inferido]
· execution_mode: [DEVELOPMENT / RESEARCH / MIXED]
· compliance_scope: [FULL / MINIMAL / NONE] — razón: [justificación]
· Stack: [propuesto o confirmado]
· RFs detectados:
    RF-01 — [nombre]: [descripción una línea]
    RF-02 — [nombre]: [descripción una línea]
    ...
· Riesgos detectados: [lista de implicaciones de seguridad o compliance]
· DoD: [umbrales de cobertura, linting, docs]

¿Confirmas? Puedes corregir cualquier punto antes de que escriba los archivos.
```

Antes de escribir en disco, el borrador se valida contra Nivel 0 (intención ética, de seguridad y legal).

**Protocolo si la validación de Nivel 0 falla sobre el borrador:**
1. NO escribir ningún archivo en `specs/active/`
2. Emitir VETO con razón específica: qué elemento del borrador activa el veto (ej: compliance_scope inferido sugiere uso dual, RF implica capacidad prohibida)
3. Presentar al usuario las dos opciones:
   - **[C] Corregir:** el usuario ajusta las respuestas que causaron el veto → INIT genera nuevo borrador → nueva validación Nivel 0
   - **[A] Abandonar:** INIT no produce specs; el usuario puede reiniciar con un objetivo diferente
4. INIT no puede relajar los criterios de Nivel 0 ni intentar reformular automáticamente el borrador para sortear el veto — la corrección pertenece al usuario

Solo tras confirmación explícita del usuario Y aprobación de Nivel 0 se escriben los 6 archivos en `specs/active/`.

---

## Archivos Generados por INIT

| Archivo | Contenido generado | Template base |
|---|---|---|
| `specs/active/INDEX.md` | Identidad completa, execution_mode, compliance_scope | `specs/_templates/INDEX.md` |
| `specs/active/functional.md` | RFs con ACs, criterios de aceptación, edge cases de seguridad | `specs/_templates/functional.md` |
| `specs/active/architecture.md` | Stack, capas, estructura de módulos, DAG inicial | `specs/_templates/architecture.md` |
| `specs/active/security.md` | Threat model OWASP, requisitos de auth/authz, headers | `specs/_templates/security.md` |
| `specs/active/quality.md` | Umbrales de cobertura, DoD, requisitos de documentación | `specs/_templates/quality.md` |
| `specs/active/compliance.md` | Perfil legal, estándares aplicables, checklist GDPR si aplica | `specs/_templates/compliance.md` |

`specs/active/research.md` solo se genera si `execution_mode: RESEARCH` o `MIXED`.

### Plantillas de CI — Oferta opcional al cierre de INIT

Tras escribir los specs, INIT pregunta al usuario si desea instalar las plantillas de CI en el repo del producto:

```
¿Deseas instalar las plantillas de CI en el repo del producto?
  [S] Sí — copio y personalizo las plantillas con los valores de tu proyecto
  [N] No — puedes hacerlo manualmente desde specs/_templates/ci/
```

Si el usuario confirma, INIT realiza:
1. Copiar `specs/_templates/ci/piv_gate_checks.yml` → `.github/workflows/piv_gate_checks.yml`
   Sustituir: `{{SRC_DIR}}`, `{{TEST_DIR}}`, `{{COV_FAIL}}`, `{{PYTHON}}` con valores de `specs/active/`
2. Copiar `specs/_templates/ci/pre-commit-config.yaml` → `.pre-commit-config.yaml`
   Sustituir: `{{SRC_DIR}}` con el directorio fuente declarado en `specs/active/architecture.md`

**Regla:** INIT sustituye los marcadores `{{...}}` con valores reales antes de escribir.
Los archivos CI resultantes NO deben contener marcadores sin sustituir.

---

## Reglas de Escritura

- Claude lee cada `specs/_templates/*.md` y sustituye los marcadores `[PENDIENTE]` con el contenido inferido
- El texto de guía (bloques `>`) de cada template se **preserva intacto** — no se modifica
- Los marcadores `[PENDIENTE]` que no puedan resolverse se marcan como `[REQUIERE_DECISIÓN_HUMANA]`
- INIT nunca modifica `specs/_templates/` — solo escribe en `specs/active/`
- `specs/active/` está en `.gitignore` de `agent-configs` — se versiona en el repo del proyecto

---

## Post-INIT

1. Actualizar `execution_mode` en `specs/active/INDEX.md` al modo destino (DEVELOPMENT / RESEARCH / MIXED)
2. Confirmar al usuario que los specs están listos para ejecutar objetivos
3. El Master Orchestrator puede iniciar FASE 1 en el siguiente objetivo
