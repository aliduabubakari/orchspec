from __future__ import annotations

from orchspec_validator import get_default_adapters


def _doc() -> dict:
    return {
        "orchspec_version": "1.0",
        "pipeline_id": "sample",
        "description": "sample",
        "metadata": {"name": "Sample", "owner": "Team", "domain": "demo", "complexity": "low"},
        "components": [
            {"id": "a", "name": "A", "category": "Extractor", "executor": {"type": "python_script"}}
        ],
        "flow": {"pattern": "sequential", "entry_points": ["a"], "edges": []},
    }


def test_default_adapters_project_stub_ir() -> None:
    doc = _doc()
    adapters = get_default_adapters()
    assert len(adapters) == 7

    for adapter in adapters:
        issues = adapter.validate_invariants(doc)
        assert issues == []
        result = adapter.project(doc)
        assert result.target == adapter.capability().target
        assert result.artifact_type == "stub_ir"
