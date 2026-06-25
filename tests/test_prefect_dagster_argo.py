"""Tests for Prefect, Dagster, and Argo workflow adapters."""

from __future__ import annotations

from orchspec_validator.adapters.stubs import PrefectAdapter, DagsterAdapter, ArgoAdapter


def _base_doc() -> dict:
    return {
        "orchspec_version": "1.0",
        "pipeline_id": "test_pipeline",
        "description": "A test pipeline",
        "metadata": {"name": "Test", "owner": "team", "domain": "test", "complexity": "low"},
        "components": [
            {"id": "extract", "name": "Extract", "category": "Extractor",
             "executor": {"type": "python_script"}, "script": "data = fetch()"},
            {"id": "transform", "name": "Transform", "category": "Transformer",
             "executor": {"type": "python_script"}, "script": "result = process(data)"},
            {"id": "load", "name": "Load", "category": "Loader",
             "executor": {"type": "bash"}, "script": "echo 'Done'"},
        ],
        "flow": {
            "pattern": "sequential",
            "entry_points": ["extract"],
            "edges": [
                {"from": "extract", "to": "transform", "edge_type": "success"},
                {"from": "transform", "to": "load", "edge_type": "success"},
            ],
        },
    }


# ---------------------------------------------------------------------------
# Prefect
# ---------------------------------------------------------------------------

def test_prefect_generates_flow_with_tasks() -> None:
    adapter = PrefectAdapter()
    result = adapter.project(_base_doc())
    source = result.content["source"]

    assert result.artifact_type == "prefect_flow_python"
    assert "from prefect import flow, task" in source
    assert "@task" in source
    assert "@flow(" in source
    assert "def test_pipeline():" in source
    assert "extract()" in source
    assert "transform()" in source
    assert "load()" in source


def test_prefect_handles_retry_and_timeout() -> None:
    doc = _base_doc()
    doc["components"][0]["retry"] = {"max_attempts": 3, "delay_seconds": 60}
    doc["components"][0]["timeout"] = "PT300S"

    adapter = PrefectAdapter()
    result = adapter.project(doc)
    source = result.content["source"]

    assert "retries=3" in source
    assert "retry_delay_seconds=60" in source
    assert "timeout_seconds=300" in source


def test_prefect_handles_schedule() -> None:
    doc = _base_doc()
    doc["schedule"] = {"enabled": True, "cron": "0 */6 * * *"}

    adapter = PrefectAdapter()
    result = adapter.project(doc)
    source = result.content["source"]

    assert ".serve(" in source
    assert "0 */6 * * *" in source


def test_prefect_single_component() -> None:
    doc = _base_doc()
    doc["components"] = [doc["components"][0]]
    doc["flow"]["entry_points"] = ["extract"]
    doc["flow"]["edges"] = []

    adapter = PrefectAdapter()
    result = adapter.project(doc)
    source = result.content["source"]

    assert "def extract():" in source
    assert "def test_pipeline():" in source


# ---------------------------------------------------------------------------
# Dagster
# ---------------------------------------------------------------------------

def test_dagster_generates_assets_with_job() -> None:
    adapter = DagsterAdapter()
    result = adapter.project(_base_doc())
    source = result.content["source"]

    assert result.artifact_type == "dagster_definitions_python"
    assert "from dagster import" in source
    assert "@asset" in source
    assert "AssetExecutionContext" in source
    assert "Definitions(" in source
    assert "define_asset_job" in source
    assert "def test_pipeline" in source or "test_pipeline" in source


def test_dagster_asset_dependencies() -> None:
    adapter = DagsterAdapter()
    result = adapter.project(_base_doc())
    source = result.content["source"]

    # transform depends on extract, load depends on transform
    assert "deps=[extract]" in source
    assert "deps=[transform]" in source


def test_dagster_handles_schedule() -> None:
    doc = _base_doc()
    doc["schedule"] = {"enabled": True, "cron": "0 8 * * 1-5"}

    adapter = DagsterAdapter()
    result = adapter.project(doc)
    source = result.content["source"]

    assert "ScheduleDefinition" in source
    assert "0 8 * * 1-5" in source
    assert "all_schedules" in source


def test_dagster_handles_retry() -> None:
    doc = _base_doc()
    doc["components"][0]["retry"] = {"max_attempts": 5}

    adapter = DagsterAdapter()
    result = adapter.project(doc)
    source = result.content["source"]

    assert "RetryPolicy" in source
    assert "max_retries=5" in source


def test_dagster_single_asset_no_deps() -> None:
    doc = _base_doc()
    doc["components"] = [doc["components"][0]]
    doc["flow"]["entry_points"] = ["extract"]
    doc["flow"]["edges"] = []

    adapter = DagsterAdapter()
    result = adapter.project(doc)
    source = result.content["source"]

    assert "@asset" in source
    assert "deps" not in source.split("@asset")[1].split("def")[0]  # no deps arg


# ---------------------------------------------------------------------------
# Argo Workflows
# ---------------------------------------------------------------------------

def test_argo_generates_workflow_template() -> None:
    adapter = ArgoAdapter()
    result = adapter.project(_base_doc())
    source = result.content["source"]

    assert result.artifact_type == "argo_workflow_template_yaml"
    assert "apiVersion: argoproj.io/v1alpha1" in source
    assert "kind: WorkflowTemplate" in source
    assert "entrypoint: main" in source
    assert "templates:" in source
    assert "dag:" in source


def test_argo_task_templates_have_scripts() -> None:
    adapter = ArgoAdapter()
    result = adapter.project(_base_doc())
    source = result.content["source"]

    assert "extract-template" in source
    assert "transform-template" in source
    assert "load-template" in source
    assert "script:" in source


def test_argo_dag_has_dependencies() -> None:
    adapter = ArgoAdapter()
    result = adapter.project(_base_doc())
    source = result.content["source"]

    assert "dependencies:" in source


def test_argo_handles_schedule_with_cron_workflow() -> None:
    doc = _base_doc()
    doc["schedule"] = {"enabled": True, "cron": "*/30 * * * *"}

    adapter = ArgoAdapter()
    result = adapter.project(doc)
    source = result.content["source"]

    assert "kind: CronWorkflow" in source
    assert "*/30 * * * *" in source


def test_argo_handles_retry_strategy() -> None:
    doc = _base_doc()
    doc["components"][0]["retry"] = {"max_attempts": 3, "delay_seconds": 30}
    doc["components"] = [doc["components"][0]]
    doc["flow"]["entry_points"] = ["extract"]
    doc["flow"]["edges"] = []

    adapter = ArgoAdapter()
    result = adapter.project(doc)
    source = result.content["source"]

    assert "retryStrategy:" in source
    assert "limit: 3" in source


def test_argo_single_task_workflow() -> None:
    doc = _base_doc()
    doc["components"] = [doc["components"][0]]
    doc["flow"]["entry_points"] = ["extract"]
    doc["flow"]["edges"] = []

    adapter = ArgoAdapter()
    result = adapter.project(doc)
    source = result.content["source"]

    assert "apiVersion: argoproj.io/v1alpha1" in source
    assert "kind: WorkflowTemplate" in source
