from __future__ import annotations

from orchspec_validator import validate_orchspec


def _base_doc() -> dict:
    return {
        "orchspec_version": "1.0",
        "pipeline_id": "p",
        "description": "d",
        "metadata": {"name": "n", "owner": "o", "domain": "d", "complexity": "low"},
        "components": [
            {
                "id": "a",
                "name": "A",
                "category": "Extractor",
                "executor": {"type": "python_script"},
                "retry": {"max_attempts": 2, "strategy": "constant", "delay_seconds": 10},
            },
            {
                "id": "b",
                "name": "B",
                "category": "Transformer",
                "executor": {"type": "python_script"},
                "retry": {"max_attempts": 2, "strategy": "constant", "delay_seconds": 10},
            },
            {
                "id": "c",
                "name": "C",
                "category": "Loader",
                "executor": {"type": "python_script"},
                "retry": {"max_attempts": 2, "strategy": "constant", "delay_seconds": 10},
            },
        ],
        "flow": {
            "pattern": "dag",
            "entry_points": ["a"],
            "edges": [{"from": "a", "to": "b", "edge_type": "success"}],
        },
    }


def test_sem011_unreachable_component() -> None:
    doc = _base_doc()
    report = validate_orchspec(doc)
    assert any(e.code == "SEM011" for e in report.errors)


def test_sem012_disconnected_subgraphs() -> None:
    doc = _base_doc()
    doc["flow"]["edges"] = [
        {"from": "a", "to": "b", "edge_type": "success"}
    ]
    report = validate_orchspec(doc)
    assert any(e.code == "SEM012" for e in report.errors)


def test_sem013_retry_coherence() -> None:
    doc = _base_doc()
    doc["components"][0]["retry"] = {
        "max_attempts": 2,
        "strategy": "exponential",
        "delay_seconds": 30,
        "max_delay_seconds": 10,
        "multiplier": 1.0,
    }
    report = validate_orchspec(doc)
    assert any(e.code == "SEM013" for e in report.errors)


def test_sem010_promoted_to_error_in_strict_mode() -> None:
    doc = _base_doc()
    doc["components"][1]["category"] = "Notifier"
    doc["components"][1]["executor"] = {"type": "sql"}

    non_strict = validate_orchspec(doc, strict=False)
    strict = validate_orchspec(doc, strict=True)

    assert any(w.code == "SEM010" for w in non_strict.warnings)
    assert any(e.code == "SEM010" for e in strict.errors)


def test_sem010_accepts_expanded_corpus_patterns() -> None:
    doc = _base_doc()
    doc["components"][1]["category"] = "Notifier"
    doc["components"][1]["executor"] = {"type": "python_script"}
    doc["components"][2]["executor"] = {"type": "bash"}
    doc["components"][0]["category"] = "Reconciliator"
    doc["components"][0]["executor"] = {"type": "container"}

    report = validate_orchspec(doc, strict=True)
    assert not any(e.code == "SEM010" for e in report.errors)


def test_sem010_accepts_sql_extractor() -> None:
    doc = _base_doc()
    doc["components"][0]["executor"] = {"type": "sql"}

    report = validate_orchspec(doc, strict=True)
    assert not any(e.code == "SEM010" for e in report.errors)


# ---------------------------------------------------------------------------
# SEM014: resource requests must not exceed limits
# ---------------------------------------------------------------------------

def test_sem014_cpu_request_exceeds_limit() -> None:
    doc = _base_doc()
    doc["components"][0]["resources"] = {
        "request": {"cpu": "1000m", "memory": "128Mi"},
        "limit": {"cpu": "500m", "memory": "256Mi"},
    }
    report = validate_orchspec(doc)
    assert any(e.code == "SEM014" and "CPU" in e.message for e in report.errors)


def test_sem014_memory_request_exceeds_limit() -> None:
    doc = _base_doc()
    doc["components"][0]["resources"] = {
        "request": {"cpu": "500m", "memory": "1Gi"},
        "limit": {"cpu": "1000m", "memory": "512Mi"},
    }
    report = validate_orchspec(doc)
    assert any(e.code == "SEM014" and "memory" in e.message for e in report.errors)


def test_sem014_gpu_request_exceeds_limit() -> None:
    doc = _base_doc()
    doc["components"][0]["resources"] = {
        "request": {"gpu": 2},
        "limit": {"gpu": 1},
    }
    report = validate_orchspec(doc)
    assert any(e.code == "SEM014" and "GPU" in e.message for e in report.errors)


