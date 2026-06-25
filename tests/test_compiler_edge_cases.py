"""Compiler edge-case and error-path tests."""

from __future__ import annotations

import json

import pytest

from orchspec_validator import CompileOptions, compile_pipespec_to_orchspec, validate_orchspec


def _base_pipespec() -> dict:
    return {
        "pipespec_version": "1.0",
        "metadata": {"analysis_timestamp": "2026-01-01T00:00:00Z"},
        "pipeline_summary": {
            "name": "Test Pipeline",
            "description": "A test pipeline",
            "flow_patterns": ["sequential"],
            "task_executors": ["python"],
            "complexity": "low",
        },
        "components": [
            {
                "id": "step1",
                "name": "Step 1",
                "category": "Extractor",
                "executor_type": "python",
                "io_spec": [
                    {"name": "data", "direction": "output", "kind": "object", "format": "json"}
                ],
            }
        ],
        "flow_structure": {
            "pattern": "sequential",
            "entry_points": ["step1"],
            "nodes": {
                "step1": {
                    "kind": "Task",
                    "component_type_id": "step1",
                    "upstream_policy": {"type": "all_success"},
                    "next_nodes": [],
                }
            },
            "edges": [],
        },
        "parameters": {
            "pipeline": {},
            "schedule": {},
            "execution": {},
            "components": {},
            "environment": {},
        },
        "integrations": {
            "connections": [],
            "data_lineage": {"sources": [], "sinks": [], "intermediate_datasets": []},
        },
    }


# ---------------------------------------------------------------------------
# COMP error codes
# ---------------------------------------------------------------------------

def test_comp001_unknown_executor_strict() -> None:
    doc = _base_pipespec()
    doc["components"][0]["executor_type"] = "made_up_runtime"
    with pytest.raises(ValueError, match="COMP001"):
        compile_pipespec_to_orchspec(doc, options=CompileOptions(strict=True))


def test_comp001_unknown_executor_non_strict_coerces_to_custom() -> None:
    doc = _base_pipespec()
    doc["components"][0]["executor_type"] = "made_up_runtime"
    result = compile_pipespec_to_orchspec(doc, options=CompileOptions(strict=False))
    assert result["components"][0]["executor"]["type"] == "custom"


def test_comp008_wrong_pipespec_version() -> None:
    doc = _base_pipespec()
    doc["pipespec_version"] = "2.0"
    with pytest.raises(ValueError, match="COMP008"):
        compile_pipespec_to_orchspec(doc, options=CompileOptions())


def test_comp009_empty_components() -> None:
    doc = _base_pipespec()
    doc["components"] = []
    with pytest.raises(ValueError, match="COMP009"):
        compile_pipespec_to_orchspec(doc, options=CompileOptions())


def test_comp010_missing_pipeline_name() -> None:
    doc = _base_pipespec()
    doc["pipeline_summary"]["name"] = ""
    with pytest.raises(ValueError, match="COMP010"):
        compile_pipespec_to_orchspec(doc, options=CompileOptions())


def test_comp011_missing_pipeline_description() -> None:
    doc = _base_pipespec()
    doc["pipeline_summary"]["description"] = ""
    with pytest.raises(ValueError, match="COMP011"):
        compile_pipespec_to_orchspec(doc, options=CompileOptions())


def test_comp012_profile_rejects_unknown_field() -> None:
    doc = _base_pipespec()
    doc["unknown_field"] = "should be rejected"
    with pytest.raises(ValueError, match="COMP012"):
        compile_pipespec_to_orchspec(doc, options=CompileOptions(strict=True, enforce_profile=True))


# ---------------------------------------------------------------------------
# All executor types
# ---------------------------------------------------------------------------

def test_all_executor_types_compile() -> None:
    executors = ["python", "http", "sql", "bash", "email", "docker", "custom"]
    for ex in executors:
        doc = _base_pipespec()
        doc["components"][0]["executor_type"] = ex
        result = compile_pipespec_to_orchspec(doc, options=CompileOptions(strict=True))
        mapped = result["components"][0]["executor"]["type"]
        # Every executor must map to a valid OrchSpec executor
        assert mapped in {
            "python_script", "http_request", "sql", "bash",
            "email", "container", "custom",
        }, f"{ex} → {mapped}"


