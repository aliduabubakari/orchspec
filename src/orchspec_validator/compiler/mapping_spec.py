"""Machine-readable mapping spec loader."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def load_mapping_spec() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / "spec" / "mappings" / "pipespec_to_orchspec_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def executor_mapping() -> dict[str, str]:
    return dict(load_mapping_spec().get("executor_mapping", {}))


def parameter_type_mapping() -> dict[str, str]:
    return dict(load_mapping_spec().get("parameter_type_mapping", {}))


def orchestrator_invariants() -> dict[str, Any]:
    return dict(load_mapping_spec().get("orchestrator_invariants", {}))
