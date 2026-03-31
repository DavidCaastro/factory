# SKILL: Estándares de Calidad — PIV/OAC v3.2
> Cargado por: StandardsAgent en Gate 2
> Custodio: StandardsAgent (propone cambios al cierre, con gate SecurityAgent + confirmación humana)
> Este archivo define los umbrales y convenciones que todo código debe cumplir para alcanzar grado de entrega para producción.

---

## Umbrales de Cobertura de Tests

| Tipo de módulo | Cobertura mínima requerida |
|---|---|
| Flujos críticos (autenticación, pagos, datos sensibles) | 100% de líneas + ramas |
| Lógica de negocio principal | ≥ 90% |
| Utilidades y helpers | ≥ 80% |
| Configuración y bootstrapping | ≥ 70% |

**Herramienta requerida:** `pytest-cov` con reporte en formato XML o terminal. No se acepta estimación manual.

**Cobertura no es suficiencia:** Alcanzar el umbral es necesario pero no suficiente. Los tests deben cubrir casos límite y rutas de error, no solo el happy path.

---

## Estándares de Documentación

### Funciones y métodos
```python
def nombre_funcion(param1: tipo, param2: tipo) -> tipo_retorno:
    """
    Descripción concisa de qué hace la función.

    Args:
        param1: Descripción del parámetro.
        param2: Descripción del parámetro.

    Returns:
        Descripción del valor retornado.

    Raises:
        NombreExcepcion: Condición bajo la cual se lanza.
    """
```

### Clases
```python
class NombreClase:
    """
    Descripción del propósito de la clase.

    Attributes:
        atributo: Descripción del atributo público.
    """
```

### Cuándo no se requiere docstring
- Funciones con nombre completamente autoexplicativo y sin lógica no obvia (e.g., `get_user_by_id`)
- Métodos `__repr__`, `__str__`, `__eq__` con implementación estándar
- Tests (los nombres de test son la documentación)

---

## Convenciones de Código Python

### Naming
- Módulos y paquetes: `snake_case`
- Clases: `PascalCase`
- Funciones, métodos, variables: `snake_case`
- Constantes: `UPPER_SNAKE_CASE`
- Variables privadas de instancia: `_prefijo_snake_case`

### Complejidad
- Complejidad ciclomática máxima por función: **10**
- Longitud máxima de función: **50 líneas** (excluye docstring)
- Longitud máxima de línea: **100 caracteres**
- Máximo de parámetros por función: **5** (usar dataclass o schema si se necesitan más)

### Calidad
- **DRY:** Lógica duplicada en ≥ 2 lugares → extraer a función/clase
- **SRP:** Cada función hace exactamente una cosa
- **Sin magic numbers:** Usar constantes nombradas
- **Sin imports circulares:** Revisar dependencias entre módulos

---

## Estándares de Tests

### Estructura de un test
```python
def test_<nombre_funcionalidad>_<escenario>_<resultado_esperado>():
    # Arrange
    # preparar datos y dependencias

    # Act
    # ejecutar la funcionalidad bajo test

    # Assert
    # verificar el resultado esperado
```

### Qué debe tener cada suite de tests
1. **Happy path:** El caso de uso principal funciona correctamente
2. **Casos límite:** Valores en los bordes del dominio (0, -1, None, string vacío, lista vacía)
3. **Rutas de error:** Qué pasa cuando los inputs son inválidos o las dependencias fallan
4. **Tests de integración:** Para flujos que cruzan capas (transport → domain → data)

### Tests de seguridad obligatorios (cuando aplica)
- Autenticación: intentos con token inválido, expirado, manipulado
- Autorización: acceso a recursos de otro usuario
- Inputs: inyección SQL, XSS, valores fuera de rango
- Timing: endpoints de login deben tomar tiempo similar si usuario existe o no

---

## Estándares de Estructura de Proyecto (Python/FastAPI)

```
proyecto/
├── app/
│   ├── __init__.py
│   ├── main.py               ← solo bootstrapping
│   ├── api/                  ← capa de transporte (rutas, schemas Pydantic)
│   │   └── v1/
│   ├── domain/               ← lógica de negocio (pura, sin frameworks)
│   ├── infrastructure/       ← adaptadores (DB, caché, servicios externos)
│   └── core/                 ← configuración, constantes, excepciones base
├── tests/
│   ├── unit/                 ← tests de domain/ sin dependencias externas
│   ├── integration/          ← tests de api/ con DB real (no mock)
│   └── conftest.py           ← fixtures compartidos
├── .env.example              ← variables de entorno documentadas (sin valores reales)
└── requirements.txt / pyproject.toml
```

