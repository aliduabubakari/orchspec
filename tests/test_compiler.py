from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchspec_validator import CompileOptions, compile_pipespec_to_orchspec

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return json.loads((ROOT / "spec" / "examples" / "pipespec" / name).read_text(encoding="utf-8"))


def test_compile_airvisual_minimum_structure() -> None:
    pipespec = _load("airvisual_pipeline.json")
    orchspec = compile_pipespec_to_orchspec(pipespec, options=CompileOptions(strict=True))
    assert orchspec["orchspec_version"] == "1.0"
    assert orchspec["metadata"]["complexity"] == "low"
    assert len(orchspec["components"]) == 2
    assert orchspec["flow"]["entry_points"] == ["extract_airvisual_api"]


def test_compile_deterministic_output() -> None:
    pipespec = _load("digital_marketing_pipeline.json")
    first = compile_pipespec_to_orchspec(pipespec, options=CompileOptions(strict=True))
    second = compile_pipespec_to_orchspec(pipespec, options=CompileOptions(strict=True))
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_compile_strict_unknown_executor_has_code() -> None:
    pipespec = _load("pm25_alert_pipeline.json")
    pipespec["components"][0]["executor_type"] = "unknown_runtime"

    with pytest.raises(ValueError) as exc:
        compile_pipespec_to_orchspec(pipespec, options=CompileOptions(strict=True))

    assert "COMP001" in str(exc.value)
