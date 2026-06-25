from __future__ import annotations

import json
from pathlib import Path

from orchspec_validator import validate_orchspec

ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_compiled_airvisual() -> None:
    pipespec = _load_json(ROOT / "spec" / "examples" / "pipespec" / "airvisual_pipeline.json")
    from orchspec_validator import CompileOptions, compile_pipespec_to_orchspec

    orchspec = compile_pipespec_to_orchspec(pipespec, options=CompileOptions(strict=True))
    report = validate_orchspec(orchspec)
    assert report.valid is True
    assert not report.errors


def test_semantic_missing_integration() -> None:
    doc = {
        "orchspec_version": "1.0",
        "pipeline_id": "x",
        "description": "x",
        "metadata": {"name": "x", "owner": "o", "domain": "d", "complexity": "low"},
        "components": [
            {
                "id": "c1",
                "name": "c1",
                "category": "Extractor",
                "executor": {"type": "python_script"},
                "integrations_used": ["missing"]
            }
        ],
        "flow": {"pattern": "sequential", "entry_points": ["c1"], "edges": []}
    }
    report = validate_orchspec(doc)
    assert report.valid is False
    assert any(e.code == "SEM004" for e in report.errors)