def test_sem014_valid_resources_pass() -> None:
    doc = _base_doc()
    doc["components"][0]["resources"] = {
        "request": {"cpu": "500m", "memory": "256Mi"},
        "limit": {"cpu": "1000m", "memory": "1Gi"},
    }
    report = validate_orchspec(doc)
    assert not any(e.code == "SEM014" for e in report.errors)


def test_sem014_cpu_cores_parsing() -> None:
    doc = _base_doc()
    doc["components"][0]["resources"] = {
        "request": {"cpu": "2"},
        "limit": {"cpu": "1"},
    }
    report = validate_orchspec(doc)
    assert any(e.code == "SEM014" for e in report.errors)


# ---------------------------------------------------------------------------
# SEM015: security context coherence
# ---------------------------------------------------------------------------

def test_sem015_run_as_non_root_with_uid_zero() -> None:
    doc = _base_doc()
    doc["components"][0]["security_context"] = {
        "run_as_non_root": True,
        "run_as_user": 0,
    }
    report = validate_orchspec(doc)
    assert any(e.code == "SEM015" for e in report.errors)


def test_sem015_drop_and_add_same_capability() -> None:
    doc = _base_doc()
    doc["components"][0]["security_context"] = {
        "drop_capabilities": ["NET_ADMIN", "SYS_TIME"],
        "add_capabilities": ["NET_ADMIN"],
    }
    report = validate_orchspec(doc)
    assert any(e.code == "SEM015" for e in report.errors)


def test_sem015_valid_security_context_pass() -> None:
    doc = _base_doc()
    doc["components"][0]["security_context"] = {
        "run_as_non_root": True,
        "run_as_user": 1000,
        "drop_capabilities": ["ALL"],
        "add_capabilities": ["NET_BIND_SERVICE"],
    }
    report = validate_orchspec(doc)
    assert not any(e.code == "SEM015" for e in report.errors)


# ---------------------------------------------------------------------------
# SEM016: duplicate output path conflicts
# ---------------------------------------------------------------------------

def test_sem016_duplicate_output_paths() -> None:
    doc = _base_doc()
    doc["components"][0]["outputs"] = [
        {"name": "out1", "kind": "file", "path_pattern": "/data/output.parquet"}
    ]
    doc["components"][1]["outputs"] = [
        {"name": "out2", "kind": "file", "path_pattern": "/data/output.parquet"}
    ]
    report = validate_orchspec(doc)
    assert any(w.code == "SEM016" for w in report.warnings)


def test_sem016_unique_output_paths_pass() -> None:
    doc = _base_doc()
    doc["components"][0]["outputs"] = [
        {"name": "out1", "kind": "file", "path_pattern": "/data/a.parquet"}
    ]
    doc["components"][1]["outputs"] = [
        {"name": "out2", "kind": "file", "path_pattern": "/data/b.parquet"}
    ]
    report = validate_orchspec(doc)
    assert not any(w.code == "SEM016" for w in report.warnings)


# ---------------------------------------------------------------------------
# SEM017: data flow compatibility between connected components
# ---------------------------------------------------------------------------

def test_sem017_incompatible_io_kinds() -> None:
    doc = _base_doc()
    doc["components"][0]["outputs"] = [
        {"name": "out1", "kind": "file"}
    ]
    doc["components"][1]["inputs"] = [
        {"name": "in1", "kind": "table"}
    ]
    report = validate_orchspec(doc)
    assert any(w.code == "SEM017" for w in report.warnings)


def test_sem017_compatible_io_kinds_pass() -> None:
    doc = _base_doc()
    doc["components"][0]["outputs"] = [
        {"name": "out1", "kind": "file"}
    ]
    doc["components"][1]["inputs"] = [
        {"name": "in1", "kind": "file"}
    ]
    report = validate_orchspec(doc)
    assert not any(w.code == "SEM017" for w in report.warnings)


def test_sem017_no_io_declared_passes() -> None:
    doc = _base_doc()
    report = validate_orchspec(doc)
    assert not any(w.code == "SEM017" for w in report.warnings)


# ---------------------------------------------------------------------------
# SEM018: condition expression syntax
# ---------------------------------------------------------------------------

def test_sem018_empty_condition() -> None:
    doc = _base_doc()
    doc["flow"]["edges"] = [
        {"from": "a", "to": "b", "edge_type": "success", "condition": "   "}
    ]
    report = validate_orchspec(doc)
    assert any(w.code == "SEM018" for w in report.warnings)


