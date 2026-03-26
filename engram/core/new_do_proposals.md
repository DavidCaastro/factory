---
name: new DO type proposals
description: Domain Orchestrator types proposed by MasterOrchestrator during piv-challenge C-1..C-5 stimulation scenarios
type: project
domain: core
source: piv-challenge OBJ-001, scenarios C-1..C-5
date: 2026-03-16
status: PROPUESTO — requiere gate de StandardsAgent + SecurityAgent + confirmación humana para añadir a registry/
---

# Propuestas de Nuevos Domain Orchestrators

> Estas propuestas son evidencia del gap analysis de piv-challenge.
> Para añadirlas oficialmente al catálogo de registry/:
> 1. StandardsAgent redacta el `registry/<nombre>.md` completo
> 2. SecurityAgent revisa la propuesta
> 3. Confirmación humana explícita → merge a agent-configs

---

## MLOrchestrator

**Origen:** C-1 (AI Analytics Pipeline), C-3 (Fraud Detection)

**Responsabilidad propuesta:**
- Coordinar tareas de entrenamiento de modelos ML (scikit-learn, XGBoost, PyTorch)
- Gestionar feature stores compartidos entre entrenamiento y serving
- Supervisar ciclos de reentrenamiento automático (drift detection, accuracy thresholds)
- Coordinar experimentos de A/B testing y comparación de modelos
- Interfaz con MLflow, Weights & Biases u otros experiment trackers

**Justificación del gap:**
El catálogo actual de DOs no contempla la dualidad `train/serve` ni el estado
mutable de un modelo ML a lo largo del tiempo. Un HarnessDO o ValidatorDO no
puede gestionar re-entrenamientos periódicos con criterios estadísticos.

---

## InfraOrchestrator

**Origen:** C-2 (SaaS Multi-tenant + GDPR), C-4 (Monolith Migration)

**Responsabilidad propuesta:**
- Gestionar provisioning de infraestructura (IaC: Terraform, Pulumi)
- Coordinar migraciones de base de datos zero-downtime
- Supervisar despliegues multi-región con restricciones de residencia de datos
- Gestionar configuración de reverse proxies, service mesh, load balancers
- Verificar SLAs de disponibilidad durante migraciones

**Justificación del gap:**
Las tareas de infraestructura tienen un ciclo de vida distinto al código de aplicación
(idempotencia, state drift, blast radius elevado). Requieren gates específicos que
los DOs de aplicación no contemplan (plan → apply → verify).

---

## DataOrchestrator

**Origen:** C-1 (Analytics), C-4 (Monolith Migration)

**Responsabilidad propuesta:**
- Coordinar pipelines ETL/ELT complejos
- Gestionar schemas y migraciones de datos
- Supervisar consistencia en sistemas distribuidos (eventual consistency, CQRS)
- Coordinar estrategias Strangler Fig para extracción de dominios de datos

---

## MetaOrchestrator

**Origen:** C-5 (Autonomous CI/CD con gates de IA)

**Responsabilidad propuesta:**
- Gestionar objetivos donde el framework PIV/OAC orquesta su propio proceso
- Coordinar escenarios donde los agentes son tanto los ejecutores como el objeto de trabajo
- Supervisar la coherencia del framework en ciclos de auto-mejora
- Detectar y prevenir recursión infinita en meta-objetivos

**Justificación del gap:**
C-5 es el meta-caso más complejo: el framework construye un sistema que usa IA como
quality gates. Ningún DO existente contempla la gestión de un sistema que sea
instancia del mismo framework que lo construye.

---

## StreamingOrchestrator

**Origen:** C-3 (Fraud Detection en tiempo real)

**Responsabilidad propuesta:**
- Gestionar pipelines de datos en tiempo real (Kafka, Flink, Spark Streaming)
- Coordinar backpressure, checkpointing y recovery en streams
- Supervisar latencia end-to-end en pipelines de decisión en tiempo real

---

## Próximos pasos

Para cada propuesta, crear `registry/<nombre>_orchestrator.md` siguiendo la plantilla
de `registry/domain_orchestrator.md` y hacer pasar por:
1. StandardsAgent review
2. SecurityAgent review
3. Confirmación humana → merge
