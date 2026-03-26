# Átomo: quality/code_patterns
> ACCESO: StandardsAgent, CodeImplementer (Specialist Agent)
> CROSS-IMPACT: core/architecture_decisions
> Patrones de calidad de código aprendidos en sesiones anteriores.

---

## Patrones de calidad — Stack Python/FastAPI

**ruff con `ignore = ["E501"]`**
Docstrings y comentarios no deben penalizar por longitud. La regla E501 (line too long) causa más ruido que valor en docstrings largos. Configurar en `pyproject.toml`.

**Circular buffer para estructuras de crecimiento ilimitado**
`deque(maxlen=N)` en lugar de `list` para cualquier estructura in-memory que crece sin límite (audit logs, caches). Definir `N` según el caso de uso; previene OOM en procesos de larga duración.

**Serialización de deque para FastAPI**
`list(store.<deque>)` al retornar desde un endpoint. FastAPI no serializa `deque` directamente.

**CI/CD como gate de calidad obligatorio**
- ruff (linting) como paso bloqueante
- pip-audit (SCA) como paso bloqueante
- `--cov-fail-under=90` para cobertura mínima bloqueante

**pyproject.toml vs. setup.py**
Preferir `pyproject.toml` para configuración de herramientas (ruff, pytest, coverage). Es el estándar moderno de Python.

---

## Checklist de calidad técnica (anti-patrones comunes)

Criterios de penalización observados en auditorías — verificar antes de Gate 2:

- Audit log capturando status_code incorrecto (ej. siempre 200 en lugar del código real)
- Estructuras in-memory de crecimiento ilimitado sin `deque(maxlen=N)`
- Sin exception handler genérico (errores 500 exponen stack trace)
- Sin headers de seguridad HTTP (HSTS, X-Content-Type-Options, X-Frame-Options)
- Contenedor Docker ejecutando como root
- Sin HEALTHCHECK en Dockerfile
- Sin CI coverage gate bloqueante
