# Especificaciones de Calidad — [NOMBRE DEL PROYECTO]
> Cargado por: StandardsAgent (Gate 2), TestWriter (inicio de tarea de tests)
> Define los umbrales de calidad requeridos para ESTE producto — no son los estándares del framework.
> ISO/IEC 25010:2023 — Non-Functional Requirements del producto

---

## Umbrales de Cobertura de Tests

| Tipo de módulo | Umbral requerido | Herramienta | Estado actual |
|---|---|---|---|
| Flujos críticos | 100% líneas + ramas | pytest-cov | PENDIENTE |
| Lógica de negocio | ≥90% | pytest-cov | PENDIENTE |
| Transport layer | ≥85% | pytest-cov | PENDIENTE |
| Coverage gate en CI | ≥90% global | `--cov-fail-under=90` | PENDIENTE |

> Ajustar umbrales según el tipo y criticidad del producto antes del primer objetivo.

---

## Requisitos de Calidad de Código

| Métrica | Umbral | Herramienta | Estado actual |
|---|---|---|---|
| Errores de linting | 0 (excepto E501) | ruff | PENDIENTE |
| Vulnerabilidades en dependencias | 0 | pip-audit | PENDIENTE |
| Complejidad ciclomática por función | ≤10 | radon (si disponible) | PENDIENTE |
| Longitud máxima de función | 50 líneas (sin docstring) | revisión manual | PENDIENTE |

---

## Requisitos de Documentación

| Elemento | Requisito | Estado actual |
|---|---|---|
| Funciones/métodos públicos | Docstring con Args, Returns, Raises | PENDIENTE |
| Endpoints de API | OpenAPI/Swagger automático | PENDIENTE |
| Variables de entorno | Documentadas en `.env.example` con comentarios | PENDIENTE |
| Política de seguridad | `SECURITY.md` en raíz | PENDIENTE |
| Changelog o historial | Documentado en specs/ o archivo dedicado | PENDIENTE |

---

## Requisitos de Infraestructura de Calidad

| Elemento | Requisito | Estado actual |
|---|---|---|
| CI/CD | Pipeline con gates bloqueantes | PENDIENTE |
| Imagen Docker | Usuario non-root + HEALTHCHECK | PENDIENTE |
| `.dockerignore` | Excluye archivos del framework y sensibles | PENDIENTE |

---

## Definición de Hecho (Definition of Done)

Un objetivo se considera COMPLETADO solo cuando:

1. Todos los RFs en scope están en estado CUMPLIDO con evidencia de archivo:línea
2. Cobertura global ≥90% verificada por pytest-cov (no estimada)
3. ruff: 0 errores
4. pip-audit: 0 vulnerabilidades
5. Todos los gates del framework: aprobados (Security + Audit + Standards + Coherence)
6. TechSpecSheet generado en `/compliance/<objetivo>/delivery/`
7. Merge a main con confirmación humana explícita