def test_sem018_unbalanced_parentheses() -> None:
    doc = _base_doc()
    doc["flow"]["edges"] = [
        {"from": "a", "to": "b", "edge_type": "success", "condition": "(x > 5"}
    ]
    report = validate_orchspec(doc)
    assert any(w.code == "SEM018" for w in report.warnings)


def test_sem018_valid_condition_passes() -> None:
    doc = _base_doc()
    doc["flow"]["edges"] = [
        {"from": "a", "to": "b", "edge_type": "success", "condition": "x > 5 and y < 10"}
    ]
    report = validate_orchspec(doc)
    assert not any(w.code == "SEM018" for w in report.warnings)


# ---------------------------------------------------------------------------
# SEM019: integration type ↔ IO kind compatibility
# ---------------------------------------------------------------------------

def test_sem019_file_io_with_database_integration() -> None:
    doc = _base_doc()
    doc["integrations"] = [
        {"id": "pg", "type": "database", "name": "Postgres"}
    ]
    doc["components"][0]["outputs"] = [
        {"name": "out1", "kind": "file", "integration_id": "pg"}
    ]
    report = validate_orchspec(doc)
    assert any(w.code == "SEM019" for w in report.warnings)


def test_sem019_table_io_with_database_integration_passes() -> None:
    doc = _base_doc()
    doc["integrations"] = [
        {"id": "pg", "type": "database", "name": "Postgres"}
    ]
    doc["components"][0]["outputs"] = [
        {"name": "out1", "kind": "table", "integration_id": "pg"}
    ]
    report = validate_orchspec(doc)
    assert not any(w.code == "SEM019" for w in report.warnings)


# ---------------------------------------------------------------------------
# SEM020: timeout vs schedule interval sanity
# ---------------------------------------------------------------------------

def test_sem020_component_timeout_exceeds_schedule_interval() -> None:
    doc = _base_doc()
    doc["schedule"] = {
        "enabled": True,
        "cron": "*/5 * * * *",
    }
    doc["components"][0]["timeout"] = "PT600S"  # 10 minutes > 5 minute interval
    report = validate_orchspec(doc)
    assert any(w.code == "SEM020" for w in report.warnings)


def test_sem020_timeout_within_schedule_interval_passes() -> None:
    doc = _base_doc()
    doc["schedule"] = {
        "enabled": True,
        "cron": "*/10 * * * *",
    }
    doc["components"][0]["timeout"] = "PT60S"  # 1 minute < 10 minute interval
    report = validate_orchspec(doc)
    assert not any(w.code == "SEM020" for w in report.warnings)


def test_sem020_no_schedule_passes() -> None:
    doc = _base_doc()
    doc["components"][0]["timeout"] = "PT3600S"
    report = validate_orchspec(doc)
    assert not any(w.code == "SEM020" for w in report.warnings)


# ---------------------------------------------------------------------------
# SEM021: unused parameters and secrets
# ---------------------------------------------------------------------------

def test_sem021_unused_parameters() -> None:
    doc = _base_doc()
    doc["parameters"] = {
        "batch_size": {"type": "INT", "default": 100},
        "dry_run": {"type": "BOOLEAN", "default": False},
    }
    report = validate_orchspec(doc)
    assert any(w.code == "SEM021" for w in report.warnings)


def test_sem021_used_parameters_pass() -> None:
    doc = _base_doc()
    doc["parameters"] = {
        "batch_size": {"type": "INT", "default": 100},
    }
    doc["components"][0]["parameters"] = {"batch_size": 50}
    report = validate_orchspec(doc)
    assert not any(w.code == "SEM021" for w in report.warnings)


def test_sem021_unused_secrets() -> None:
    doc = _base_doc()
    doc["secrets"] = [
        {"name": "API_KEY"},
        {"name": "DB_PASSWORD"},
    ]
    report = validate_orchspec(doc)
    assert any(w.code == "SEM021" for w in report.warnings)


def test_sem021_secret_used_by_integration_passes() -> None:
    doc = _base_doc()
    doc["secrets"] = [
        {"name": "API_KEY"},
    ]
    doc["integrations"] = [
        {
            "id": "ext_api",
            "type": "api",
            "name": "External API",
            "authentication": {"method": "bearer", "secret_ref": "API_KEY"},
        }
    ]
    report = validate_orchspec(doc)
    assert not any(w.code == "SEM021" for w in report.warnings)
