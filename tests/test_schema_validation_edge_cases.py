"""Schema validation edge-case tests."""

from __future__ import annotations

from orchspec_validator import validate_orchspec


def _base() -> dict:
    return {
        "orchspec_version": "1.0",
        "pipeline_id": "p",
        "description": "d",
        "metadata": {"name": "n", "owner": "o", "domain": "d", "complexity": "low"},
        "components": [
            {"id": "a", "name": "A", "category": "Extractor", "executor": {"type": "python_script"}},
        ],
        "flow": {"pattern": "sequential", "entry_points": ["a"], "edges": []},
    }


def test_rejects_wrong_orchspec_version() -> None:
    doc = _base()
    doc["orchspec_version"] = "2.0"
    report = validate_orchspec(doc)
    assert not report.valid


def test_rejects_missing_required_field() -> None:
    doc = _base()
    del doc["components"]
    report = validate_orchspec(doc)
    assert not report.valid


def test_rejects_invalid_pipeline_id_pattern() -> None:
    doc = _base()
    doc["pipeline_id"] = "Invalid ID!"
    report = validate_orchspec(doc)
    assert not report.valid


def test_rejects_unknown_executor_type() -> None:
    doc = _base()
    doc["components"][0]["executor"]["type"] = "unknown"
    report = validate_orchspec(doc)
    assert not report.valid


def test_rejects_unknown_category() -> None:
    doc = _base()
    doc["components"][0]["category"] = "UnknownCategory"
    report = validate_orchspec(doc)
    assert not report.valid


def test_rejects_invalid_flow_pattern() -> None:
    doc = _base()
    doc["flow"]["pattern"] = "hypercube"
    report = validate_orchspec(doc)
    assert not report.valid


def test_rejects_empty_entry_points() -> None:
    doc = _base()
    doc["flow"]["entry_points"] = []
    report = validate_orchspec(doc)
    assert not report.valid


def test_rejects_description_too_long() -> None:
    doc = _base()
    doc["description"] = "x" * 5000
    report = validate_orchspec(doc)
    assert not report.valid


def test_valid_document_with_multiple_optional_fields() -> None:
    doc = _base()
    doc["schedule"] = {"enabled": True, "cron": "0 0 * * *"}
    doc["parameters"] = {"batch_size": {"type": "INT", "default": 100}}
    doc["secrets"] = [{"name": "API_KEY", "sensitivity": "high"}]
    doc["error_handling"] = {"on_failure": "fail_pipeline"}
    doc["observability"] = {"logging": {"level": "INFO", "format": "json"}}
    report = validate_orchspec(doc, strict=True)
    assert report.valid


def test_valid_document_with_conditional_flow() -> None:
    doc = _base()
    doc["components"] = [
        {"id": "a", "name": "A", "category": "Extractor", "executor": {"type": "python_script"}},
        {"id": "b", "name": "B", "category": "Loader", "executor": {"type": "python_script"}},
        {"id": "c", "name": "C", "category": "Loader", "executor": {"type": "python_script"}},
    ]
    doc["flow"] = {
        "pattern": "conditional",
        "entry_points": ["a"],
        "edges": [
            {"from": "a", "to": "b", "edge_type": "success", "condition": "x > 5"},
            {"from": "a", "to": "c", "edge_type": "success", "condition": "x <= 5"},
        ],
    }
    report = validate_orchspec(doc)
    assert report.valid


def test_valid_document_with_parallel_flow() -> None:
    doc = _base()
    doc["components"] = [
        {"id": "a", "name": "A", "category": "Extractor", "executor": {"type": "python_script"}},
        {"id": "b", "name": "B", "category": "Transformer", "executor": {"type": "python_script"}},
        {"id": "c", "name": "C", "category": "Transformer", "executor": {"type": "python_script"}},
        {"id": "d", "name": "D", "category": "Loader", "executor": {"type": "python_script"}},
    ]
    doc["flow"] = {
        "pattern": "parallel",
        "entry_points": ["a"],
        "edges": [
            {"from": "a", "to": "b", "edge_type": "success"},
            {"from": "a", "to": "c", "edge_type": "success"},
            {"from": "b", "to": "d", "edge_type": "success"},
            {"from": "c", "to": "d", "edge_type": "success"},
        ],
    }
    report = validate_orchspec(doc)
    assert report.valid


def test_validate_returns_structured_json_report() -> None:
    doc = _base()
    report = validate_orchspec(doc)
    d = report.to_dict()
    assert d["summary"]["valid"] is True
    assert "error_count" in d["summary"]
    assert "warning_count" in d["summary"]
    assert isinstance(d["errors"], list)
    assert isinstance(d["warnings"], list)


def test_sem007_detects_duplicate_component_ids() -> None:
    doc = _base()
    doc["components"] = [
        {"id": "a", "name": "A1", "category": "Extractor", "executor": {"type": "python_script"}},
        {"id": "a", "name": "A2", "category": "Loader", "executor": {"type": "python_script"}},
    ]
    doc["flow"]["entry_points"] = ["a"]
    report = validate_orchspec(doc)
    assert any(e.code == "SEM007" and "component" in e.message.lower() for e in report.errors)


def test_sem008_rejects_branching_in_sequential_flow() -> None:
    doc = _base()
    doc["components"] = [
        {"id": "a", "name": "A", "category": "Extractor", "executor": {"type": "python_script"}},
        {"id": "b", "name": "B", "category": "Loader", "executor": {"type": "python_script"}},
        {"id": "c", "name": "C", "category": "Loader", "executor": {"type": "python_script"}},
    ]
    doc["flow"] = {
        "pattern": "sequential",
        "entry_points": ["a"],
        "edges": [
            {"from": "a", "to": "b", "edge_type": "success"},
            {"from": "a", "to": "c", "edge_type": "success"},
        ],
    }
    report = validate_orchspec(doc)
    assert any(e.code == "SEM008" for e in report.errors)


def test_sem009_schedule_enabled_without_cron() -> None:
    doc = _base()
    doc["schedule"] = {"enabled": True}
    report = validate_orchspec(doc)
    assert any(e.code == "SEM009" for e in report.errors)
