"""Semantic diff edge case tests."""

from __future__ import annotations

from orchspec_validator import semantic_diff_orchspec


def _base() -> dict:
    return {
        "orchspec_version": "1.0",
        "pipeline_id": "p",
        "description": "d",
        "metadata": {"name": "n", "owner": "o", "domain": "d", "complexity": "low"},
        "components": [
            {"id": "a", "name": "A", "category": "Extractor", "executor": {"type": "python_script"}},
            {"id": "b", "name": "B", "category": "Loader", "executor": {"type": "python_script"}},
        ],
        "flow": {
            "pattern": "sequential",
            "entry_points": ["a"],
            "edges": [{"from": "a", "to": "b", "edge_type": "success"}],
        },
    }


def test_diff_empty_for_identical_docs() -> None:
    doc = _base()
    report = semantic_diff_orchspec(doc, doc)
    assert len(report.changes) == 0


def test_diff_detects_edge_removal() -> None:
    left = _base()
    right = _base()
    right["flow"]["edges"] = []
    report = semantic_diff_orchspec(left, right)
    assert len(report.changes) > 0
    assert any(c.change_type == "removed" and "flow.edges" in c.path for c in report.changes)


def test_diff_detects_edge_addition() -> None:
    left = _base()
    left["flow"]["edges"] = []
    right = _base()
    report = semantic_diff_orchspec(left, right)
    assert len(report.changes) > 0
    assert any(c.change_type == "added" and "flow.edges" in c.path for c in report.changes)


def test_diff_detects_component_addition() -> None:
    left = _base()
    right = _base()
    right["components"].append(
        {"id": "c", "name": "C", "category": "Notifier", "executor": {"type": "email"}}
    )
    report = semantic_diff_orchspec(left, right)
    assert any(c.change_type == "added" and "components.c" in c.path for c in report.changes)


def test_diff_detects_component_removal() -> None:
    left = _base()
    right = _base()
    right["components"] = [right["components"][0]]
    report = semantic_diff_orchspec(left, right)
    assert any(c.change_type == "removed" and "components.b" in c.path for c in report.changes)


def test_diff_classifies_component_changes_as_breaking() -> None:
    left = _base()
    right = _base()
    right["components"][0]["executor"]["type"] = "bash"
    report = semantic_diff_orchspec(left, right)
    comp_changes = [c for c in report.changes if "components" in c.path]
    assert len(comp_changes) > 0
    assert all(c.classification == "breaking" for c in comp_changes)


def test_diff_classifies_integration_changes_as_non_breaking() -> None:
    left = _base()
    left["integrations"] = [{"id": "db", "type": "database", "name": "DB"}]
    right = _base()
    right["integrations"] = [{"id": "db", "type": "api", "name": "DB"}]
    report = semantic_diff_orchspec(left, right)
    integ_changes = [c for c in report.changes if "integrations" in c.path]
    assert len(integ_changes) > 0
    assert all(c.classification == "non_breaking" for c in integ_changes)


def test_diff_detects_integration_addition() -> None:
    left = _base()
    right = _base()
    right["integrations"] = [{"id": "new_db", "type": "database", "name": "New DB"}]
    report = semantic_diff_orchspec(left, right)
    assert any(c.change_type == "added" and "integrations" in c.path for c in report.changes)


def test_diff_detects_description_change() -> None:
    left = _base()
    right = _base()
    right["description"] = "new description"
    report = semantic_diff_orchspec(left, right)
    assert any(c.path == "description" for c in report.changes)


def test_diff_detects_deeply_nested_field_change() -> None:
    left = _base()
    left["components"][0]["retry"] = {
        "max_attempts": 3, "strategy": "constant", "delay_seconds": 10
    }
    right = _base()
    right["components"][0]["retry"] = {
        "max_attempts": 5, "strategy": "constant", "delay_seconds": 10
    }
    report = semantic_diff_orchspec(left, right)
    assert any("retry.max_attempts" in c.path for c in report.changes)
