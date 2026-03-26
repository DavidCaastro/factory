---
name: piv-challenge cycle learnings
description: Technical learnings from OBJ-001 (piv-challenge v0.1.0) — Python 3.13 + pytest + anthropic SDK
type: project
domain: piv-challenge
objective: OBJ-001
date: 2026-03-16
---

# Aprendizajes de Ciclo — piv-challenge v0.1.0

## Python 3.13 + setuptools

- `setuptools.backends.legacy:build` fue eliminado en setuptools recientes → usar `setuptools.build_meta`
- `pydantic==2.6.4` requiere compilar `pydantic-core==2.16.3` desde Rust sin wheels para Python 3.13 → usar `pydantic>=2.7.0`
- `anthropic==0.25.0` depende de `tokenizers` que requiere Rust → usar `anthropic>=0.40.0`
- `ruff==0.1.6` no soporta `target-version = "py313"` → usar `py312` como proxy

## str-Enum discriminación

- `ExpectedOutcome(str, Enum)` hace que `isinstance(val, str)` sea siempre `True` para cualquier miembro del enum
- Para discriminar entre `ExpectedOutcome` miembro y string literal `"UNEXPECTED"`, usar:
  ```python
  # CORRECTO
  assert val in list(ExpectedOutcome) or val == "UNEXPECTED"
  # INCORRECTO (siempre True para miembros del enum)
  if isinstance(val, str): ...
  ```

## Firmas de métodos abstractos en harnesses

- `AgentHarness._call_agent` tiene firma `async def _call_agent(self, prompt: str) -> tuple[str, TokenUsage]`
- Los agentes subclase deben implementarla exactamente con esa firma (no `Scenario`)
- El `invoke()` base extrae `scenario.input_prompt` antes de llamar a `_call_agent`
- Usar `self._client` (con underscore) — no `self.client`

## Mock de sockets en tests async

- Parchear `socket.socket.connect` en tests async causa falsos positivos al teardown (pytest internals usan sockets)
- Para verificar que un cliente mock no hace HTTP → parchear `httpx.AsyncClient.send` en su lugar

## Cobertura con múltiples harnesses

- Cada harness concreto requiere tests propios (no hay cobertura transitiva desde el harness base)
- Pattern mínimo por harness: invoke() → AgentResult, _parse_output con VERDICT inglés, VEREDICTO español, output desconocido → "UNEXPECTED"
