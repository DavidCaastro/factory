#!/usr/bin/env python3
"""
skill_manifest.py — Generador y verificador del manifest SHA-256 de skills

Propósito: calcular/actualizar los hashes SHA-256 de todos los skills en skills/
y actualizar skills/manifest.json. Operación completamente mecánica — sin LLM.

Uso:
    python scripts/skill_manifest.py --update    # Actualizar todos los hashes
    python scripts/skill_manifest.py --verify    # Verificar integridad
    python scripts/skill_manifest.py --verify --skill orchestration  # Verificar uno
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_PATH = Path("skills/manifest.json")
SKILLS_DIR = Path("skills")


def compute_sha256(filepath: Path) -> str:
    content = filepath.read_text(encoding="utf-8")
    return hashlib.sha256(content.encode()).hexdigest()


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"version": "1.0", "skills": {}}
    return json.loads(MANIFEST_PATH.read_text())


def save_manifest(manifest: dict) -> None:
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))


def update_all(manifest: dict) -> int:
    updated = 0
    for skill_file in sorted(SKILLS_DIR.glob("*.md")):
        skill_name = skill_file.stem
        sha256 = compute_sha256(skill_file)
        manifest.setdefault("skills", {})[skill_name] = {
            "path": str(skill_file),
            "sha256": sha256,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "gate_verified": manifest.get("skills", {}).get(skill_name, {}).get("gate_verified", False)
        }
        updated += 1
    return updated


def verify_all(manifest: dict, skill_filter: str = None) -> list[dict]:
    errors = []
    skills = manifest.get("skills", {})
    for skill_name, entry in skills.items():
        if skill_filter and skill_name != skill_filter:
            continue
        skill_path = Path(entry["path"])
        if not skill_path.exists():
            errors.append({"skill": skill_name, "error": "FILE_NOT_FOUND"})
            continue
        actual = compute_sha256(skill_path)
        if actual != entry["sha256"]:
            errors.append({
                "skill": skill_name,
                "error": "HASH_MISMATCH",
                "expected": entry["sha256"][:16] + "...",
                "actual": actual[:16] + "..."
            })
    return errors


def main():
    parser = argparse.ArgumentParser(description="PIV/OAC Skills Manifest — SHA-256 manager")
    parser.add_argument("--update", action="store_true", help="Actualizar todos los hashes")
    parser.add_argument("--verify", action="store_true", help="Verificar integridad")
    parser.add_argument("--skill", help="Filtrar por nombre de skill")
    args = parser.parse_args()

    manifest = load_manifest()

    if args.update:
        count = update_all(manifest)
        save_manifest(manifest)
        print(f"[OK] {count} skills actualizados en {MANIFEST_PATH}")

    if args.verify:
        errors = verify_all(manifest, args.skill)
        if not errors:
            print(f"[OK] Todos los skills verificados — integridad correcta")
        else:
            print(f"[ERROR] {len(errors)} skills con problemas de integridad:")
            for e in errors:
                print(f"  - {e['skill']}: {e['error']}")
            sys.exit(1)

    if not args.update and not args.verify:
        parser.print_help()


if __name__ == "__main__":
    main()
