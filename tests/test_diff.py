from __future__ import annotations

from orchspec_validator import semantic_diff_orchspec


def test_diff_detects_component_field_level_change() -> None:
    left = {
        "orchspec_version": "1.0",
        "pipeline_id": "p",
        "description": "a",
        "metadata": {"name": "n", "owner": "o", "domain": "d", "complexity": "low"},
        "components": [{"id": "a", "name": "A", "category": "Extractor", "executor": {"type": "python_script"}}],
        "flow": {"pattern": "sequential", "entry_points": ["a"], "edges": []}
    }
    right = {
        "orchspec_version": "1.0",
        "pipeline_id": "p",
        "description": "a",
        "metadata": {"name": "n", "owner": "o", "domain": "d", "complexity": "low"},
        "components": [{"id": "a", "name": "A", "category": "Extractor", "executor": {"type": "http_request"}}],
        "flow": {"pattern": "sequential", "entry_points": ["a"], "edges": []}
    }
    report = semantic_diff_orchspec(left, right)
    assert report.changes
    assert any(c.path == "components.a.executor.type" for c in report.changes)
    assert all(c.classification == "breaking" for c in report.changes)
