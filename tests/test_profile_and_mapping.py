from __future__ import annotations

import json
from pathlib import Path

import pytest

from opos_validator import CompileOptions, compile_pipespec_to_opos, validate_opos
from opos_validator.compiler.mapping_spec import load_mapping_spec

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return json.loads((ROOT / "spec" / "examples" / "pipespec" / name).read_text(encoding="utf-8"))


def test_profile_rejects_unknown_top_level_key() -> None:
    pipespec = _load("pm25_alert_pipeline.json")
    pipespec["unexpected"] = "x"

    with pytest.raises(ValueError) as exc:
        compile_pipespec_to_opos(pipespec, options=CompileOptions(strict=True, enforce_profile=True))

    assert "COMP012" in str(exc.value)


def test_mapping_spec_has_required_sections() -> None:
    spec = load_mapping_spec()
    assert spec["mapping_version"] == "1.0"
    assert "executor_mapping" in spec
    assert spec["executor_mapping"]["python"] == "python_script"
    assert "parameter_type_mapping" in spec
    assert spec["parameter_type_mapping"]["float"] == "FLOAT"
    assert "orchestrator_invariants" in spec


def test_profile_accepts_full_pipespec_flow_and_compiles_to_valid_opos() -> None:
    pipespec = {
        "pipespec_version": "1.0",
        "metadata": {
            "analysis_timestamp": "2026-04-26T00:00:00Z",
            "source_file": "canonical_intent.md",
            "llm_provider": "deepinfra",
            "llm_model": "openai/gpt-oss-120b",
        },
        "pipeline_summary": {
            "name": "Government Pipeline",
            "description": "Government pipeline with branching and dotted ids.",
            "flow_patterns": ["dag"],
            "task_executors": ["python", "sql"],
            "complexity": "medium",
        },
        "components": [
            {
                "id": "group.start",
                "name": "Group Start",
                "category": "Extractor",
                "executor_type": "python",
                "concurrency": {"supports_parallelism": False},
                "datasets": {"consumes": [], "produces": []},
                "io_spec": [
                    {
                        "name": "source_payload",
                        "direction": "output",
                        "kind": "object",
                        "format": "json",
                        "connection_id": "ftp.source",
                    }
                ],
                "connections": [{"id": "ftp.source", "type": "other", "purpose": "ftp input"}],
            },
            {
                "id": "load.results",
                "name": "Load Results",
                "category": "Loader",
                "executor_type": "sql",
                "io_spec": [
                    {
                        "name": "result_rows",
                        "direction": "input",
                        "kind": "object",
                        "format": "redis",
                        "connection_id": "redis.default",
                    },
                    {
                        "name": "results_table",
                        "direction": "output",
                        "kind": "table",
                        "format": "sql",
                        "connection_id": "postgres.default",
                    },
                ],
                "connections": [
                    {"id": "redis.default", "type": "database", "purpose": "state"},
                    {"id": "postgres.default", "type": "database", "purpose": "sink"},
                ],
            },
        ],
        "flow_structure": {
            "pattern": "dag",
            "entry_points": ["group.start"],
            "nodes": {
                "group.start": {
                    "kind": "Task",
                    "component_type_id": "group.start",
                    "upstream_policy": {"type": "all_success", "timeout_seconds": None},
                    "next_nodes": ["load.results"],
                },
                "load.results": {
                    "kind": "Task",
                    "component_type_id": "load.results",
                    "upstream_policy": {"type": "all_success", "timeout_seconds": None},
                    "next_nodes": [],
                },
            },
            "edges": [{"from": "group.start", "to": "load.results", "edge_type": "conditional", "metadata": {"note": "x"}}],
        },
        "parameters": {
            "pipeline": {
                "start_date": {
                    "description": "Start date",
                    "type": "datetime",
                    "default": "2024-01-01",
                    "required": False,
                }
            },
            "schedule": {
                "catchup": {
                    "description": "Catchup",
                    "type": "boolean",
                    "default": False,
                    "required": False,
                },
                "expression": {
                    "description": "Cron expression",
                    "type": "string",
                    "default": "@daily",
                    "required": False,
                },
                "type": {
                    "description": "Schedule type",
                    "type": "string",
                    "default": "cron",
                    "required": False,
                },
            },
            "execution": {
                "model": {
                    "description": "Execution model",
                    "type": "string",
                    "default": "batch",
                    "required": False,
                }
            },
            "components": {},
            "environment": {
                "API_TOKEN": {
                    "description": "API token",
                    "type": "string",
                    "default": None,
                    "required": True,
                    "associated_component_id": "group.start",
                }
            },
        },
        "integrations": {
            "connections": [
                {
                    "id": "ftp.source",
                    "name": "FTP Source",
                    "type": "other",
                    "config": {"base_url": "ftp://example.com"},
                    "authentication": {"type": "none"},
                    "used_by_components": ["group.start"],
                    "direction": "input",
                    "datasets": {"produces": ["source_payload"]},
                },
                {
                    "id": "redis.default",
                    "name": "Redis",
                    "type": "database",
                    "config": {"host": "redis"},
                    "authentication": {"type": "none"},
                    "used_by_components": ["load.results"],
                    "direction": "both",
                },
                {
                    "id": "postgres.default",
                    "name": "Postgres",
                    "type": "database",
                    "config": {"host": "postgres"},
                    "authentication": {"type": "none"},
                    "used_by_components": ["load.results"],
                    "direction": "output",
                },
            ],
            "data_lineage": {"sources": [], "sinks": [], "intermediate_datasets": []},
        },
    }

    opos = compile_pipespec_to_opos(pipespec, options=CompileOptions(strict=True, enforce_profile=True))
    report = validate_opos(opos, strict=True)

    assert report.valid is True
    assert opos["components"][0]["id"] == "group_start"
    assert opos["components"][1]["id"] == "load_results"
    assert opos["integrations"][0]["type"] == "custom"
    assert opos["schedule"]["enabled"] is True
    assert opos["schedule"]["cron"] == "@daily"
    assert opos["schedule"]["start_date"] == "2024-01-01T00:00:00Z"
    assert opos["flow"]["edges"][0]["edge_type"] == "success"


