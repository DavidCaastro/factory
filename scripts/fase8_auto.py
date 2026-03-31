#!/usr/bin/env python3
"""
fase8_auto.py — Generador automático de logs de cierre PIV/OAC FASE 8

Propósito: generar los archivos JSONL de logs_veracidad/<product-id>/ y la entrada
de metrics/sessions.md leyendo el estado de .piv/active/ y git log.
El AuditAgent revisa y aprueba el reporte — no escribe manualmente.

Uso:
    python scripts/fase8_auto.py --objective-id OBJ-003 --product-id framework-v4.0

# === COMANDOS REGISTRADOS DURANTE EJECUCIÓN OBJ-003 ===
# Creación de rama base:
#   git checkout -b directive/v4.0-base agent-configs
# Creación de staging:
#   git checkout -b staging directive/v4.0-base
# Creación de feature branches:
#   git checkout -b feature/T-01-specs directive/v4.0-base
#   git checkout -b feature/T-02-registry directive/v4.0-base
#   git checkout -b feature/T-03-skills-nuevos directive/v4.0-base
#   git checkout -b feature/T-06-logs-metrics directive/v4.0-base
#   git checkout -b feature/T-04-skills-update directive/v4.0-base
#   git checkout -b feature/T-05-protocolo-core directive/v4.0-base
#   git checkout -b feature/T-05-protocolo-core/exp-claude-md feature/T-05-protocolo-core
#   git checkout -b feature/T-05-protocolo-core/exp-agent-md feature/T-05-protocolo-core
#   git checkout -b feature/T-05-protocolo-core/exp-contracts feature/T-05-protocolo-core
#   git checkout -b feature/T-07-automatizacion directive/v4.0-base
#   git checkout -b feature/T-08-integracion directive/v4.0-base
# Merge de features a staging (Gate 2b aprobado):
#   git checkout staging && git merge --no-ff feature/T-01-specs -m "merge: T-01 specs redefinition → staging [Gate 2b APROBADO]"
#   git merge --no-ff feature/T-02-registry -m "merge: T-02 registry nuevos agentes → staging [Gate 2b APROBADO]"
#   git merge --no-ff feature/T-03-skills-nuevos -m "merge: T-03 skills nuevos → staging [Gate 2b APROBADO]"
#   git merge --no-ff feature/T-06-logs-metrics -m "merge: T-06 logs metrics → staging [Gate 2b APROBADO]"
#   git merge --no-ff feature/T-04-skills-update -m "merge: T-04 skills update → staging [Gate 2b APROBADO]"
#   git merge --no-ff feature/T-05-protocolo-core -m "merge: T-05 protocolo core → staging [Gate 2b APROBADO]"
#   git merge --no-ff feature/T-07-automatizacion -m "merge: T-07 automatizacion → staging [Gate 2b APROBADO]"
#   git merge --no-ff feature/T-08-integracion -m "merge: T-08 integracion validacion → staging [Gate 2b APROBADO]"
# Push de ramas:
#   git push origin directive/v4.0-base staging feature/T-01-specs feature/T-02-registry feature/T-03-skills-nuevos feature/T-04-skills-update feature/T-05-protocolo-core feature/T-06-logs-metrics feature/T-07-automatizacion feature/T-08-integracion
# Gate 3 (manual — requiere confirmación humana):
#   git checkout main && git merge --no-ff staging -m "release: PIV/OAC Framework v4.0 [Gate 3 APROBADO — confirmación humana]"
#   git push origin main
"""

import argparse
import json
import subprocess
import hashlib
from datetime import datetime, timezone
from pathlib import Path


def get_git_log(since_ref: str = None, format: str = "%H|%s|%ai|%an") -> list[dict]:
    cmd = ["git", "log", f"--pretty=format:{format}"]
    if since_ref:
        cmd.append(f"{since_ref}..HEAD")
    result = subprocess.run(cmd, capture_output=True, text=True)
    entries = []
    for line in result.stdout.strip().split("\n"):
        if "|" in line:
            parts = line.split("|", 3)
            entries.append({"hash": parts[0], "subject": parts[1], "date": parts[2], "author": parts[3]})
    return entries


