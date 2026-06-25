"""Airflow adapter advanced tests — multi-branch DAGs, invariants, all executors."""

from __future__ import annotations

import pytest

from orchspec_validator.adapters.stubs import AirflowAdapter


def test_airflow_multi_branch_fan_out_dag() -> None:
    """Fan-out: one source → multiple targets."""
    doc = {
        "orchspec_version": "1.0",
        "pipeline_id": "fan_out_pipeline",
        "description": "Fan-out test",
        "metadata": {"name": "Fan Out", "owner": "team", "domain": "test", "complexity": "low"},
        "components": [
            {"id": "extract", "name": "Extract", "category": "Extractor",
             "executor": {"type": "python_script"}, "script": "data = fetch()"},
            {"id": "process_a", "name": "Process A", "category": "Transformer",
             "executor": {"type": "bash"}, "script": "echo A"},
            {"id": "process_b", "name": "Process B", "category": "Transformer",
             "executor": {"type": "bash"}, "script": "echo B"},
        ],
        "flow": {
            "pattern": "dag",
            "entry_points": ["extract"],
            "edges": [
                {"from": "extract", "to": "process_a", "edge_type": "success"},
                {"from": "extract", "to": "process_b", "edge_type": "success"},
            ],
        },
    }
    adapter = AirflowAdapter()
    result = adapter.project(doc)
    source = result.content["source"]
    assert "extract() >> [process_a, process_b]" in source


def test_airflow_multi_branch_fan_in_dag() -> None:
    """Fan-in: multiple sources → one target."""
    doc = {
        "orchspec_version": "1.0",
        "pipeline_id": "fan_in_pipeline",
        "description": "Fan-in test",
        "metadata": {"name": "Fan In", "owner": "team", "domain": "test", "complexity": "low"},
        "components": [
            {"id": "source_a", "name": "Source A", "category": "Extractor",
             "executor": {"type": "http_request", "http_method": "GET"}},
            {"id": "source_b", "name": "Source B", "category": "Extractor",
             "executor": {"type": "http_request", "http_method": "GET"}},
            {"id": "merger", "name": "Merger", "category": "Transformer",
             "executor": {"type": "python_script"}, "script": "merge()"},
        ],
        "flow": {
            "pattern": "dag",
            "entry_points": ["source_a", "source_b"],
            "edges": [
                {"from": "source_a", "to": "merger", "edge_type": "success"},
                {"from": "source_b", "to": "merger", "edge_type": "success"},
            ],
        },
    }
    adapter = AirflowAdapter()
    result = adapter.project(doc)
    source = result.content["source"]
    assert "source_a >> merger()" in source
    assert "source_b >> merger()" in source


def test_airflow_all_executor_types_generate_operators() -> None:
    """Every OrchSpec executor type must produce a valid Airflow operator."""
    from orchspec_validator.adapters.airflow_projector import generate_airflow_dag

    executors_and_operators = {
        "python_script": "@task",
        "http_request": "SimpleHttpOperator",
        "sql": "SQLExecuteQueryOperator",
        "email": "EmailOperator",
        "bash": "BashOperator",
        "container": "DockerOperator",
        "custom": "PythonOperator",
    }
    for exec_type, expected_op in executors_and_operators.items():
        doc = {
            "orchspec_version": "1.0",
            "pipeline_id": f"test_{exec_type}",
            "description": "Test",
            "metadata": {"name": "Test", "owner": "t", "domain": "t", "complexity": "low"},
            "components": [
                {"id": "task1", "name": "Task", "category": "Custom",
                 "executor": {"type": exec_type, "image": "alpine:latest", "http_method": "GET"},
                 "script": "echo test" if exec_type in ("bash", "sql", "python_script") else None},
            ],
            "flow": {"pattern": "sequential", "entry_points": ["task1"], "edges": []},
        }
        source = generate_airflow_dag(doc)
        assert expected_op in source, f"Expected '{expected_op}' for executor '{exec_type}':\n{source}"


def test_airflow_invariant_sql_warns() -> None:
    adapter = AirflowAdapter()
    doc = {
        "orchspec_version": "1.0",
        "pipeline_id": "test",
        "description": "Test",
        "metadata": {"name": "Test", "owner": "t", "domain": "t", "complexity": "low"},
        "components": [
            {"id": "task1", "name": "Task", "category": "Transformer",
             "executor": {"type": "sql"}, "script": "SELECT 1"},
        ],
        "flow": {"pattern": "sequential", "entry_points": ["task1"], "edges": []},
    }
    violations = adapter.validate_invariants(doc)
    assert len(violations) > 0
    assert any("sql" in v.lower() for v in violations)


def test_airflow_invariant_container_without_image_warns() -> None:
    adapter = AirflowAdapter()
    doc = {
        "orchspec_version": "1.0",
        "pipeline_id": "test",
        "description": "Test",
        "metadata": {"name": "Test", "owner": "t", "domain": "t", "complexity": "low"},
        "components": [
            {"id": "task1", "name": "Task", "category": "Custom",
             "executor": {"type": "container"}},
        ],
        "flow": {"pattern": "sequential", "entry_points": ["task1"], "edges": []},
    }
    violations = adapter.validate_invariants(doc)
    assert len(violations) > 0
    assert any("image" in v.lower() for v in violations)


def test_airflow_project_raises_on_violations() -> None:
    adapter = AirflowAdapter()
    doc = {
        "orchspec_version": "1.0",
        "pipeline_id": "",
        "description": "",
        "metadata": {},
        "components": [],
        "flow": {},
    }
    with pytest.raises(ValueError, match="Cannot project to airflow"):
        adapter.project(doc)


def test_airflow_dag_with_entry_points_multiple() -> None:
    """Multiple entry points should generate correct DAG."""
    doc = {
        "orchspec_version": "1.0",
        "pipeline_id": "multi_entry",
        "description": "Multi entry",
        "metadata": {"name": "Multi", "owner": "t", "domain": "t", "complexity": "low"},
        "components": [
            {"id": "a", "name": "A", "category": "Extractor",
             "executor": {"type": "python_script"}, "script": "pass"},
            {"id": "b", "name": "B", "category": "Extractor",
             "executor": {"type": "python_script"}, "script": "pass"},
            {"id": "c", "name": "C", "category": "Loader",
             "executor": {"type": "bash"}, "script": "echo done"},
        ],
        "flow": {
            "pattern": "dag",
            "entry_points": ["a", "b"],
            "edges": [
                {"from": "a", "to": "c", "edge_type": "success"},
                {"from": "b", "to": "c", "edge_type": "success"},
            ],
        },
    }
    adapter = AirflowAdapter()
    result = adapter.project(doc)
    source = result.content["source"]
    assert "def a(" in source
    assert "def b(" in source
    assert "BashOperator" in source
