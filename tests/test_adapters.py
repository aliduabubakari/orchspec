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
        # Airflow is the only adapter with a real projection (v1.0)
        if result.target == "airflow":
            assert result.artifact_type == "airflow_dag_python"
            assert "source" in result.content
            assert "from airflow" in result.content["source"]
        else:
            assert result.artifact_type == "stub_ir"


def test_airflow_adapter_generates_valid_dag() -> None:
    """Verify the Airflow adapter emits syntactically plausible DAG code."""
    doc = {
        "orchspec_version": "1.0",
        "pipeline_id": "test_pipeline",
        "description": "A test pipeline",
        "metadata": {"name": "Test", "owner": "team", "domain": "test", "complexity": "low"},
        "components": [
            {"id": "extract", "name": "Extract", "category": "Extractor",
             "executor": {"type": "python_script"}, "script": "data = fetch()"},
            {"id": "load", "name": "Load", "category": "Loader",
             "executor": {"type": "bash"}, "script": "echo loaded"},
        ],
        "flow": {"pattern": "sequential", "entry_points": ["extract"],
                 "edges": [{"from": "extract", "to": "load", "edge_type": "success"}]},
    }
    from orchspec_validator.adapters.stubs import AirflowAdapter
    adapter = AirflowAdapter()
    result = adapter.project(doc)
    source = result.content["source"]

    # Must contain key Airflow constructs
    assert "from airflow.decorators import dag" in source
    assert "from airflow.decorators import task" in source
    assert "from airflow.operators.bash import BashOperator" in source
    assert "@dag(" in source
    assert "def test_pipeline():" in source
    assert "extract()" in source or "extract >>" in source
    assert "test_pipeline()" in source


def test_airflow_adapter_dag_with_schedule_and_retry() -> None:
    """Verify scheduled DAGs with retry configuration."""
    doc = {
        "orchspec_version": "1.0",
        "pipeline_id": "scheduled_pipeline",
        "description": "Scheduled",
        "metadata": {"name": "Scheduled", "owner": "team", "domain": "test", "complexity": "low"},
        "components": [
            {"id": "step1", "name": "Step 1", "category": "Extractor",
             "executor": {"type": "http_request", "http_method": "POST"},
             "retry": {"max_attempts": 5, "delay_seconds": 120},
             "timeout": "PT600S"},
        ],
        "flow": {"pattern": "sequential", "entry_points": ["step1"], "edges": []},
        "schedule": {"enabled": True, "cron": "*/15 * * * *", "catchup": True,
                     "start_date": "2025-06-01T00:00:00Z"},
    }
    from orchspec_validator.adapters.stubs import AirflowAdapter
    adapter = AirflowAdapter()
    result = adapter.project(doc)
    source = result.content["source"]

    assert 'schedule="*/15 * * * *"' in source
    assert "catchup=True" in source
    assert "start_date=datetime.fromisoformat" in source
    assert "retries=5" in source
    assert "retry_delay=timedelta(seconds=120)" in source
    assert "execution_timeout=timedelta(seconds=600)" in source
