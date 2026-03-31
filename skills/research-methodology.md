# SKILL: Metodología de Investigación — PIV/OAC v3.2
> Cargado por: Domain Orchestrators y Specialist Agents en modo RESEARCH
> Equivalente de investigación a `skills/layered-architecture.md` en desarrollo
> NO cargar en modo DEVELOPMENT

---

## Estructura de un Objetivo de Investigación

Un objetivo de investigación se descompone en fases análogas a las capas de desarrollo:

```
Fase de Encuadre     ← Definir pregunta, hipótesis, alcance, exclusiones
      ↓
Fase de Recolección  ← Buscar y evaluar fuentes por sub-pregunta (paralela)
      ↓
Fase de Síntesis     ← Integrar hallazgos, detectar contradicciones
      ↓
Fase de Validación   ← Verificar que cada afirmación tiene soporte evidencial
```

**Regla de flujo:** Ninguna fase arranca sin los outputs de la anterior (secuencial por default). Sub-preguntas independientes dentro de Recolección pueden ejecutarse en paralelo.

---

## Estructura del DAG de Investigación

| Tipo de tarea | Tipo en DAG | Expertos | Depende de |
|---|---|---|---|
| Encuadre del objetivo + mapa de fuentes | SECUENCIAL | 1 | — |
| Recolección por sub-pregunta independiente | PARALELA | 1 por sub-pregunta | Encuadre |
| Síntesis de hallazgos | SECUENCIAL | 1-2 | Todas las recolecciones |
| Validación de afirmaciones | PARALELA | 1 por bloque de afirmaciones | Síntesis |
| Generación del informe final | SECUENCIAL | 1 | Validación |

---

## Formato de Pregunta de Investigación (specs/active/research.md en modo RESEARCH)

Equivalente de los RFs en desarrollo. Cada RQ tiene el mismo contrato de verificabilidad:

```markdown
### RQ-01 — [Título de la pregunta]

| Atributo | Valor |
|---|---|
| Hipótesis | [afirmación tentativa que se busca confirmar o refutar] |
| Tipo | EXPLORATORIA / CONFIRMATORIA / COMPARATIVA |
| Criterio de resolución | ¿Qué evidencia constituiría una respuesta satisfactoria? |
| Fuentes esperadas | [tipo: papers / documentación oficial / datos empíricos / etc.] |
| Alcance | [qué entra en scope y qué NO] |
| Estado | PENDIENTE / EN_PROGRESO / RESUELTA / IRRESOLVABLE |
| Hallazgo | [síntesis del hallazgo con nivel de confianza] |
| Evidencia | [cita 1], [cita 2], ... |
| Confianza | ALTA / MEDIA / BAJA |
```

**Confianza ALTA:** ≥2 fuentes independientes de calidad ≥TIER-2 que coinciden.
**Confianza MEDIA:** 1 fuente de calidad ≥TIER-2, o múltiples fuentes de TIER-3 que coinciden.
**Confianza BAJA:** Fuente única de TIER-3, fuente no evaluable, o evidencia indirecta.

---

## Formato de Síntesis (output de SynthesisAgent)

```markdown
# Síntesis — [Nombre del objetivo]

## Hallazgos Principales
| RQ | Hallazgo | Confianza | Fuentes |
|---|---|---|---|
| RQ-01 | [síntesis] | ALTA | [citas] |

## Contradicciones Detectadas
| Fuente A | Fuente B | Naturaleza del conflicto | Resolución |
|---|---|---|---|

## Afirmaciones Pendientes de Validación
[Lista de claims que necesitan más evidencia]

## Limitaciones
[Qué NO pudo responderse y por qué — gaps de conocimiento explícitos]

## Metodología
- Fuentes consultadas: [N total]
- Fuentes incluidas: [N] | Excluidas: [N] (razón: [calidad / fuera de scope / duplicadas])
- Período de búsqueda: [fechas de las fuentes — no la fecha del agente]
- Idiomas: [lista]
```

---

## Definition of Done — Investigación

Un objetivo de investigación se considera COMPLETADO cuando:

1. Todas las RQs en scope están en estado RESUELTA o IRRESOLVABLE (con razón documentada)
2. Cada afirmación en el informe final tiene ≥1 cita con credibilidad ≥TIER-2
3. Todas las contradicciones entre fuentes están documentadas y abordadas
4. La sección de Limitaciones es explícita sobre qué no se pudo resolver
5. La sección de Metodología documenta el proceso de búsqueda y exclusión
6. EpistemicAgent (SecurityAgent en modo research) ha aprobado el informe final
7. El informe pasa Gate 2 (Audit trazabilidad de hipótesis) y Gate 3 (revisión humana)

---

## Diferencia con Desarrollo: El Gate de Calidad

En desarrollo, el gate es binario: tests pasan o fallan.
En investigación, el gate evalúa grados:

| Criterio | Condición de aprobación |
|---|---|
| Cobertura de RQs | 100% resueltas o justificadamente irresolubles |
| Soporte evidencial | 0 afirmaciones sin cita verificable |
| Contradicciones | Todas documentadas — ninguna ignorada |
| Confianza mínima | Ningún hallazgo central con confianza BAJA sin advertencia explícita |
| Limitaciones | Sección presente y honesta |