# ---------------------------------------------------------------------------
# ID canonicalization edge cases
# ---------------------------------------------------------------------------

def test_canonical_ids_handle_special_characters() -> None:
    doc = _base_pipespec()
    doc["components"][0]["id"] = "My Component!!!"
    result = compile_pipespec_to_orchspec(doc, options=CompileOptions())
    # Should be sanitized to lowercase alphanumeric + underscores
    cid = result["components"][0]["id"]
    assert cid == "my_component"


def test_canonical_ids_handle_collisions() -> None:
    doc = _base_pipespec()
    doc["components"] = [
        {
            "id": "task.one",
            "name": "Task One",
            "category": "Extractor",
            "executor_type": "python",
            "io_spec": [{"name": "x", "direction": "output", "kind": "object", "format": "json"}],
        },
        {
            "id": "task one",
            "name": "Task Two",
            "category": "Transformer",
            "executor_type": "python",
            "io_spec": [{"name": "x", "direction": "input", "kind": "object", "format": "json"}],
        },
    ]
    doc["flow_structure"]["entry_points"] = ["task.one"]
    doc["flow_structure"]["nodes"] = {
        "task.one": {
            "kind": "Task", "component_type_id": "task.one",
            "upstream_policy": {"type": "all_success"}, "next_nodes": ["task one"],
        },
        "task one": {
            "kind": "Task", "component_type_id": "task one",
            "upstream_policy": {"type": "all_success"}, "next_nodes": [],
        },
    }
    doc["flow_structure"]["edges"] = [{"from": "task.one", "to": "task one", "edge_type": "success"}]
    result = compile_pipespec_to_orchspec(doc, options=CompileOptions())
    ids = [c["id"] for c in result["components"]]
    assert len(ids) == 2
    assert len(set(ids)) == 2  # no collisions after canonicalization
    assert "task_one" in ids
    assert any(i.startswith("task_one_") for i in ids)


# ---------------------------------------------------------------------------
# Parameter type normalization
# ---------------------------------------------------------------------------

def test_parameter_types_normalized() -> None:
    doc = _base_pipespec()
    doc["parameters"]["pipeline"] = {
        "batch_size": {"description": "Batch size", "type": "integer", "default": 100, "required": True},
        "threshold": {"description": "Threshold", "type": "float", "default": 0.5, "required": False},
        "enabled": {"description": "Enabled", "type": "boolean", "default": True, "required": False},
    }
    result = compile_pipespec_to_orchspec(doc, options=CompileOptions())
    params = result.get("parameters", {})
    assert params.get("batch_size", {}).get("type") == "INT"
    assert params.get("threshold", {}).get("type") == "FLOAT"
    assert params.get("enabled", {}).get("type") == "BOOLEAN"


# ---------------------------------------------------------------------------
# Schedule normalization edge cases
# ---------------------------------------------------------------------------

def test_schedule_disabled_for_manual_expression() -> None:
    doc = _base_pipespec()
    doc["parameters"]["schedule"] = {
        "expression": {"default": {"value": "manual"}},
    }
    result = compile_pipespec_to_orchspec(doc, options=CompileOptions())
    assert result.get("schedule", {}).get("enabled") is False


def test_schedule_enabled_for_cron_expression() -> None:
    doc = _base_pipespec()
    doc["parameters"]["schedule"] = {
        "expression": {"default": {"value": "0 */6 * * *"}},
        "type": {"default": {"value": "cron"}},
        "catchup": {"default": True},
    }
    result = compile_pipespec_to_orchspec(doc, options=CompileOptions())
    assert result.get("schedule", {}).get("enabled") is True
    assert result.get("schedule", {}).get("cron") == "0 */6 * * *"
    assert result.get("schedule", {}).get("catchup") is True


# ---------------------------------------------------------------------------
# IO format normalization
# ---------------------------------------------------------------------------

def test_io_formats_normalized() -> None:
    doc = _base_pipespec()
    doc["components"][0]["io_spec"] = [
        {"name": "x", "direction": "output", "kind": "file", "format": "TXT"},
        {"name": "y", "direction": "input", "kind": "file", "format": "csv"},
    ]
    result = compile_pipespec_to_orchspec(doc, options=CompileOptions())
    outputs = result["components"][0].get("outputs", [])
    inputs = result["components"][0].get("inputs", [])
    assert outputs[0]["format"] == "text"
    assert inputs[0]["format"] == "csv"


