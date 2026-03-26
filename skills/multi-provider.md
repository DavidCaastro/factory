# G-09 — Multi-Provider Abstraction

## 1. Principio de abstracción

El framework es model-agnostic a nivel de protocolo. Los contratos de salida
(`skills/agent-contracts.md`) son texto estructurado — cualquier LLM que siga
las instrucciones del system prompt puede cumplirlos. El SDK abstrae el proveedor
detrás de una interfaz común (`LLMClient`) de modo que cambiar de provider no
requiere modificar lógica de agentes ni de pipeline.

## 2. Providers soportados (v0.1)

| Provider         | Modelos recomendados por rol                                                             | Estado       |
|------------------|------------------------------------------------------------------------------------------|--------------|
| Anthropic Claude | Opus 4.6 (MasterOrch/Security), Sonnet 4.6 (Audit/Coherence/DO), Haiku 4.5 (Specialist) | STABLE       |
| OpenAI           | GPT-4o (MasterOrch/Security), GPT-4o-mini (otros)                                       | EXPERIMENTAL |
| Local (Ollama)   | llama3.1:70b (MasterOrch), llama3.1:8b (Specialist)                                     | EXPERIMENTAL |

## 3. Interfaz LLMClient (nivel SDK)

El SDK expone el siguiente `Protocol` (PEP 544). Todas las implementaciones deben
satisfacerlo:

```python
class LLMClient(Protocol):
    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        max_tokens: int = 4096,
    ) -> tuple[str, int, int]:  # (response_text, tokens_in, tokens_out)
        ...
```

El contrato de retorno `(response_text, tokens_in, tokens_out)` es obligatorio
para que el sistema de métricas de costo (`metrics/cost-schema.md`) pueda
contabilizar tokens independientemente del provider.

## 4. Implementaciones

| Clase             | Descripción                                                                                                  |
|-------------------|--------------------------------------------------------------------------------------------------------------|
| `AnthropicClient` | Wraps `anthropic.AsyncAnthropic`. Provider por defecto. STABLE.                                             |
| `OpenAIClient`    | Wraps `openai.AsyncOpenAI`. Requiere `pip install piv-oac[openai]`. EXPERIMENTAL.                           |
| `OllamaClient`    | Wraps `httpx.AsyncClient` hacia endpoint Ollama local (`http://localhost:11434`). EXPERIMENTAL.              |

La función de fábrica `get_client(provider, **kwargs) -> LLMClient` selecciona la
implementación correcta según el nombre del provider.

## 5. Selección de modelo por rol

La sección `provider` en `project_spec.md` es opcional; si se omite se usa
Anthropic con los modelos por defecto.

```yaml
# project_spec.md — sección provider (opcional)
provider:
  name: anthropic          # anthropic | openai | ollama
  endpoint: null           # solo para ollama; ej. http://localhost:11434
  model_map:
    master_orchestrator: claude-opus-4-6
    security_agent:      claude-opus-4-6
    audit_agent:         claude-sonnet-4-6
    coherence_agent:     claude-sonnet-4-6
    domain_orchestrator: claude-sonnet-4-6
    specialist_agent:    claude-haiku-4-5
```

Valores por defecto para OpenAI:

```yaml
provider:
  name: openai
  model_map:
    master_orchestrator: gpt-4o
    security_agent:      gpt-4o
    audit_agent:         gpt-4o-mini
    coherence_agent:     gpt-4o-mini
    domain_orchestrator: gpt-4o-mini
    specialist_agent:    gpt-4o-mini
```

Valores por defecto para Ollama:

```yaml
provider:
  name: ollama
  endpoint: http://localhost:11434
  model_map:
    master_orchestrator: llama3.1:70b
    security_agent:      llama3.1:70b
    audit_agent:         llama3.1:8b
    coherence_agent:     llama3.1:8b
    domain_orchestrator: llama3.1:8b
    specialist_agent:    llama3.1:8b
```

## 6. Restricciones de seguridad (SecurityAgent)

`SecurityAgent` siempre corre en el modelo más capaz disponible del provider
seleccionado. **No se permite degradarlo a modelos menores por ahorro de costo**
— el veto de seguridad requiere máxima capacidad de razonamiento.

Regla de fallback de provider para seguridad crítica:

> Si el provider seleccionado no tiene un modelo con capacidad de razonamiento
> equivalente a Opus (criterio: ventana de contexto ≥ 128 k tokens y capacidad
> de instrucción de nivel expert), `SecurityAgent` escala automáticamente a
> `AnthropicClient` con `claude-opus-4-6`, independientemente del provider
> configurado para el resto del pipeline.

Esta regla se aplica en `sdk/piv_oac/agents/security.py` antes de llamar a
`client.complete(...)`.

## 7. Consideraciones de calidad por provider

- Los system prompts de cada agente están optimizados para Claude. Con OpenAI u
  Ollama puede requerirse ajuste del tono instruccional (más directivo, menos
  conversacional).
- Los contratos de output (`skills/agent-contracts.md`) son agnósticos al
  provider — el parser (`ContractParser`) opera sobre texto estructurado con
  prefijos de campo y es igual independientemente del modelo.
- La calificación de gate (APPROVED/REJECTED) tiene el mismo criterio
  independientemente del provider — el resultado no varía por el modelo usado,
  solo por el contenido analizado.
- Al usar Ollama con modelos pequeños (≤ 8 B parámetros), se recomienda reducir
  la complejidad del contexto inyectado y aumentar `max_tokens` para compensar
  mayor tasa de truncamiento.

## 8. Compatibilidad con engram/VERSIONING.md y cost-control.md

- Los tokens se cuentan igual independientemente del provider (input / output).
  La tupla `(tokens_in, tokens_out)` que retorna `LLMClient.complete` se
  registra directamente en el snapshot de engram.
- El costo USD usa los precios del provider activo. Actualizar
  `metrics/cost-schema.md` con la tabla de precios del provider si se usa
  OpenAI u Ollama (Ollama local tiene costo efectivo $0 salvo hardware propio).
- Los snapshots de engram no dependen del provider — el formato
  (`engram/VERSIONING.md`) es agnóstico al modelo.
- La skill `skills/cost-control.md` aplica sus reglas de presupuesto y alarma
  usando los tokens contabilizados por `LLMClient.complete`, sin importar el
  provider activo.