def load_piv_state(objective_id: str) -> dict:
    state_file = Path(f".piv/active/{objective_id.replace('/', '-')}.json")
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {}


def generate_acciones_jsonl(objective_id: str, product_id: str, state: dict) -> list[dict]:
    events = []
    ts = datetime.now(timezone.utc).isoformat()
    events.append({
        "ts": ts, "session": objective_id, "agent": "AuditAgent",
        "event": "FASE8_CIERRE", "product_id": product_id,
        "result": state.get("status", "COMPLETADO")
    })
    for gate in state.get("gates_completed", []):
        events.append({
            "ts": ts, "session": objective_id, "agent": "GateEnforcer",
            "event": "GATE_VERDICT", "gate": gate, "verdict": "APROBADO"
        })
    return events


def generate_metrics_entry(objective_id: str, product_id: str, state: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    tasks_total = len(state.get("tasks", {}))
    tasks_done = len(state.get("tasks_completed", []))
    return f"""
### {objective_id} — {product_id}

| Campo | Valor |
|---|---|
| Fecha inicio | {state.get('created_at', 'N/D')} |
| Fecha cierre | {now} |
| execution_mode | {state.get('execution_mode', 'DEVELOPMENT')} |
| compliance_scope | {state.get('compliance_scope', 'MINIMAL')} |
| Resultado | {state.get('status', 'COMPLETADO')} |

#### Métricas de Entrega
| Métrica | Valor |
|---|---|
| Tareas completadas | {tasks_done}/{tasks_total} |
| Gate pass rate | Ver gates_completed en estado |

#### Métricas de Costo
| Campo | Valor |
|---|---|
| tokens_input | Ver ExecutionAuditReport |
| tokens_output | Ver ExecutionAuditReport |
| usd_actual | Ver ExecutionAuditReport |

---
"""


def write_jsonl_append(filepath: Path, events: list[dict]) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def compute_sha256(filepath: Path) -> str:
    if not filepath.exists():
        return "FILE_NOT_FOUND"
    content = filepath.read_bytes()
    return hashlib.sha256(content).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="PIV/OAC FASE 8 — Generador automático de logs de cierre")
    parser.add_argument("--objective-id", required=True, help="ID del objetivo (ej: OBJ-003)")
    parser.add_argument("--product-id", required=True, help="ID del producto para logs_veracidad/ (ej: framework-v4.0)")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar — no escribir")
    args = parser.parse_args()

    print(f"[FASE8_AUTO] Objetivo: {args.objective_id} | Producto: {args.product_id}")

    state = load_piv_state(args.objective_id)
    events = generate_acciones_jsonl(args.objective_id, args.product_id, state)
    metrics_entry = generate_metrics_entry(args.objective_id, args.product_id, state)

    log_dir = Path(f"logs_veracidad/{args.product_id}")
    acciones_file = log_dir / "acciones.jsonl"
    metrics_file = Path("metrics/sessions.md")

    if args.dry_run:
        print(f"[DRY-RUN] Escribiría {len(events)} eventos a {acciones_file}")
        print(f"[DRY-RUN] Añadiría entrada a {metrics_file}")
        return

    write_jsonl_append(acciones_file, events)
    print(f"[OK] {len(events)} eventos escritos en {acciones_file}")

    sha256 = compute_sha256(acciones_file)
    print(f"[OK] SHA-256 de acciones.jsonl: {sha256}")

    with open(metrics_file, "a", encoding="utf-8") as f:
        f.write(metrics_entry)
    print(f"[OK] Entrada añadida a {metrics_file}")
    print("[FASE8_AUTO] Completado. Revisar y aprobar con AuditAgent.")


if __name__ == "__main__":
    main()
