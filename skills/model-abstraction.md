# Skill: Model Abstraction — Portabilidad de Proveedor LLM
> Cargado por: Master Orchestrator (evaluación de portabilidad), SecurityAgent (revisión de vendor lock-in)
> Versión: 1.0 | ISO/IEC 25010:2023 — Portabilidad / Mantenibilidad

---

## 1. Propósito

Define la política de abstracción de modelos LLM del sistema PIV/OAC para mitigar el riesgo de vendor lock-in con Anthropic/Claude. Permite evaluar el esfuerzo de migración y proporciona el patrón de abstracción recomendado cuando se requiere portabilidad.

**Riesgo mitigado:** Dependencia exclusiva de Claude API → proveedor alterna política, precios o disponibilidad → el framework queda inoperativo.

---

## 2. Tabla de Dependencias de Proveedor

| Componente | Dependencia actual | Portabilidad | Alternativa viable |
|---|---|---|---|
| Modelo de razonamiento (Orchestrators) | claude-opus-4-6 | Media | GPT-4o, Gemini 1.5 Pro |
| Modelo de ejecución (Specialists) | claude-sonnet-4-6 | Alta | GPT-4o-mini, Gemini 1.5 Flash |
| Modelo de tareas rápidas | claude-haiku-4-5 | Alta | GPT-4o-mini, Gemini Flash |
| Tool use / function calling | Claude API nativo | Alta | Compatible en todos los proveedores principales |
| Prompt caching | Claude API (Anthropic) | Baja | Sin equivalente directo en GPT-4 / Gemini |
| Ventana de contexto (200K) | Claude nativo | Media | GPT-4o (128K), Gemini 1.5 (1M) |

---

## 3. Capa de Abstracción — Patrón Recomendado

Cuando se construya un producto PIV/OAC con requisito de portabilidad explícito, encapsular la interacción LLM en una interfaz única:

```python
# Interfaz abstracta — independiente de proveedor
class LLMProvider(Protocol):
    def complete(
        self,
        messages: list[dict],
        model: str,
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        ...

# Implementación Claude (Anthropic SDK)
class ClaudeProvider:
    def complete(self, messages, model, tools=None, max_tokens=4096):
        client = anthropic.Anthropic()
        return client.messages.create(
            model=model, messages=messages, tools=tools or [],
            max_tokens=max_tokens
        )

# Implementación OpenAI (para migración / fallback)
class OpenAIProvider:
    def complete(self, messages, model, tools=None, max_tokens=4096):
        client = openai.OpenAI()
        return client.chat.completions.create(
            model=model, messages=messages,
            tools=tools or [], max_tokens=max_tokens
        )
```

**Punto de configuración único:**
```python
# config.py — un cambio migra todos los agentes
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "claude")  # "claude" | "openai" | "gemini"
MODEL_ORCHESTRATOR = os.getenv("MODEL_ORCHESTRATOR", "claude-opus-4-6")
MODEL_SPECIALIST = os.getenv("MODEL_SPECIALIST", "claude-sonnet-4-6")
```

---

## 4. Política de Fallback (sin migración completa)

Si el proveedor primario no está disponible (timeout, rate limit, outage):

| Nivel | Condición | Acción |
|---|---|---|
| L1 — Reintento | Timeout en llamada individual | Reintentar con backoff exponencial (1s, 2s, 4s) × 3 |
| L2 — Degradación | 3 reintentos fallidos en un agente | Emitir VETO_SATURACIÓN equivalente → escalar al orquestador padre |
| L3 — Pausa de sesión | Proveedor primario inoperativo >5 min | Master Orchestrator guarda estado en `.piv/active/` → notificar usuario → pausar sesión |
| L4 — Migración de emergencia | Usuario solicita continuar con proveedor alternativo | Instanciar LLMProvider alternativo → reanudar desde `.piv/active/` sin pérdida de estado |

---

## 5. Evaluación de Portabilidad (check pre-migración)

Antes de migrar de proveedor, el Master Orchestrator evalúa:

```
PORTABILITY CHECK:
  prompt_caching: ¿se usa? [SÍ/NO] — si SÍ, evaluar alternativa o eliminar
  tool_use_format: ¿es Claude-specific? [SÍ/NO] — verificar compatibilidad
  context_window: máximo usado en sesión = X tokens — ¿entra en destino?
  model_assignments: [lista de agentes] → [modelo destino propuesto]
  esfuerzo_estimado: BAJO (<1 día) | MEDIO (1-3 días) | ALTO (>3 días)
```

---

## 6. Restricciones

- Este skill no autoriza ningún cambio de proveedor — solo documenta el patrón y evalúa esfuerzo.
- Cambio de proveedor requiere confirmación humana explícita (Gate 3 equivalente).
- Las implementaciones de `LLMProvider` no se crean en el framework mismo — solo en productos derivados que lo requieran.
- Sin prompt caching en proveedores alternativos: evaluar impacto en costo antes de migrar.

---

## 7. Referencias Cruzadas

| Archivo | Relación |
|---|---|
| `CLAUDE.md` — Asignación de Modelo | Tabla de modelos actual (Claude) |
| `registry/agent_taxonomy.md` | Lista de agentes y sus modelos asignados |
| `skills/session-continuity.md` | Estado de sesión persiste en `.piv/active/` — portable entre proveedores |
| `metrics/schema.md` | Métricas de costo/tokens para evaluar impacto de migración |
