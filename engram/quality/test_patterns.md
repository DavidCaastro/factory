# Átomo: quality/test_patterns
> ACCESO: StandardsAgent, TestWriter (Specialist Agent)
> CROSS-IMPACT: quality/code_patterns
> Patrones de testing efectivos aprendidos en sesiones anteriores.

---

## Patrones de testing — Stack Python/FastAPI

**1. Verificar valores, no solo presencia de campos**
Un audit log entry con `user_id=None` pasa un test que solo verifique `"user_id" in entry`. Siempre verificar que los valores son significativos para el contexto del test.

**2. Cada fix de seguridad necesita su test negativo**
Para cada vulnerabilidad corregida, añadir el test que demuestra el vector de ataque bloqueado:
- Fix de rate limit por IP → test que envía N+1 requests y verifica 429
- Fix de audit log en fallo → test que verifica la entry con el evento correcto
- Fix de token revocado → test que verifica token inválido post-logout
- Fix de ownership → test que verifica que usuario B no puede modificar recurso de usuario A
- Fix de input limits → tests de boundary exacto (max, max+1, 0)

**3. Tests de boundary deben verificar ambos lados del límite**
- `len(field) = max_length` → debe aceptarse
- `len(field) = max_length + 1` → debe rechazarse con 422
- `len(field) = 0` si `min_length=1` → debe rechazarse con 422

**4. Rate limit tests deben alcanzar el límite real**
- Incorrecto: "usuario hace N-1 requests y todos pasan" (no verifica el límite real)
- Correcto: "usuario hace N requests (ok) + 1 más (429)"

**5. Tokens expirados — creación manual**
Crear con `jwt.encode(..., exp=time.time()-3600)`. NO depender del mock de tiempo ni esperar que expiren naturalmente.

**6. Filtrar el tipo de audit entry en tests**
Si el schema puede tener variantes (entrada con `user_id=None` vs. autenticado con `user_id` real), el test debe filtrar explícitamente el tipo de entry que quiere verificar.

**7. bcrypt >= 4.1 no silencia passwords > 72 bytes**
`max_length` en el schema Pydantic debe ser ≤ 72. Un `max_length=128` con bcrypt >= 4.1 causa HTTP 500.

**8. Separación de archivos de test por concern**
Crear archivos de test separados por dominio (ej. `test_security.py` para headers y validación de inputs). No sobrecargar un único archivo con concerns de capas distintas.

**9. ruff F401 en CI**
Eliminar `import pytest` en test files que no usan directamente fixtures de pytest. pytest no necesita ser importado explícitamente si solo se usan fixtures de conftest.