---

## Atomización de Archivos del Framework (FASE 8)

El StandardsAgent verifica esta regla sobre **archivos del framework modificados en la sesión** (registry/, skills/, specs/, agent.md, CLAUDE.md). No aplica a código de producto.

```
PARA CADA archivo de framework modificado en la sesión:
  1. Contar líneas actuales del archivo
  2. Si líneas > 500 → evaluar los 3 criterios:
       [ ] Carga independiente: distintos agentes cargan distintas secciones
       [ ] Ciclo de actualización distinto: hay secciones estables y secciones volátiles
       [ ] Responsabilidad mixta: el archivo sirve más de un rol distinto
  3. Si ≥ 2 criterios se cumplen → generar propuesta de atomización
  4. Si < 2 criterios → registrar en reporte como "revisado, no requiere atomización"
```

**Exenciones — no evaluar aunque superen 500 líneas:**
- `agent.md` — protocolo maestro, siempre leído completo por el Master Orchestrator
- `logs_veracidad/*` — logs append-only; su atomización es el separador de sesión

**Formato de propuesta de atomización:**
```markdown
## Propuesta de Atomización — StandardsAgent [FECHA]
Archivo: <ruta>
Líneas actuales: <n>
Criterios cumplidos: <lista>
División propuesta:
  <archivo-nuevo-1>: <secciones que contiene> — cargado por: <agente(s)>
  <archivo-nuevo-2>: <secciones que contiene> — cargado por: <agente(s)>
Beneficio esperado: <ahorro de contexto estimado por agente>
```

La propuesta sigue el mismo gate que las propuestas de skills: SecurityAgent revisa + confirmación humana explícita antes de aplicar.

---

## Definition of Done (DoD) — Fuente de Verdad Canónica

> Esta sección es el source of truth único del DoD para el framework PIV/OAC. Referencias en otros archivos apuntan aquí.

### DoD para modo DEVELOPMENT (Gate 2 + Gate 3)

```
Una tarea de desarrollo se considera COMPLETADA cuando:
[ ] Tests pasan con cobertura ≥ umbrales de la tabla de esta skill
[ ] Herramienta pytest-cov ejecutó sin error y produjo reporte
[ ] ruff reporta 0 errores (no warnings — errores)
[ ] Toda función/clase pública tiene docstring o nombre completamente autoexplicativo
[ ] Sin código muerto ni imports sin usar
[ ] Documentación de API actualizada si la tarea expone endpoints
[ ] PR / rama de tarea sin conflictos de merge con staging
```

### DoD para modo RESEARCH (Gate 2 epistémico)

```
Una tarea de investigación se considera COMPLETADA cuando:
[ ] Todas las RQs en estado RESUELTA o IRRESOLVABLE (con razón documentada)
[ ] Cada afirmación central respaldada por ≥1 fuente TIER-1 o TIER-2
[ ] Sección de Limitaciones presente y honesta
[ ] Nivel de confianza (ALTA/MEDIA/BAJA) declarado por hallazgo
```

### DoD de Framework (MODO_META_ACTIVO — Gate 2)

```
Ver skills/framework-quality.md — equivalentes deterministas para checks de producto:
  cross-reference integrity  ≡  cobertura de tests
  structural completeness    ≡  linting
  protocol integrity         ≡  pip-audit
  no placeholders            ≡  Definition of Done de producto
```

---

## Checklist de Entrega Pre-Producción

Antes de Gate 3 (staging → main), además de lo anterior:

```
[ ] .env.example actualizado con todas las variables requeridas
[ ] requirements.txt / pyproject.toml actualizado y consistente
[ ] Sin archivos .env, *.pem, *.key en el repositorio
[ ] Migraciones de DB incluidas si hay cambios de esquema
[ ] CHANGELOG o equivalente actualizado
[ ] Sin TODOs críticos sin ticket asociado
[ ] Docker/compose funcional si el proyecto lo usa
```

## Referencia a Rubric de Evaluación

La medición de calidad 0-1 por dimensión está definida en `contracts/evaluation.md`.
Los umbrales de aprobación en `specs/active/quality.md` (por proyecto) deben estar
alineados con los pesos de FUNC/QUAL de contracts/evaluation.md.