# ---------------------------------------------------------------------------
# Integration type normalization
# ---------------------------------------------------------------------------

def test_integration_types_normalized() -> None:
    doc = _base_pipespec()
    doc["integrations"]["connections"] = [
        {
            "id": "s3_bucket",
            "name": "S3",
            "type": "objectstore",
            "config": {},
            "authentication": {"type": "none"},
            "used_by_components": ["step1"],
            "direction": "both",
        },
        {
            "id": "kafka_topic",
            "name": "Kafka",
            "type": "queue",
            "config": {},
            "authentication": {"type": "none"},
            "used_by_components": ["step1"],
            "direction": "input",
        },
    ]
    result = compile_pipespec_to_orchspec(doc, options=CompileOptions())
    types = {i["type"] for i in result.get("integrations", [])}
    assert "object_store" in types
    assert "message_queue" in types


# ---------------------------------------------------------------------------
# Deterministism properties
# ---------------------------------------------------------------------------

def test_determinism_preserves_semantics_across_runs() -> None:
    doc = _base_pipespec()
    compiled = [
        json.dumps(compile_pipespec_to_orchspec(doc, options=CompileOptions(strict=True)), sort_keys=True)
        for _ in range(5)
    ]
    assert len(set(compiled)) == 1


def test_determinism_handles_topological_sort_consistently() -> None:
    """Components with the same topology should sort consistently."""
    doc = _base_pipespec()
    doc["components"] = [
        {"id": "C", "name": "C", "category": "Loader", "executor_type": "python",
         "io_spec": [{"name": "x", "direction": "input", "kind": "object", "format": "json"}]},
        {"id": "A", "name": "A", "category": "Extractor", "executor_type": "python",
         "io_spec": [{"name": "x", "direction": "output", "kind": "object", "format": "json"}]},
        {"id": "B", "name": "B", "category": "Transformer", "executor_type": "python",
         "io_spec": [{"name": "x", "direction": "input", "kind": "object", "format": "json"}]},
    ]
    doc["flow_structure"]["entry_points"] = ["A"]
    doc["flow_structure"]["nodes"] = {
        "A": {"kind": "Task", "component_type_id": "A", "upstream_policy": {"type": "all_success"}, "next_nodes": ["B"]},
        "B": {"kind": "Task", "component_type_id": "B", "upstream_policy": {"type": "all_success"}, "next_nodes": ["C"]},
        "C": {"kind": "Task", "component_type_id": "C", "upstream_policy": {"type": "all_success"}, "next_nodes": []},
    }
    doc["flow_structure"]["edges"] = [
        {"from": "A", "to": "B", "edge_type": "success"},
        {"from": "B", "to": "C", "edge_type": "success"},
    ]
    first = compile_pipespec_to_orchspec(doc, options=CompileOptions())
    second = compile_pipespec_to_orchspec(doc, options=CompileOptions())
    assert [c["id"] for c in first["components"]] == [c["id"] for c in second["components"]]


# ---------------------------------------------------------------------------
# Roundtrip: compile → validate
# ---------------------------------------------------------------------------

def test_compiled_output_passes_validation() -> None:
    doc = _base_pipespec()
    orchspec = compile_pipespec_to_orchspec(doc, options=CompileOptions(strict=True))
    report = validate_orchspec(orchspec, strict=True)
    assert report.valid is True
    assert len(report.errors) == 0


# ---------------------------------------------------------------------------
# Provenance tracking
# ---------------------------------------------------------------------------

def test_provenance_includes_source_info() -> None:
    doc = _base_pipespec()
    doc["metadata"]["source_file"] = "pipeline_desc.txt"
    doc["metadata"]["llm_model"] = "gpt-4"
    doc["metadata"]["llm_provider"] = "openai"
    result = compile_pipespec_to_orchspec(doc, options=CompileOptions())
    prov = result.get("provenance", {})
    assert prov.get("source_file") == "pipeline_desc.txt"
    assert prov.get("generator_id") == "openai"
    assert prov.get("generator_version") == "gpt-4"
    assert prov.get("source_type") == "step1_json"
