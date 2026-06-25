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
