"""PipeSpec profile validation for compiler input."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from orchspec_validator.compiler.models import CompileError


@lru_cache(maxsize=1)
def _validator() -> Draft7Validator:
    schema_path = Path(__file__).resolve().parents[3] / "spec" / "pipespec_profile_v1.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft7Validator(schema)


def validate_pipespec_profile(doc: dict[str, Any]) -> None:
    validator = _validator()
    errors = sorted(validator.iter_errors(doc), key=lambda e: str(e.path))
    if not errors:
        return

    first = errors[0]
    path = "$" + "".join([f"[{repr(p)}]" for p in first.path])
    raise CompileError("COMP012", f"pipespec profile validation failed: {first.message}", path)
