# ADR-002 — Engram: memoria estructural por dominio vs. vector store unificado

**Estado:** Aceptado | **Fecha:** 2026-03-23 | **Autor:** PIV/OAC Framework

---

## Contexto

Los frameworks de agentes con persistencia usan principalmente **vector stores** (ChromaDB, Pinecone, pgvector) con búsqueda semántica para recuperar contexto relevante. La alternativa es un sistema de archivos Markdown estructurado con frontmatter y acceso determinista por ruta.

---

## Decisión

Se eligió **Engram: archivos Markdown estructurados por dominio** con acceso determinista y escritura exclusiva por agente.

Estructura canónica:
```
engram/
├── core/          ← Master + Domain Orchestrators
├── audit/         ← AuditAgent exclusivo
├── security/      ← SecurityAgent exclusivo
├── coherence/     ← CoherenceAgent
├── quality/       ← StandardsAgent
├── domains/       ← conocimiento de dominio del proyecto
└── precedents/    ← solo post-Gate 3 (estado VALIDADO)
```

---

## Razones

1. **Zero-Trust Metodológico sobre la memoria:** un SecurityAgent no debería acceder al contexto de coherencia y viceversa. Con archivos separados por dominio, el protocolo puede declarar "SecurityAgent solo lee `engram/security/`" y es verificable mediante grep en los registry files.

2. **Integridad verificable:** cada átomo del engram es un archivo de texto versionado en git. SHA-256 registrado en `engram/audit/gate_decisions.md`. Un vector store requiere infraestructura adicional para garantizar la misma integridad.

3. **Sin costo operativo:** Chroma/Pinecone añaden una dependencia de infraestructura. El engram solo requiere git — ya presente en cualquier proyecto que use el framework.

4. **Lazy loading compatible:** el protocolo de carga perezosa es más fácil de implementar con rutas de archivo conocidas que con queries de embeddings.

5. **Precedentes con estado de validación:** la distinción `REGISTRADO` / `VALIDADO` (solo post-Gate 3) es un estado de workflow que los vector stores no modelan nativamente.

---

## Consecuencias

- Los átomos del engram son texto legible por humanos — facilitando auditorías manuales.
- La búsqueda semántica dentro del engram no está disponible — solo acceso estructurado por ruta.
- Si el engram crece mucho (> 1000 entradas por átomo), la carga completa del archivo puede volverse costosa. Mitigación: índices en `engram/INDEX.md` y lazy loading por sección.
- El engram no es apropiado para memoria de alta frecuencia de escritura (>100 updates/sesión). Para ese caso se usa `.piv/active/` como estado de sesión.

---

## Alternativas consideradas y descartadas

**Vector store (descartado):** bueno para búsqueda semántica difusa, pero sin control de acceso por dominio, sin integridad verificable en git, y con overhead operativo. Elegido por Semantic Kernel (Azure AI Search) y CrewAI (ChromaDB).

**Base de datos relacional (descartado):** mayor fidelidad para consultas complejas, pero rompe el principio de "solo git" y dificulta la portabilidad entre entornos.
