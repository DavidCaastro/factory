# CHANGELOG — PIV/OAC

> Generado automáticamente por `scripts/generate_changelog.py`.
> Basado en commits con formato [Conventional Commits](https://www.conventionalcommits.org/).
> Última actualización: 2026-03-23

---

## March 2026

### Nuevas funcionalidades

- **framework**: evaluaciÃ³n competitiva, justificaciÃ³n, ADRs, production-readiness skill (`3f0f42ba`)
- **sdk**: Sprint 2 â€” CheckpointValidator, ResearchOrchestrator, piv status, API docs (`6f5e02e1`)
- **sdk**: OBJ-003 Sprint 1 â€” CLI + EvaluationAgent + Gate 2b CI (`c055e33a`)
- **flows**: T6 â€” aÃ±adir FASE 5b/5c, EvaluationAgent y registro de precedentes a flujos visuales (`edf1843d`)
- **registry**: T2 â€” split security_auditor.md into security_agent.md + audit_agent.md + evaluation_agent.md (`9ff90edc`)
- **framework**: T3 â€” thin CLAUDE.md + Â§19 EvaluationAgent + FASE 5b/5c/8b + contracts/ en LAYERS (`226706b4`)
- **framework**: T4 â€” skills/evaluation.md + engram/precedents/ + cross-updates (`2c3d01bf`)
- **metrics**: T5 â€” logs_scores/ audit trail + evaluation metrics schema + precedents schema (`85cf8859`)
- **framework**: T1 â€” crear contracts/ con primitivas canÃ³nicas del framework PIV/OAC v3.2 (`b3774e4a`)
- **sdk**: Jaeger UI + trazas padre-hijo para demo de telemetrÃ­a (`a087409a`)
- **sdk**: Bloque 1 â€” cobertura completa, mypy, docs y CHANGELOG (`5983c196`)
- **sdk**: Phase 2 â€” DAG validator, AgentBase timeouts, docs (`f5a8d5a0`)
- Fase 1 estabilizaciÃ³n â€” agentes completos + checkpoint + tests + README (`97629910`)
- portable environment â€” Bash(*) permissions + bootstrap auto-detection (`3db013d7`)
- **framework**: INIT protocol + specs template/active separation (`9a281575`)
- **P1-C/D/F/G**: framework hardening â€” rollback, canonicity, intent re-validation, model abstraction (`bb8bdad5`)
- **OBJ-13**: add Session Continuity Protocol (skills/session-continuity.md) (`20d17cd2`)
- **OBJ-12**: formalize monitor_diff protocol in coherence_agent.md (`84a68879`)
- **OBJ-11**: add framework metrics schema section (`602f527d`)
- **OBJ-08**: complete CLAUDE.md structure listing (`ad4e1788`)
- **OBJ-06+OBJ-07**: CLAUDE.md coherence + Modo Meta formalization (`57772ef5`)
- **OBJ-06**: add registry/research_orchestrator.md + CLAUDE.md coherence (`95bd1515`)
- **OBJ-05**: generalize engram/domains â€” remove auth-service POC data (`ddf53e08`)
- **OBJ-02+OBJ-03b**: INIT mode in INDEX + Gate 3 Recordatorio rule (`793b81ea`)
- **OBJ-04**: add registry/domain_orchestrator.md â€” formal DO registration (`96923146`)
- **OBJ-03a**: add intent_rejections.jsonl log + FASE 0 instruction (`dcd8ce8e`)
- **OBJ-02**: add execution_mode INIT â€” bootstrap protocol for new projects (`9a96fc29`)
- **OBJ-01**: add LAYERS.md layer separation contract and MIT license (`7626ea85`)

### Correcciones

- **framework**: corregir 27 hallazgos de auditorÃ­a â€” coherencia, bucles, redundancias (`a46677d6`)
- **tests**: patch Resource en test_telemetry_otel â€” falla en CI sin OTel instalado (`5b09d8d5`)
- **ci**: corregir gate-2b-sdk y pip-audit en piv-gate-framework.yml (`0058af17`)
- **sdk**: CoherenceAgent.invoke() + service.name en OTel Resource (`1979df6a`)
- consolidate duplicate CI workflows + fix scan-secrets false positive (`3cf66d01`)
- add Bash pre-approval patterns + Contexto de Rama rule for subagents (`76749678`)
- replace LLM-inferrable compliance conditions with deterministic lookup tables (`b26236ff`)
- **P0-B**: add inline JSON schema fields to session-continuity.md Â§1 (`139438a7`)
- **OBJ-12**: add Restricciones + Referencias Cruzadas to coherence_agent.md (`1e5a89ef`)
- **OBJ-01**: correct engram/projects/ â†’ engram/domains/ in LAYERS.md (`185c9275`)

### Refactorizaciones

- **framework**: purge artifact contamination + enforce directive/artifact separation (`b9532690`)
- **OBJ-09**: generalize skills/backend-security.md header (`a824a7e7`)
- **OBJ-07**: replace Modo Meta exemptions with Framework Quality Gate (`699ccd8f`)

### Documentación

- **CLAUDE.md**: add model-abstraction.md to skills directory listing (`78c40bf4`)

### Tests

- cubrir client, EngramStore y telemetry â€” alcanzar coverage â‰¥80% (`eb094fa3`)

### Tareas internas

- **OBJ-10**: truncate engram/session_learning.md to DEPRECATED stub (`37dc2db4`)

### Otros cambios

- audit(fase8): cierre OBJ-002 â€” PIV/OAC v3.3 redesign (`2ed234ad`)
- engram(coherence): registrar conflictos de sesiÃ³n 2026-03-22 â€” redesign PIV/OAC v3.3 (`640d81af`)
- engram: OBJ-001 learnings â€” control agent timing + context checkpoints + artifact push (`1ac79758`)
- Add validate-specs.py tool and Level 2 tutorial walkthrough (`e7f02c26`)
- Improve sdk/README with full API reference; add Prometheus alert rules (`5a4b114f`)
- Close OBJ-001 formally + integrate OTel agent_span in AgentBase.invoke() (`e55e58cb`)
- Fix CI Quality Gate checks â€” resolve all 4 false positives (`37b8f910`)
- Add PyPI publish workflow â€” manual dispatch + sdk-v*.*.* tag trigger, dry-run mode (`96fe1057`)
- Fix CI workflow: python3 setup, word-boundary secret patterns, add SDK venv gate (`c6feab84`)
- Fix telemetry __init__ import path â€” relative package import instead of absolute sdk.piv_oac (`33409036`)
- G-01: Add piv-oac SDK skeleton â€” installable Python package with agent contracts, engram store, exceptions (`98204b75`)
- G-09: Add multi-provider abstraction â€” LLMClient protocol, Anthropic/OpenAI/Ollama implementations, provider model map (`069ab06c`)
- G-02: Add observability protocol â€” OpenTelemetry traces/metrics/logs, dashboard panels, alerts, SDK tracer module (`a621f433`)
- G-03: Add fault recovery protocol â€” retry/backoff, model fallback, checkpoint, WORKTREE_CONFLICT, GATE_DEADLOCK (`d8f261c9`)
- G-12: Add CI/CD native â€” GitHub Actions piv-gate-framework.yml with 5 blocking gates (`2acc262f`)
- G-06: Add JSON schemas for spec validation â€” 5 schemas + frontmatter validation system (`0d072a3d`)
- G-07: Add agent interface contracts â€” structured output schemas, canonical field names, parsing protocol (`ca264e57`)
- G-07: Add agent interface contracts â€” structured output schemas, canonical field names, parsing protocol (`66358fef`)
- G-11: Add cost metrics schema â€” USD/RF benchmarks, model distribution, sessions.md template extension (`7a770b69`)
- G-10: Add worktree automation â€” naming convention, lifecycle protocol, bash script (`04ba1a79`)
- G-08: Add external onboarding guide â€” prerequisites, quick start, key concepts, FAQ (`b5310d93`)
- G-05: Add engram versioning â€” SHA-256 integrity, snapshots, rollback protocol (`f45e3452`)
- G-04: Add cost-control protocol â€” rate limiting, budget per objective, VETO_SATURACIÃ“N por costo (`aaeae51f`)
- V-6 completado: 2 objetivos paralelos sin conflictos (`26118bfd`)
- OBJ-003: Document 5 new DO type proposals from piv-challenge C-1..C-5 (`62c7db92`)
- OBJ-002: Add piv-challenge cycle learnings engram atom (`7198bc28`)
- V-3..V-7: Update ROADMAP and metrics after piv-challenge cycle (`8d824b12`)
- Fix validate_env.py: encoding + pytest-cov detection (`16872cb1`)
- Complete Phase 3: engram bootstrap, Gate 3 reminder protocol, AuditAgent FASE 8 contingency, Mermaid sync (`58c4e71a`)
- Phase 2: resolve all 13 coherence gaps (M-1â†’M-7, B-1â†’B-7) (`ec6dbe3e`)
- Phase 1: resolve C-2, M-8, A-1 â€” context protocol + MODO_META detection (`1916c742`)
- Add production roadmap with audit scores and gap tracking (`27a89700`)
- Add PIV/OAC acronym definitions to CLAUDE.md and agent.md (`4ac985e5`)
- Fix 9 logical process weaknesses found in coherence audit (`8fe99148`)
- Fix 9 framework issues found in deep semantic audit (`d93338c6`)
- Add docs/flows/ â€” 13 Mermaid flowcharts covering all PIV/OAC v3.2 processes (`0c193ab3`)
- Fix loose ends: replace deprecated refs + complete registry structure (`69826e69`)
- Separate framework CI from product CI (changes A + B) (`d0063779`)
- Remove contamination + parametrize tool commands (changes C, D, E, F) (`6cead81e`)
- Fix 10 gray zones: replace LLM-inferrable decisions with deterministic rules (`c418ee84`)
- Fix unclosed code block in coherence_agent.md Â§11 InvocaciÃ³n (`786c09cc`)
- Reset specs/ to templates and remove project-specific runtime artifacts (`b8e5c744`)
- Implement production readiness improvements â€” reach â‰¥95% coverage + infrastructure layer (`8cd8f1f4`)
- Fix residual ruff attribution in metrics sources (`a5a30056`)
- Fix 8 congruence/coherence issues (PIV/OAC v3.2 procedural hardening) (`ceebacf1`)
- Fix 5 framework weaknesses identified in comparative quality analysis (`ca0c3513`)
- Add conditional atomization rule for framework files >500 lines (`1eb0820c`)
- Add INVESTIGACIÃ“N_REQUERIDA state alongside BLOQUEADA_POR_DISEÃ‘O (`0007e359`)
- Fix 5 ambiguities from research mode extension (PIV/OAC v3.2) (`1ec0d6e7`)
- Add research mode support (PIV/OAC v3.2): execution_mode + EpistemicAgent (`d7557bd0`)
- Atomize project_spec: replace monolith with 6-module specs/ directory (v3.2) (`a7c5078d`)
- Add TechSpecSheet: dual-column technical specification table as mandatory deliverable (`dbf3dc96`)
- Fill 3 gaps identified from synthesis review (v3.2) (`5ce4d1de`)
- Atomize Engram: replace monolith with role-scoped memory network (v3.2) (`95bb8901`)
- Add granular parallelism model and recursive agent fragmentation (v3.2) (`eb7b6487`)
- Upgrade PIV/OAC framework to v3.2: StandardsAgent, ComplianceAgent, Zero-Trust metodolÃ³gico (`54513751`)
- Add full project: PIV/OAC framework + Mini Platform API (`b44581f4`)
- Initialize main branch (`12d98f30`)

---