def test_mapping_normalizes_schedule_value_auth_password_and_unknown() -> None:
    pipespec = {
        "pipespec_version": "1.0",
        "metadata": {},
        "pipeline_summary": {
            "name": "Auth Schedule Pipeline",
            "description": "Check auth and schedule normalization.",
            "flow_patterns": ["dag"],
            "task_executors": ["python", "bash"],
            "complexity": "low",
        },
        "components": [
            {
                "id": "extract",
                "name": "Extract",
                "category": "Extractor",
                "executor_type": "bash",
                "io_spec": [],
                "connections": [{"id": "db_conn", "type": "database", "purpose": "read"}],
            },
            {
                "id": "notify",
                "name": "Notify",
                "category": "Notifier",
                "executor_type": "python",
                "io_spec": [],
                "connections": [{"id": "smtp_conn", "type": "smtp", "purpose": "notify"}],
            },
        ],
        "flow_structure": {
            "pattern": "dag",
            "entry_points": ["extract"],
            "nodes": {
                "extract": {
                    "kind": "Task",
                    "component_type_id": "extract",
                    "upstream_policy": {"type": "all_success"},
                    "next_nodes": ["notify"],
                },
                "notify": {
                    "kind": "Task",
                    "component_type_id": "notify",
                    "upstream_policy": {"type": "all_success"},
                    "next_nodes": [],
                },
            },
            "edges": [{"from": "extract", "to": "notify", "edge_type": "success"}],
        },
        "parameters": {
            "pipeline": {},
            "schedule": {
                "catchup": {"value": False},
                "start_date": {"default": {"value": "2024-01-01"}},
                "expression": {"default": {"value": "@daily"}},
                "type": {"default": {"value": "cron"}},
            },
            "execution": {},
            "components": {},
            "environment": {
                "DB_PASSWORD": {
                    "description": "Database password",
                    "type": "string",
                    "default": None,
                    "required": True,
                    "associated_component_id": "extract",
                }
            },
        },
        "integrations": {
            "connections": [
                {
                    "id": "db_conn",
                    "name": "DB",
                    "type": "database",
                    "config": {"protocol": "jdbc"},
                    "authentication": {"type": "password", "password_secret": "DB_PASSWORD"},
                    "used_by_components": ["extract"],
                    "direction": "input",
                },
                {
                    "id": "smtp_conn",
                    "name": "SMTP",
                    "type": "smtp",
                    "config": {"protocol": "smtp"},
                    "authentication": {"type": "unknown"},
                    "used_by_components": ["notify"],
                    "direction": "output",
                },
            ],
            "data_lineage": {"sources": [], "sinks": [], "intermediate_datasets": []},
        },
    }

    opos = compile_pipespec_to_opos(pipespec, options=CompileOptions(strict=True, enforce_profile=True))
    report = validate_opos(opos, strict=True)

    assert report.valid is True
    assert opos["schedule"]["catchup"] is False
    assert opos["schedule"]["start_date"] == "2024-01-01T00:00:00Z"
    assert opos["integrations"][0]["authentication"]["method"] == "basic"
    assert opos["integrations"][0]["authentication"]["password_secret"] == "DB_PASSWORD"
    assert opos["integrations"][1]["authentication"]["method"] == "none"
