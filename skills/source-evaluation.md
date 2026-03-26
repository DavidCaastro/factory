# SKILL: Evaluación de Fuentes — PIV/OAC v3.2
> Cargado por: SourceEvaluator, EvidenceValidator, SecurityAgent (modo RESEARCH)
> Equivalente de investigación a `skills/backend-security.md` en desarrollo
> Cargado también por SecurityAgent en modo RESEARCH para detección de alucinaciones

---

## Tiers de Credibilidad de Fuentes

| Tier | Tipo de fuente | Peso evidencial | Ejemplos |
|---|---|---|---|
| TIER-1 | Peer-reviewed + replicado | Máximo | Papers con replicación, meta-análisis, RCTs |
| TIER-2 | Peer-reviewed / institucional oficial | Alto | Papers académicos, documentación oficial, RFC, estándares ISO/IETF/W3C |
| TIER-3 | Publicación técnica establecida / informe de industria | Medio | Reports de Gartner/IDC, posts técnicos de organizaciones reconocidas, libros técnicos |
| TIER-4 | Blog técnico / documentación de comunidad | Bajo — solo corroboración | Posts de ingenieros conocidos, wikis de comunidad, Stack Overflow |
| TIER-X | Sin autor identificable / sin fecha / sin referencia | NO USAR como evidencia | Artículos sin firma, páginas sin fecha, fuentes anónimas |

**Regla:** Una afirmación central en el informe necesita ≥1 fuente TIER-1 o TIER-2. Las fuentes TIER-4 solo pueden usarse para corroborar, no como soporte primario.

---

## Evaluación de Recencia

| Campo | Recencia requerida | Razón |
|---|---|---|
| Tecnología (frameworks, librerías) | ≤2 años | El ecosistema cambia rápido |
| Estándares (ISO, RFC, OWASP) | Verificar versión vigente | Los estándares se actualizan |
| Investigación científica | ≤5 años para área activa | Verificar si fue superada |
| Historia, humanidades, derecho | Sin límite estricto | El conocimiento histórico no caduca igual |
| Estadísticas y datos | Verificar año del dato | Una estadística de 2015 puede ser engañosa en 2026 |

---

## Indicadores de Sesgo a Detectar

El SourceEvaluator y el SecurityAgent (modo research) verifican activamente:

| Tipo de sesgo | Señal de alerta | Acción |
|---|---|---|
| Sesgo de confirmación | Solo se consultaron fuentes que apoyan la hipótesis | Buscar fuentes que la refuten activamente |
| Cherry-picking | Se citan partes de un estudio ignorando sus conclusiones contrarias | Citar la conclusión completa del estudio |
| Fuente circular | Varias fuentes citan la misma fuente original no evaluada | Ir a la fuente primaria |
| Actualización selectiva | Se usa versión antigua de un estándar que fue superado | Verificar versión vigente |
| Autoridad irrelevante | Un experto en campo A opina sobre campo B | Evaluar si la autoridad aplica al dominio |

---

## Verificación de Existencia de Fuentes

**Regla crítica:** El EpistemicAgent (SecurityAgent en modo research) debe verificar que las fuentes citadas existen y dicen lo que se afirma que dicen.

Señales de alucinación de fuentes:
- Título plausible pero no encontrable en búsqueda
- DOI o URL que no resuelve
- Autor que no tiene publicaciones en ese campo
- Año de publicación anterior a la existencia del concepto citado
- Cita que no aparece en el texto del paper referenciado

**Protocolo de verificación:**
1. Buscar el título exacto de la fuente
2. Verificar que el autor existe y publicó en ese campo
3. Verificar que el contenido citado aparece en la fuente (no solo el título)
4. Si no puede verificarse → marcar como FUENTE_NO_VERIFICADA y no usar como evidencia principal

---

## Manejo de Fuentes en Conflicto

Cuando dos fuentes de calidad comparable afirman cosas contradictorias:

```
CONFLICTO DETECTADO:
  Fuente A: [cita] → [afirmación A]
  Fuente B: [cita] → [afirmación B]
  Nivel de conflicto: DIRECTO / MATIZABLE / CONTEXTUAL

RESOLUCIÓN:
  DIRECTO: Documentar conflicto. No elegir una sobre otra sin justificación.
    → Reportar ambas perspectivas con sus respectivos soportes
    → Confianza del hallazgo baja a MEDIA máximo
  MATIZABLE: Identificar si las afirmaciones se aplican a contextos diferentes
  CONTEXTUAL: Verificar si el conflicto es de fecha, jurisdicción, stack, etc.
```

---

## Formato de Referencia Estandarizado

Toda fuente citada en un informe PIV/OAC debe incluir:

```
[ID-FUENTE] Apellido, N. (Año). Título. Fuente/Journal/URL.
  Tier: TIER-N
  Credibilidad evaluada: ALTA / MEDIA / BAJA / NO_VERIFICADA
  Accedida: [fecha de consulta — para URLs]
  Fragmento relevante: "[cita textual o paráfrasis del pasaje específico]"
```

Ejemplo:
```
[F-01] OWASP Foundation (2023). OWASP API Security Top 10 2023. owasp.org/API-Security
  Tier: TIER-2
  Credibilidad evaluada: ALTA
  Accedida: 2026-03-15
  Fragmento relevante: "API1:2023 - Broken Object Level Authorization [...]"
```
