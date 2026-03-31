# Spec Frontmatter Validation System

## What Is This?

Every spec Markdown file in `specs/` (functional, architecture, quality, security, compliance) carries a YAML frontmatter block at the top of the file. This frontmatter is the machine-readable contract that agents and the MasterOrchestrator use to verify spec completeness before building the task DAG.

This directory (`specs/schemas/`) contains one JSON Schema (draft-07) per spec file. The script `tools/validate-specs.py` extracts each frontmatter block and validates it against the corresponding schema.

**Rule:** The MasterOrchestrator MUST run `tools/validate-specs.py` and receive an all-pass result before constructing the DAG for any objective. A single schema validation failure blocks DAG construction.

---

## How to Add Frontmatter to a Spec

Place a YAML frontmatter block between `---` delimiters at the very top of the Markdown file — before any other content.

```markdown
---
spec_name: functional
version: 1.0.0
status: DRAFT
project_name: My Project
rf_count: 5
rfs_completed: 0
coverage_target: 80
---

# Especificaciones Funcionales — My Project
...
```

The frontmatter must come before the first heading. Do not place any content above the opening `---`.

---

## Valid Frontmatter Examples

### functional.md

```yaml
---
spec_name: functional
version: 1.0.0
status: ACTIVE
project_name: Inventory API
rf_count: 12
rfs_completed: 9
coverage_target: 90
budget_max_usd: 5000
validated: true
validated_at: "2026-03-17T10:00:00Z"
---
```

Required fields: `spec_name`, `version`, `status`, `project_name`, `rf_count` (integer >= 1), `rfs_completed` (integer >= 0), `coverage_target` (0–100).
Optional fields: `budget_max_usd`, `validated`, `validated_at`.

---

### architecture.md

```yaml
---
spec_name: architecture
version: 1.0.0
status: ACTIVE
stack_components:
  - name: API Server
    technology: FastAPI
    version_min: "0.110"
  - name: Database
    technology: PostgreSQL
    version_min: "14.0"
  - name: Runtime
    technology: Python
    version_min: "3.11"
layer_count: 3
dag_tasks: 8
validated: true
validated_at: "2026-03-17T10:00:00Z"
---
```

Required fields: `spec_name`, `version`, `status`, `stack_components` (array of `{name, technology, version_min}`, min 1 item), `layer_count` (integer >= 2), `dag_tasks` (integer >= 1).
Optional fields: `validated`, `validated_at`.

---

### quality.md

```yaml
---
spec_name: quality
version: 1.0.0
status: ACTIVE
coverage_gate: 90
lint_gate: ruff
test_framework: pytest
sca_tool: pip-audit
validated: true
validated_at: "2026-03-17T10:00:00Z"
---
```

Required fields: `spec_name`, `version`, `status`, `coverage_gate` (0–100), `lint_gate` (one of: `ruff`, `flake8`, `eslint`), `test_framework`.
Optional fields: `sca_tool`, `validated`, `validated_at`.

---

### security.md

```yaml
---
spec_name: security
version: 1.0.0
status: ACTIVE
threat_model: STRIDE
owasp_top10_reviewed: true
secrets_in_code_allowed: false
pentest_required: false
validated: true
validated_at: "2026-03-17T10:00:00Z"
---
```

Required fields: `spec_name`, `version`, `status`, `threat_model` (non-empty string), `owasp_top10_reviewed` (boolean), `secrets_in_code_allowed` (**must always be `false`**).
Optional fields: `pentest_required`, `validated`, `validated_at`.

Note: `secrets_in_code_allowed: true` is a hard schema violation. The validator will reject the spec and block DAG construction.

---

### compliance.md

```yaml
---
spec_name: compliance
version: 1.0.0
status: ACTIVE
compliance_scope: FULL
regulations:
  - GDPR
  - OWASP-API-2023
validated: true
validated_at: "2026-03-17T10:00:00Z"
---
```

Required fields: `spec_name`, `version`, `status`, `compliance_scope` (one of: `FULL`, `MINIMAL`, `NONE`), `regulations` (array, may be empty).
Optional fields: `validated`, `validated_at`.

---

## Running the Validation

```bash
python tools/validate-specs.py
```

The script will:
1. Scan `specs/*.md` (excluding `specs/_templates/`).
2. Extract the YAML frontmatter from each file.
3. Look up the corresponding schema in `specs/schemas/<spec_name>.schema.json` using the `spec_name` field from the frontmatter.
4. Validate using `jsonschema` (draft-07).
5. Print a per-spec PASS / FAIL report and exit with code `0` (all pass) or `1` (any failure).

Prerequisites:

```bash
pip install jsonschema pyyaml
```

---

## MasterOrchestrator Integration

The MasterOrchestrator MUST call `tools/validate-specs.py` as the first step of DAG construction (before any task is scheduled). The required sequence is:

1. Run `python tools/validate-specs.py` — exit code must be `0`.
2. If any spec fails validation, halt DAG construction and surface the error to the user for resolution.
3. Only after all specs pass validation proceed with building the task DAG.

This ensures that agent-contracts (written by G-07) always bind to a validated, schema-consistent spec state. The `validated` and `validated_at` fields in each frontmatter are written back by the script on success, providing an auditable timestamp of the last known-good validation.

---

## Schema Compatibility with Agent Contracts

These schemas are designed to be compatible with the agent-contract fields defined by G-07. Every schema exposes the following shared fields that agent contracts may reference:

| Field | Type | Used by contracts |
|---|---|---|
| `spec_name` | string | contract identifier binding |
| `version` | semver string | version pinning |
| `status` | DRAFT / ACTIVE / DEPRECATED | activation guard |
| `validated` | boolean | pre-flight check |
| `validated_at` | ISO 8601 string | audit trail |
