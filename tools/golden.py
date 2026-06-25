#!/usr/bin/env python3
"""Golden fixture management for PipeSpec -> OrchSpec outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from orchspec_validator import CompileOptions, compile_pipespec_to_orchspec


ROOT = Path(__file__).resolve().parents[1]
PIPESPEC_DIR = ROOT / "spec" / "examples" / "pipespec"
GOLDEN_DIR = ROOT / "tests" / "fixtures" / "golden"


def _render_compiled(path: Path) -> str:
    pipespec = json.loads(path.read_text(encoding="utf-8"))
    compiled = compile_pipespec_to_orchspec(pipespec, options=CompileOptions(strict=True))
    return json.dumps(compiled, indent=2, sort_keys=True) + "\n"


def update_golden() -> int:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for pipespec_path in sorted(PIPESPEC_DIR.glob("*.json")):
        rendered = _render_compiled(pipespec_path)
        golden_name = pipespec_path.name.replace(".json", ".orchspec.json")
        golden_path = GOLDEN_DIR / golden_name
        golden_path.write_text(rendered, encoding="utf-8")
        count += 1
    print(f"Updated {count} golden files in {GOLDEN_DIR}")
    return 0


def check_golden() -> int:
    mismatches: list[str] = []
    missing: list[str] = []

    for pipespec_path in sorted(PIPESPEC_DIR.glob("*.json")):
        rendered = _render_compiled(pipespec_path)
        golden_name = pipespec_path.name.replace(".json", ".orchspec.json")
        golden_path = GOLDEN_DIR / golden_name
        if not golden_path.exists():
            missing.append(golden_name)
            continue
        existing = golden_path.read_text(encoding="utf-8")
        if existing != rendered:
            mismatches.append(golden_name)

    if missing or mismatches:
        if missing:
            print("Missing golden files:")
            for name in missing:
                print(f"  - {name}")
        if mismatches:
            print("Mismatched golden files:")
            for name in mismatches:
                print(f"  - {name}")
        print("Run: PYTHONPATH=src python tools/golden.py --update-golden")
        return 1

    print("Golden files are up to date")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage golden fixtures")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Check if golden files match compiler output")
    group.add_argument("--update-golden", action="store_true", help="Regenerate golden files")
    args = parser.parse_args()

    if args.update_golden:
        return update_golden()
    return check_golden()


if __name__ == "__main__":
    raise SystemExit(main())
