"""JSON schema validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from orchspec_validator.validation.models import ValidationIssue


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[3] / "spec" / "orchspec_schema_v1.json"


def validate_against_schema(
    doc: dict[str, Any], *, schema_version: str = "1.0"
) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    if schema_version != "1.0":
        return [ValidationIssue("SCHEMA_VERSION", f"Unsupported schema version: {schema_version}", "$")], []

    schema = json.loads(_schema_path().read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)

    errors: list[ValidationIssue] = []
    for err in sorted(validator.iter_errors(doc), key=lambda e: str(e.path)):
        path = "$" + "".join([f"[{repr(p)}]" for p in err.path])
        errors.append(ValidationIssue("SCHEMA_VALIDATION", err.message, path))
    return errors, []
