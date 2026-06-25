from __future__ import annotations

import json
from pathlib import Path

from orchspec_validator import CompileOptions, compile_pipespec_to_orchspec

ROOT = Path(__file__).resolve().parents[1]


def test_golden_compiler_outputs() -> None:
    pipespec_dir = ROOT / "spec" / "examples" / "pipespec"
    golden_dir = ROOT / "tests" / "fixtures" / "golden"

    for pipespec_path in sorted(pipespec_dir.glob("*.json")):
        pipespec = json.loads(pipespec_path.read_text(encoding="utf-8"))
        compiled = compile_pipespec_to_orchspec(pipespec, options=CompileOptions(strict=True))
        compiled_text = json.dumps(compiled, indent=2, sort_keys=True) + "\n"

        golden_name = pipespec_path.name.replace(".json", ".orchspec.json")
        golden_path = golden_dir / golden_name
        golden_text = golden_path.read_text(encoding="utf-8")

        assert compiled_text == golden_text, f"golden mismatch for {pipespec_path.name}"
